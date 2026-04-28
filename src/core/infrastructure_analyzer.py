"""
Infrastructure Intelligence Module

Integrates real infrastructure data (roads, utilities, planned developments) 
to enhance speculative scoring accuracy beyond heuristics.

Author: CloudClearingAPI Team  
Date: September 2025
"""

import json
import logging
import os
import threading
import time
from typing import Dict, List, Tuple, Optional, Any

import requests
from dataclasses import dataclass
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, box
import numpy as np
from datetime import datetime, timedelta
import ee

# 🆕 v2.8: OSM Infrastructure Caching
from src.core.osm_cache import OSMInfrastructureCache

logger = logging.getLogger(__name__)

# Process-wide Overpass throttling: parallel scoring + 3× concurrent queries per region
# was tripping HTTP 429 on public instances. Serialize POSTs and space them out.
_overpass_lock = threading.Lock()
_last_overpass_end = 0.0
_CC_OVERPASS_MIN_GAP = float(os.environ.get("CC_OVERPASS_MIN_GAP_SEC", "2.5"))
# Skip all live Overpass calls (regional fallback only) — for unstable public instances
_CC_OS_SKIP_LIVE_OVERPASS = os.environ.get("CC_OS_SKIP_LIVE_OVERPASS", "").lower() in (
    "1",
    "true",
    "yes",
)

# Process-wide Overpass circuit breaker. When the upstream public instances are
# down (504 / timeout storms), every region pays minutes of retry sleeps before
# falling back. After N total failed Overpass calls in this run we trip the
# breaker and route all remaining regions straight to the regional fallback.
_OVERPASS_BREAKER_LOCK = threading.Lock()
_overpass_failure_count = 0
_overpass_breaker_tripped_at = 0.0
_OVERPASS_BREAKER_THRESHOLD = int(os.environ.get("CC_OVERPASS_BREAKER_THRESHOLD", "6"))


def _overpass_breaker_record_failure() -> bool:
    """Increment the global Overpass failure count. Returns True if the breaker just tripped."""
    global _overpass_failure_count, _overpass_breaker_tripped_at
    with _OVERPASS_BREAKER_LOCK:
        _overpass_failure_count += 1
        if _overpass_failure_count >= _OVERPASS_BREAKER_THRESHOLD and _overpass_breaker_tripped_at == 0.0:
            _overpass_breaker_tripped_at = time.monotonic()
            return True
        return False


def _overpass_breaker_is_tripped() -> bool:
    return _overpass_breaker_tripped_at > 0.0


def _overpass_connect_timeout_sec() -> float:
    return float(os.environ.get("CC_OVERPASS_CONNECT_TIMEOUT_SEC", "12"))


def _overpass_stall_log_interval_sec() -> float:
    """Log while HTTP is in-flight so multi-minute hangs are visible in the log."""
    return float(os.environ.get("CC_OVERPASS_STALL_LOG_SEC", "45"))


class _OverpassCancelled(Exception):
    """Raised when an in-flight Overpass POST is cancelled by an outer timeout."""


def _requests_post_overpass(
    url: str,
    query: str,
    timeout_tuple: Tuple[float, float],
    log_label: str,
    cancel_event: Optional[threading.Event] = None,
) -> requests.Response:
    """
    Run requests.post in a worker thread and log periodically if still waiting.
    Bounds connect vs read explicitly (single float timeout can still wedge on some stacks).

    If *cancel_event* is set while the request is in flight the function raises
    ``_OverpassCancelled`` promptly (within one stall-log interval) instead of
    waiting for the full HTTP timeout.  The daemon thread may continue briefly
    but will terminate when its socket times out or the process exits.
    """
    headers = {"User-Agent": "CloudClearingAPI/2.0 (research; contact via repo)"}
    result: Dict[str, Any] = {}
    error: Dict[str, Exception] = {}

    def _worker() -> None:
        try:
            resp = requests.post(
                url,
                data={"data": query},
                timeout=timeout_tuple,
                headers=headers,
            )
            result["response"] = resp
        except Exception as e:
            error["e"] = e

    th = threading.Thread(target=_worker, daemon=True, name="overpass-http")
    th.start()
    t0 = time.monotonic()
    interval = max(15.0, _overpass_stall_log_interval_sec())
    while th.is_alive():
        th.join(timeout=interval)
        # Check cancellation from outer region timeout
        if cancel_event is not None and cancel_event.is_set():
            elapsed = time.monotonic() - t0
            logger.warning(
                f"  ⛔ {log_label}: cancelled by outer timeout after {elapsed:.0f}s "
                f"(daemon HTTP thread will drain on its own)"
            )
            raise _OverpassCancelled(f"{log_label} cancelled after {elapsed:.0f}s")
        if th.is_alive():
            elapsed = time.monotonic() - t0
            logger.warning(
                f"  … {log_label}: still waiting on Overpass HTTP "
                f"({elapsed:.0f}s elapsed, connect/read timeout={timeout_tuple})"
            )
    if error:
        raise error["e"]
    if "response" not in result:
        raise RuntimeError(f"{log_label}: Overpass worker exited without response or error")
    return result["response"]


def _overpass_post_throttled(
    url: str,
    query: str,
    read_timeout: float,
    log_label: str = "Overpass",
    cancel_event: Optional[threading.Event] = None,
) -> requests.Response:
    """Single global Overpass POST with minimum spacing between calls."""
    global _last_overpass_end
    try:
        host = url.split("//", 1)[1].split("/", 1)[0]
    except (IndexError, ValueError):
        host = url
    connect_t = _overpass_connect_timeout_sec()
    timeout_tuple = (connect_t, float(read_timeout))
    # Log outside the lock so a blocked thread still shows *something* while another holds the slot.
    logger.info(
        f"  ⏳ {log_label}: waiting for shared Overpass slot (another region may be querying)…"
    )
    with _overpass_lock:
        # Check cancellation while waiting for the slot
        if cancel_event is not None and cancel_event.is_set():
            raise _OverpassCancelled(f"{log_label} cancelled before POST (outer timeout)")
        gap = time.monotonic() - _last_overpass_end
        if gap < _CC_OVERPASS_MIN_GAP:
            time.sleep(_CC_OVERPASS_MIN_GAP - gap)
        logger.info(
            f"  📤 {log_label}: HTTP POST → {host} "
            f"(connect {connect_t}s, read up to {read_timeout}s; "
            f"stall log every {_overpass_stall_log_interval_sec():.0f}s if slow)"
        )
        try:
            return _requests_post_overpass(url, query, timeout_tuple, log_label, cancel_event)
        finally:
            _last_overpass_end = time.monotonic()

@dataclass
class InfrastructureFeature:
    """Container for infrastructure data"""
    feature_type: str      # 'highway', 'railway', 'airport', 'port'
    name: str
    geometry: Any          # Shapely geometry
    importance: str        # 'primary', 'secondary', 'tertiary'
    status: str           # 'existing', 'under_construction', 'planned'
    distance_km: float    # Distance from analysis area
    impact_score: float   # 0-100

class InfrastructureAnalyzer:
    """
    Analyzes real infrastructure data to enhance investment scoring
    """
    
    def __init__(self):
        self.osm_base_url = "https://overpass-api.de/api/interpreter"
        # Alternative Overpass API endpoints for failover.
        # kumi.systems demoted to last — it returned empty/garbage responses
        # ("Expecting value: line 1 column 1") on multiple queries in the
        # 2026-04-05 run.
        self.osm_fallback_urls = [
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]
        
        # 🆕 v2.8: Initialize OSM Infrastructure Cache (7-day expiry)
        self.osm_cache = OSMInfrastructureCache(
            cache_dir="./cache/osm",
            expiry_days=7
        )
        logger.info("✅ OSM infrastructure cache initialized (7-day expiry)")
        
        self.infrastructure_weights = {
            # Road infrastructure
            'motorway': 100,
            'trunk': 90, 
            'primary': 80,
            'secondary': 60,
            'tertiary': 40,
            'motorway_construction': 95,
            'trunk_construction': 85,
            
            # Railways
            'rail': 75,
            'light_rail': 65,
            'subway': 70,
            'rail_construction': 80,
            
            # Aviation
            'aerodrome': 90,
            'airport': 95,
            'helipad': 30,
            
            # Ports and logistics
            'harbour': 85,
            'port': 90,
            'logistics': 70
        }
        
        # 🆕 IMPROVED: Expanded distance decay factors for better rural coverage
        self.distance_decay = {
            'motorway': {'max_distance': 50, 'half_life': 15},     # Expanded from 10km to 50km
            'airport': {'max_distance': 100, 'half_life': 30},     # Expanded from 25km to 100km
            'railway': {'max_distance': 25, 'half_life': 8},       # Expanded from 5km to 25km
            'port': {'max_distance': 50, 'half_life': 15}          # Expanded from 15km to 50km
        }
        
        # Regional fallback database — all 65 monitoring regions across Indonesia
        # Used when OSM Overpass API queries fail or return implausibly low results
        self.regional_infrastructure_database = {
            # Jakarta Metro Area (Tier 1)
            'jakarta_north_sprawl': {'infra_score': 95, 'highways': 8, 'ports': 2, 'airports': 2, 'railways': 3},
            'jakarta_south_suburbs': {'infra_score': 90, 'highways': 7, 'ports': 1, 'airports': 2, 'railways': 2},
            'tangerang_bsd_corridor': {'infra_score': 92, 'highways': 7, 'ports': 1, 'airports': 2, 'railways': 1},
            'bekasi_industrial_belt': {'infra_score': 88, 'highways': 6, 'ports': 1, 'airports': 1, 'railways': 2},
            'cikarang_mega_industrial': {'infra_score': 85, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 2},
            'bogor_puncak_highland': {'infra_score': 70, 'highways': 4, 'ports': 0, 'airports': 0, 'railways': 1},

            'karawang_industrial_corridor': {'infra_score': 85, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 2},

            # Bandung Area (Tier 1-2)
            'bandung_north_expansion': {'infra_score': 82, 'highways': 5, 'ports': 0, 'airports': 1, 'railways': 2},
            'bandung_east_tech_corridor': {'infra_score': 78, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},

            # West Java Corridors (Tier 2-3)
            'cirebon_port_industrial': {'infra_score': 75, 'highways': 4, 'ports': 2, 'airports': 1, 'railways': 1},
            # v2.19.0: subang_patimban_megaport split into industrial + agrarian
            'subang_patimban_industrial': {'infra_score': 75, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 0},
            'subang_pantura_agrarian':    {'infra_score': 55, 'highways': 2, 'ports': 0, 'airports': 0, 'railways': 0},

            # Central Java (Tier 2)
            'semarang_port_expansion': {'infra_score': 85, 'highways': 5, 'ports': 2, 'airports': 1, 'railways': 2},
            'semarang_south_urban': {'infra_score': 80, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 2},
            'solo_raya_expansion': {'infra_score': 78, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'tegal_brebes_coastal': {'infra_score': 65, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'batang_industrial_sez': {'infra_score': 72, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'purwokerto_south_expansion': {'infra_score': 65, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 1},

            # Yogyakarta (Tier 2)
            'yogyakarta_urban_core': {'infra_score': 75, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'yogyakarta_kulon_progo_airport': {'infra_score': 82, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 0},
            'magelang_borobudur_corridor': {'infra_score': 68, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 0},

            # East Java (Tier 1-2)
            'surabaya_west_expansion': {'infra_score': 88, 'highways': 6, 'ports': 2, 'airports': 1, 'railways': 2},
            'surabaya_east_industrial': {'infra_score': 85, 'highways': 6, 'ports': 1, 'airports': 1, 'railways': 1},
            'gresik_port_industrial': {'infra_score': 82, 'highways': 5, 'ports': 2, 'airports': 1, 'railways': 1},
            'sidoarjo_delta_development': {'infra_score': 82, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 1},
            'malang_south_highland': {'infra_score': 70, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'probolinggo_bromo_gateway': {'infra_score': 68, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'jember_southern_coast': {'infra_score': 58, 'highways': 2, 'ports': 0, 'airports': 0, 'railways': 0},
            'banyuwangi_ferry_corridor': {'infra_score': 70, 'highways': 3, 'ports': 2, 'airports': 1, 'railways': 0},

            # Banten (Tier 2-3)
            'serang_cilegon_industrial': {'infra_score': 85, 'highways': 5, 'ports': 2, 'airports': 1, 'railways': 1},
            'merak_port_corridor': {'infra_score': 90, 'highways': 4, 'ports': 3, 'airports': 0, 'railways': 1},
            'anyer_carita_coastal': {'infra_score': 60, 'highways': 2, 'ports': 1, 'airports': 0, 'railways': 0},

            # Sumatra (11 regions)
            'medan_kuala_namu_corridor': {'infra_score': 82, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 1},
            'medan_belawan_port': {'infra_score': 80, 'highways': 4, 'ports': 2, 'airports': 1, 'railways': 1},
            'palembang_jakabaring_expansion': {'infra_score': 75, 'highways': 4, 'ports': 1, 'airports': 1, 'railways': 1},
            'palembang_boom_baru_port': {'infra_score': 78, 'highways': 4, 'ports': 2, 'airports': 1, 'railways': 1},
            'bandar_lampung_south_expansion': {'infra_score': 70, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 1},
            'bakauheni_ferry_corridor': {'infra_score': 65, 'highways': 2, 'ports': 2, 'airports': 0, 'railways': 0},
            'batam_industrial_expansion': {'infra_score': 85, 'highways': 4, 'ports': 3, 'airports': 1, 'railways': 0},
            'pekanbaru_urban_growth': {'infra_score': 68, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            'padang_urban_coastal': {'infra_score': 65, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            'banda_aceh_reconstruction': {'infra_score': 60, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},
            'lake_toba_tourism_zone': {'infra_score': 55, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},

            # Bali (6 regions)
            'denpasar_north_expansion': {'infra_score': 80, 'highways': 4, 'ports': 1, 'airports': 1, 'railways': 0},
            'canggu_seminyak_corridor': {'infra_score': 72, 'highways': 3, 'ports': 0, 'airports': 1, 'railways': 0},
            'sanur_beach_resort': {'infra_score': 70, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            'ubud_north_highland': {'infra_score': 55, 'highways': 2, 'ports': 0, 'airports': 1, 'railways': 0},
            'tabanan_west_coast': {'infra_score': 55, 'highways': 2, 'ports': 0, 'airports': 1, 'railways': 0},
            'nusa_dua_bukit_peninsula': {'infra_score': 78, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},

            # Lombok / NTT (4 regions)
            'mataram_urban_expansion': {'infra_score': 62, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},
            'lombok_mandalika_resort': {'infra_score': 65, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},
            'lombok_senggigi_coast': {'infra_score': 55, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},
            'labuan_bajo_komodo_gateway': {'infra_score': 58, 'highways': 1, 'ports': 1, 'airports': 1, 'railways': 0},
            'kupang_urban_development': {'infra_score': 52, 'highways': 1, 'ports': 1, 'airports': 1, 'railways': 0},

            # Kalimantan (6 regions)
            'nusantara_capital_core': {'infra_score': 70, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            'nusantara_balikpapan_corridor': {'infra_score': 75, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            # v2.19.0: balikpapan_port_industrial split into Kariangau (heavy
            # industrial, north) + Selatan (residential/commercial, south)
            'balikpapan_kariangau_industrial': {'infra_score': 78, 'highways': 4, 'ports': 2, 'airports': 0, 'railways': 0},
            'balikpapan_selatan_commercial':   {'infra_score': 80, 'highways': 4, 'ports': 1, 'airports': 1, 'railways': 0},
            'samarinda_urban_expansion': {'infra_score': 68, 'highways': 3, 'ports': 1, 'airports': 1, 'railways': 0},
            'banjarmasin_port_development': {'infra_score': 70, 'highways': 3, 'ports': 2, 'airports': 1, 'railways': 0},
            'pontianak_urban_growth': {'infra_score': 62, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},

            # Sulawesi (4 regions)
            'makassar_port_corridor': {'infra_score': 82, 'highways': 4, 'ports': 2, 'airports': 1, 'railways': 0},
            'makassar_urban_expansion': {'infra_score': 78, 'highways': 4, 'ports': 1, 'airports': 1, 'railways': 0},
            'manado_tourism_expansion': {'infra_score': 65, 'highways': 2, 'ports': 1, 'airports': 1, 'railways': 0},
            # v2.19.0: bitung_port_industrial split into port_corridor + KEK SEZ
            'bitung_port_corridor':         {'infra_score': 70, 'highways': 2, 'ports': 2, 'airports': 1, 'railways': 0},
            'bitung_kek_sez_industrial':    {'infra_score': 65, 'highways': 2, 'ports': 0, 'airports': 0, 'railways': 0},

            # Eastern Indonesia (2 regions)
            'jayapura_urban_development': {'infra_score': 52, 'highways': 1, 'ports': 1, 'airports': 1, 'railways': 0},
            'ambon_tourism_expansion': {'infra_score': 55, 'highways': 1, 'ports': 1, 'airports': 1, 'railways': 0},
        }

    def analyze_infrastructure_context(
        self,
        bbox: Dict[str, float],
        region_name: str,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """
        Analyze infrastructure context around a region using real data

        🆕 v2.8: Cache-aware infrastructure analysis (7-day cache expiry)
        - Cache HIT: Returns cached data instantly (~0.1s vs ~30s API call)
        - Cache MISS: Queries OSM API and saves to cache
        
        Args:
            bbox: Bounding box coordinates
            region_name: Name of the region being analyzed
            
        Returns:
            Infrastructure analysis results
        """
        
        analysis = {
            'infrastructure_score': 50,  # Base score
            'major_features': [],
            'construction_projects': [],
            'planned_developments': [],
            'accessibility_score': 50,
            'logistics_score': 50,
            'reasoning': []
        }
        
        try:
            # 🆕 v2.8: Check cache first (7-day expiry)
            cached_data = self.osm_cache.get(region_name)
            
            if cached_data is not None:
                logger.info(f"✅ Using cached infrastructure for {region_name}")
                return self._process_cached_infrastructure(cached_data, bbox, region_name)
            
            # Cache miss - query OSM API (or skip when public Overpass is unstable)
            if _CC_OS_SKIP_LIVE_OVERPASS:
                logger.warning(
                    f"⚠️ CC_OS_SKIP_LIVE_OVERPASS set — skipping Overpass for {region_name}, using regional fallback"
                )
                analysis["reasoning"].append(
                    "⚠️ Live Overpass disabled (CC_OS_SKIP_LIVE_OVERPASS) — regional knowledge base"
                )
                analysis.update(self._get_regional_infrastructure_fallback(region_name))
                return analysis

            # Circuit breaker: if Overpass has failed too many times this run,
            # skip live calls entirely and use the regional fallback. Saves
            # ~3-5 min per remaining region during an Overpass outage.
            if _overpass_breaker_is_tripped():
                logger.warning(
                    f"⛔ Overpass circuit breaker open — skipping live query for {region_name}, "
                    "using regional fallback (set CC_OVERPASS_BREAKER_THRESHOLD to tune)"
                )
                analysis["reasoning"].append(
                    "⚠️ Overpass circuit breaker open — using regional knowledge base"
                )
                analysis.update(self._get_regional_infrastructure_fallback(region_name))
                analysis["data_source"] = "fallback_breaker"
                return analysis

            logger.info(f"🔴 Cache miss for {region_name} - querying OSM API")

            expand_km = float(os.environ.get("CC_OSM_BBOX_EXPAND_KM", "40"))
            expanded_bbox = self._expand_bbox(bbox, expansion_km=expand_km)

            logger.info(f"📡 Querying OSM infrastructure for {region_name}...")

            # Sequential Overpass queries (roads → airports → railways). Global throttle in
            # _query_overpass_with_retry avoids 429 when many regions score in parallel.
            try:
                t0 = time.monotonic()
                logger.info(f"   🛣️  [{region_name}] Overpass 1/3: major roads (may take minutes if overloaded)...")
                roads_data = self._query_osm_roads(expanded_bbox, region_name, cancel_event=cancel_event)
                logger.info(
                    f"   🛣️  [{region_name}] roads done: {len(roads_data)} elements in "
                    f"{time.monotonic() - t0:.1f}s → airports"
                )
            except _OverpassCancelled:
                roads_data = []
                logger.warning(f"  ⛔ Roads query cancelled for {region_name} (outer timeout)")
            except Exception as exc:
                roads_data = []
                logger.error(
                    f"  🚨 Roads query exception for {region_name}: {type(exc).__name__}: {exc}"
                )
            try:
                t0 = time.monotonic()
                logger.info(f"   ✈️  [{region_name}] Overpass 2/3: airports...")
                airports_data = self._query_osm_airports(expanded_bbox, region_name, cancel_event=cancel_event)
                logger.info(
                    f"   ✈️  [{region_name}] airports done: {len(airports_data)} elements in "
                    f"{time.monotonic() - t0:.1f}s → railways"
                )
            except _OverpassCancelled:
                airports_data = []
                logger.warning(f"  ⛔ Airports query cancelled for {region_name} (outer timeout)")
            except Exception:
                airports_data = []
                logger.warning(f"  ⚠️ Airports query failed for {region_name}")
            try:
                t0 = time.monotonic()
                logger.info(f"   🚆 [{region_name}] Overpass 3/3: railways...")
                railways_data = self._query_osm_railways(expanded_bbox, region_name, cancel_event=cancel_event)
                logger.info(
                    f"   🚆 [{region_name}] railways done: {len(railways_data)} elements in "
                    f"{time.monotonic() - t0:.1f}s"
                )
            except _OverpassCancelled:
                railways_data = []
                logger.warning(f"  ⛔ Railways query cancelled for {region_name} (outer timeout)")
            except Exception:
                railways_data = []
                logger.warning(f"  ⚠️ Railways query failed for {region_name}")
            
            # Check if we got ANY data
            has_any_data = bool(roads_data or airports_data or railways_data)
            
            if not has_any_data:
                logger.warning(f"⚠️ No OSM data returned for {region_name}, using regional fallback")
                analysis['reasoning'].append("⚠️ Infrastructure data unavailable - using regional knowledge base")
                analysis.update(self._get_regional_infrastructure_fallback(region_name))
                return analysis
            
            # 🆕 v2.8: Cache the raw OSM query results
            cache_entry = {
                'roads_data': roads_data,
                'airports_data': airports_data,
                'railways_data': railways_data,
                'expanded_bbox': expanded_bbox,
                'query_timestamp': datetime.now().isoformat()
            }
            self.osm_cache.save(region_name, cache_entry)
            logger.info(f"💾 Cached infrastructure data for {region_name}")
            
            # Analyze each infrastructure type
            road_analysis = self._analyze_road_infrastructure(roads_data, bbox)
            airport_analysis = self._analyze_airport_infrastructure(airports_data, bbox)
            railway_analysis = self._analyze_railway_infrastructure(railways_data, bbox)
            
            # Combine analyses
            analysis.update(self._combine_infrastructure_analysis(
                road_analysis, airport_analysis, railway_analysis, region_name
            ))
            
            logger.info(f"✅ OSM infrastructure analysis complete for {region_name} (score: {analysis['infrastructure_score']})")
            
            # Sanity check: only override if OSM score is implausibly low
            # (< 30% of fallback) — otherwise prefer the live data even if lower
            fallback = self._get_regional_infrastructure_fallback(region_name)
            fallback_score = fallback.get('infrastructure_score', 0)
            osm_score = analysis['infrastructure_score']
            if fallback_score > 0 and osm_score < fallback_score * 0.3:
                logger.warning(
                    f"⚠️ OSM score ({osm_score}) is <30% of fallback ({fallback_score}) "
                    f"for {region_name} — blending with fallback"
                )
                blended = max(osm_score, int(fallback_score * 0.8))
                analysis['infrastructure_score'] = blended
                analysis['data_source'] = 'osm_live_blended'
            else:
                analysis['data_source'] = 'osm_live'
            
        except Exception as e:
            logger.warning(f"Infrastructure analysis failed for {region_name}: {e}")
            analysis['reasoning'].append("⚠️ Infrastructure data unavailable - using regional defaults")
            
            # Fallback to regional knowledge
            analysis.update(self._get_regional_infrastructure_fallback(region_name))
        
        return analysis
    
    def _process_cached_infrastructure(self, 
                                      cached_data: Dict[str, Any],
                                      bbox: Dict[str, float],
                                      region_name: str) -> Dict[str, Any]:
        """
        Process cached infrastructure data (exact same logic as fresh OSM query)
        
        🆕 v2.8: Enables instant infrastructure analysis from cache
        
        Args:
            cached_data: Cached OSM query results
            bbox: Current analysis bounding box
            region_name: Region name for logging
            
        Returns:
            Infrastructure analysis results
        """
        analysis = {
            'infrastructure_score': 50,
            'major_features': [],
            'construction_projects': [],
            'planned_developments': [],
            'accessibility_score': 50,
            'logistics_score': 50,
            'reasoning': ['✅ Using cached infrastructure data (< 7 days old)']
        }
        
        try:
            # Extract cached OSM data
            roads_data = cached_data.get('roads_data', [])
            airports_data = cached_data.get('airports_data', [])
            railways_data = cached_data.get('railways_data', [])
            
            # Analyze each infrastructure type (same logic as fresh query)
            road_analysis = self._analyze_road_infrastructure(roads_data, bbox)
            airport_analysis = self._analyze_airport_infrastructure(airports_data, bbox)
            railway_analysis = self._analyze_railway_infrastructure(railways_data, bbox)
            
            # Combine analyses
            analysis.update(self._combine_infrastructure_analysis(
                road_analysis, airport_analysis, railway_analysis, region_name
            ))
            
            logger.info(f"✅ Processed cached infrastructure for {region_name} (score: {analysis['infrastructure_score']})")
            
            # Check if cache has incomplete data (e.g. one leg timed out)
            has_roads = bool(roads_data)
            has_airports = bool(airports_data)
            has_railways = bool(railways_data)
            present = sum([has_roads, has_airports, has_railways])
            if 0 < present < 3:
                missing = []
                if not has_roads:
                    missing.append("roads")
                if not has_airports:
                    missing.append("airports")
                if not has_railways:
                    missing.append("railways")
                logger.info(
                    f"  ⚠️ Cached data incomplete for {region_name} "
                    f"({', '.join(missing)} missing) — invalidating cache for next run"
                )
                self.osm_cache.invalidate(region_name)
            
            fallback = self._get_regional_infrastructure_fallback(region_name)
            fallback_score = fallback.get('infrastructure_score', 0)
            osm_score = analysis['infrastructure_score']
            if fallback_score > 0 and osm_score < fallback_score * 0.3:
                blended = max(osm_score, int(fallback_score * 0.8))
                analysis['infrastructure_score'] = blended
                analysis['data_source'] = 'osm_cached_blended'
            else:
                analysis['data_source'] = 'osm_cached'
            
        except Exception as e:
            logger.warning(f"Failed to process cached infrastructure for {region_name}: {e}")
            # Fallback to regional knowledge on cache processing failure
            analysis.update(self._get_regional_infrastructure_fallback(region_name))
        
        return analysis

    def _overpass_server_timeout_sec(self) -> int:
        """Overpass QL [timeout:N] — server-side query budget (seconds)."""
        return int(os.environ.get("CC_OVERPASS_SERVER_TIMEOUT_SEC", "55"))

    def _expand_bbox(self, bbox: Dict[str, float], expansion_km: float) -> Dict[str, float]:
        """Expand bounding box by specified kilometers"""
        # Rough conversion: 1 degree ≈ 111km
        expansion_deg = expansion_km / 111.0
        
        return {
            'west': bbox['west'] - expansion_deg,
            'south': bbox['south'] - expansion_deg, 
            'east': bbox['east'] + expansion_deg,
            'north': bbox['north'] + expansion_deg
        }

    def _query_osm_roads(
        self,
        bbox: Dict[str, float],
        region_name: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> List[Dict]:
        """Query OpenStreetMap for road infrastructure with retry logic and failover"""
        _ot = self._overpass_server_timeout_sec()
        overpass_query = f"""
        [out:json][timeout:{_ot}];
        (
          way["highway"~"^(motorway|trunk|primary|secondary)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"~"^(motorway|trunk|primary)_construction$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out center;
        """

        return self._query_overpass_with_retry(
            overpass_query, "roads", region_name=region_name,
            cancel_event=cancel_event, bbox=bbox,
        )

    def _query_osm_airports(
        self,
        bbox: Dict[str, float],
        region_name: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> List[Dict]:
        """Query OpenStreetMap for airports with retry logic and failover"""
        _ot = self._overpass_server_timeout_sec()
        overpass_query = f"""
        [out:json][timeout:{_ot}];
        (
          way["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["aeroway"="airport"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out center;
        """

        return self._query_overpass_with_retry(
            overpass_query, "airports", region_name=region_name,
            cancel_event=cancel_event, bbox=bbox,
        )

    def _query_osm_railways(
        self,
        bbox: Dict[str, float],
        region_name: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> List[Dict]:
        """Query OpenStreetMap for railway infrastructure with retry logic and failover"""
        _ot = self._overpass_server_timeout_sec()
        overpass_query = f"""
        [out:json][timeout:{_ot}];
        (
          way["railway"="rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="light_rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="construction"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out center;
        """

        return self._query_overpass_with_retry(
            overpass_query, "railways", region_name=region_name,
            cancel_event=cancel_event, bbox=bbox,
        )
    
    # Plausibility thresholds for element counts per feature type.
    # Exceeding these logs a warning (data is still used — but the log
    # makes anomalies visible in post-run review).
    _ELEMENT_COUNT_WARN = {"roads": 5000, "airports": 50, "railways": 2000}

    def _query_overpass_with_retry(
        self,
        query: str,
        feature_type: str,
        max_retries: int = None,
        region_name: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
        bbox: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """
        Query Overpass with rotation, throttling, and bounded wall time.
        Fails open to [] so callers can use regional fallback when all legs miss.

        *cancel_event*: if set by an outer timeout the retry loop exits early.
        *bbox*: when provided, elements outside the bbox (± 10 %) are logged as
        out-of-bounds (they are kept — Overpass sometimes returns nearby data
        for ways that cross the bbox edge).
        """
        if max_retries is None:
            max_retries = int(os.environ.get("CC_OVERPASS_MAX_RETRIES", "3"))

        # Shorter defaults fail faster to the next mirror / empty+fallback instead of wedging the run.
        t_min = int(os.environ.get("CC_OVERPASS_HTTP_TIMEOUT_MIN_SEC", "45"))
        t_max = int(os.environ.get("CC_OVERPASS_HTTP_TIMEOUT_MAX_SEC", "90"))

        api_urls = [self.osm_base_url] + [u for u in self.osm_fallback_urls if u]
        api_urls = list(dict.fromkeys(api_urls))

        last_error = None
        prev_gateway_or_timeout = False
        consecutive_5xx_or_timeout = 0
        log_label = f"OSM {feature_type}"
        if region_name:
            log_label = f"{log_label} [{region_name}]"

        for attempt_num in range(1, max_retries + 1):
            # Bail early if the outer region timeout fired
            if cancel_event is not None and cancel_event.is_set():
                logger.warning(f"  ⛔ {log_label}: skipping attempt {attempt_num} — outer timeout")
                break

            # Per-call circuit breaker: if 2 different mirrors already returned 5xx /
            # timeout, the upstream is degraded — skip remaining attempts (saves ~22s
            # of retry sleep per query).
            if consecutive_5xx_or_timeout >= 2:
                logger.warning(
                    f"  ⛔ {log_label}: 2 consecutive 5xx/timeout — skipping remaining "
                    f"{max_retries - attempt_num + 1} attempt(s), routing to fallback"
                )
                break

            api_url = api_urls[(attempt_num - 1) % len(api_urls)]
            host = api_url.split("/")[2]
            read_timeout = min(t_min + (attempt_num - 1) * 20, t_max)

            if attempt_num > 1:
                delay = 2 if prev_gateway_or_timeout else min(5 + attempt_num * 3, 22)
                prev_gateway_or_timeout = False
                logger.info(
                    f"  Retry {attempt_num}/{max_retries} for {feature_type} "
                    f"({host}) after {delay}s delay "
                    f"(read timeout={read_timeout}s, connect={_overpass_connect_timeout_sec():.0f}s)..."
                )
                time.sleep(delay)

            try:
                response = _overpass_post_throttled(
                    api_url,
                    query,
                    read_timeout,
                    log_label=f"{log_label} try{attempt_num}/{max_retries}",
                    cancel_event=cancel_event,
                )

                if response.status_code == 429:
                    last_error = "HTTP 429 Too Many Requests"
                    retry_after = response.headers.get("Retry-After")
                    try:
                        sleep_s = min(int(retry_after), 90) if retry_after else 20
                    except (TypeError, ValueError):
                        sleep_s = 20
                    logger.warning(
                        f"  ❌ {log_label} HTTP 429 ({host}) attempt {attempt_num}/{max_retries} — "
                        f"sleeping {sleep_s}s"
                    )
                    time.sleep(sleep_s)
                    prev_gateway_or_timeout = True
                    continue

                if response.status_code in (500, 502, 503, 504):
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        f"  ❌ {log_label} HTTP {response.status_code} ({host}) "
                        f"(attempt {attempt_num}/{max_retries})"
                    )
                    prev_gateway_or_timeout = True
                    consecutive_5xx_or_timeout += 1
                    continue

                response.raise_for_status()

                data = response.json()

                remark = data.get("remark", "")
                if "timeout" in remark.lower() or "runtime" in remark.lower():
                    last_error = f"Overpass server-side timeout: {remark[:80]}"
                    logger.warning(
                        f"  ⏱️ {log_label} server-side timeout ({host}) "
                        f"(attempt {attempt_num}/{max_retries})"
                    )
                    prev_gateway_or_timeout = True
                    continue

                elements = data.get("elements", [])

                # --- element count sanity check ---
                warn_limit = self._ELEMENT_COUNT_WARN.get(feature_type, 5000)
                if len(elements) > warn_limit:
                    logger.warning(
                        f"  ⚠️ {log_label}: unusually high element count "
                        f"({len(elements)} > {warn_limit}) — data may include "
                        f"unexpected features; review query / bbox size"
                    )

                # --- coordinate plausibility (spot check) ---
                if bbox and elements:
                    margin = 0.10  # 10 % of bbox span
                    lat_span = (bbox["north"] - bbox["south"]) * margin
                    lon_span = (bbox["east"] - bbox["west"]) * margin
                    s = bbox["south"] - lat_span
                    n = bbox["north"] + lat_span
                    w = bbox["west"] - lon_span
                    e = bbox["east"] + lon_span
                    oob = 0
                    for el in elements:
                        lat = el.get("lat") or (el.get("center") or {}).get("lat")
                        lon = el.get("lon") or (el.get("center") or {}).get("lon")
                        if lat is not None and lon is not None:
                            if not (s <= lat <= n and w <= lon <= e):
                                oob += 1
                    if oob > 0:
                        logger.warning(
                            f"  ⚠️ {log_label}: {oob}/{len(elements)} elements outside "
                            f"bbox (±10 % margin) — likely ways crossing the boundary"
                        )

                if attempt_num > 1:
                    logger.info(f"  ✅ {feature_type} query succeeded on attempt {attempt_num}")

                return elements

            except _OverpassCancelled:
                logger.warning(f"  ⛔ {log_label}: cancelled during attempt {attempt_num}")
                break

            except requests.exceptions.Timeout:
                last_error = (
                    f"Timeout (connect/read {_overpass_connect_timeout_sec():.0f}s / {read_timeout}s)"
                )
                logger.warning(
                    f"  ⏱️ {log_label} query timeout ({host}) (attempt {attempt_num}/{max_retries})"
                )
                prev_gateway_or_timeout = True
                consecutive_5xx_or_timeout += 1
                continue

            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response is not None else 0
                last_error = f"HTTP error: {code}"
                logger.warning(
                    f"  ❌ {log_label} HTTP error: {code} ({host}) "
                    f"(attempt {attempt_num}/{max_retries})"
                )
                if code == 429:
                    time.sleep(min(20 + attempt_num * 8, 75))
                    prev_gateway_or_timeout = True
                    continue
                if code in (500, 502, 503, 504):
                    prev_gateway_or_timeout = True
                    continue
                break

            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(
                    f"  ❌ {log_label} request error: {e} ({host}) "
                    f"(attempt {attempt_num}/{max_retries})"
                )
                prev_gateway_or_timeout = True
                continue

            except json.JSONDecodeError:
                last_error = "Invalid JSON response"
                logger.warning(
                    f"  ❌ {log_label} invalid JSON ({host}) (attempt {attempt_num}/{max_retries})"
                )
                prev_gateway_or_timeout = True
                continue

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.warning(
                    f"  ❌ {log_label} unexpected error: {e} ({host}) "
                    f"(attempt {attempt_num}/{max_retries})"
                )
                prev_gateway_or_timeout = True
                continue

        # Build diagnostic context for post-run log review
        bbox_str = ""
        if bbox:
            bbox_str = (
                f" bbox=({bbox['south']:.3f},{bbox['west']:.3f},"
                f"{bbox['north']:.3f},{bbox['east']:.3f})"
            )
        mirrors_tried = ", ".join(
            api_urls[(i - 1) % len(api_urls)].split("/")[2]
            for i in range(1, max_retries + 1)
        )

        if feature_type == "roads":
            # Roads is the most impactful scoring leg — log at ERROR with full context
            logger.error(
                f"🚨 ROADS TOTAL FAILURE [{region_name or '?'}]: "
                f"all {max_retries} attempts returned 0 elements. "
                f"Last error: {last_error} | "
                f"Mirrors tried: [{mirrors_tried}] | "
                f"Timeouts: connect={_overpass_connect_timeout_sec():.0f}s, "
                f"read={t_min}-{t_max}s |{bbox_str}"
            )
        else:
            logger.error(
                f"❌ All {max_retries} attempts failed for {feature_type} query "
                f"[{region_name or '?'}]. Last error: {last_error} | "
                f"Mirrors: [{mirrors_tried}]{bbox_str}"
            )

        # Bump process-wide failure counter and trip the breaker if threshold reached
        if _overpass_breaker_record_failure():
            logger.error(
                f"⛔ Overpass circuit breaker TRIPPED after {_OVERPASS_BREAKER_THRESHOLD} failures — "
                "remaining regions will use regional fallback"
            )
        return []

    def _analyze_road_infrastructure(self, roads_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze road infrastructure impact"""
        
        analysis = {
            'score': 0,
            'major_roads': [],
            'construction_roads': [],
            'accessibility_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for road in roads_data:
            try:
                highway_type = road.get('tags', {}).get('highway', '')
                road_name = road.get('tags', {}).get('name', f'Unnamed {highway_type}')
                
                # Get road location (supports both out center and out geom)
                road_point = None
                if road.get('center'):
                    road_point = Point(road['center']['lon'], road['center']['lat'])
                elif road.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in road['geometry']]
                    if len(coords) >= 2:
                        road_point = LineString(coords).centroid
                    elif coords:
                        road_point = Point(coords[0])
                
                if road_point:
                    distance_km = target_center.distance(road_point) * 111
                    
                    base_weight = self.infrastructure_weights.get(highway_type, 0)
                    if distance_km <= self.distance_decay.get('motorway', {}).get('max_distance', 10):
                        decay = np.exp(-distance_km / self.distance_decay.get('motorway', {}).get('half_life', 3))
                        weighted_score = base_weight * decay
                        
                        analysis['score'] += weighted_score
                        
                        feature_info = {
                            'name': road_name,
                            'type': highway_type,
                            'distance_km': round(distance_km, 1),
                            'impact_score': round(weighted_score, 1)
                        }
                        
                        if 'construction' in highway_type:
                            analysis['construction_roads'].append(feature_info)
                        else:
                            analysis['major_roads'].append(feature_info)
                
            except Exception as e:
                logger.debug(f"Error processing road: {e}")
                continue
        
        # Calculate accessibility multiplier
        if analysis['score'] > 200:
            analysis['accessibility_multiplier'] = 1.5  # Excellent access
        elif analysis['score'] > 100:
            analysis['accessibility_multiplier'] = 1.3  # Good access
        elif analysis['score'] > 50:
            analysis['accessibility_multiplier'] = 1.1  # Moderate access
        
        return analysis

    def _analyze_airport_infrastructure(self, airports_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze airport infrastructure impact"""
        
        analysis = {
            'score': 0,
            'airports': [],
            'aviation_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for airport in airports_data:
            try:
                airport_name = airport.get('tags', {}).get('name', 'Unnamed Airport')
                airport_type = airport.get('tags', {}).get('aeroway', 'aerodrome')
                
                # Get airport location (supports node, out center, and out geom)
                airport_point = None
                if airport['type'] == 'node':
                    airport_point = Point(airport['lon'], airport['lat'])
                elif airport.get('center'):
                    airport_point = Point(airport['center']['lon'], airport['center']['lat'])
                elif airport.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in airport['geometry']]
                    if coords:
                        airport_polygon = Polygon(coords) if len(coords) > 2 else Point(coords[0])
                        airport_point = airport_polygon.centroid
                
                if not airport_point:
                    continue
                
                distance_km = target_center.distance(airport_point) * 111
                
                # Apply distance decay for airports
                if distance_km <= self.distance_decay.get('airport', {}).get('max_distance', 25):
                    base_weight = self.infrastructure_weights.get('airport', 95)
                    decay = np.exp(-distance_km / self.distance_decay.get('airport', {}).get('half_life', 8))
                    weighted_score = base_weight * decay
                    
                    analysis['score'] += weighted_score
                    analysis['airports'].append({
                        'name': airport_name,
                        'type': airport_type,
                        'distance_km': round(distance_km, 1),
                        'impact_score': round(weighted_score, 1)
                    })
                
            except Exception as e:
                logger.debug(f"Error processing airport: {e}")
                continue
        
        # Aviation multiplier for tourism/business development
        if analysis['score'] > 150:
            analysis['aviation_multiplier'] = 1.4
        elif analysis['score'] > 75:
            analysis['aviation_multiplier'] = 1.2
        
        return analysis

    def _analyze_railway_infrastructure(self, railways_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze railway infrastructure impact"""
        
        analysis = {
            'score': 0,
            'railways': [],
            'transit_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for railway in railways_data:
            try:
                railway_type = railway.get('tags', {}).get('railway', 'rail')
                railway_name = railway.get('tags', {}).get('name', f'Railway {railway_type}')
                
                railway_point = None
                if railway.get('center'):
                    railway_point = Point(railway['center']['lon'], railway['center']['lat'])
                elif railway.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in railway['geometry']]
                    if len(coords) >= 2:
                        railway_point = LineString(coords).centroid
                    elif coords:
                        railway_point = Point(coords[0])
                
                if railway_point:
                    distance_km = target_center.distance(railway_point) * 111
                    
                    if distance_km <= self.distance_decay.get('railway', {}).get('max_distance', 5):
                        base_weight = self.infrastructure_weights.get(railway_type, 75)
                        decay = np.exp(-distance_km / self.distance_decay.get('railway', {}).get('half_life', 2))
                        weighted_score = base_weight * decay
                        
                        analysis['score'] += weighted_score
                        analysis['railways'].append({
                            'name': railway_name,
                            'type': railway_type,
                            'distance_km': round(distance_km, 1),
                            'impact_score': round(weighted_score, 1)
                        })
                
            except Exception as e:
                logger.debug(f"Error processing railway: {e}")
                continue
        
        if analysis['score'] > 100:
            analysis['transit_multiplier'] = 1.3
        elif analysis['score'] > 50:
            analysis['transit_multiplier'] = 1.15
        
        return analysis

    def _combine_infrastructure_analysis(self, 
                                       road_analysis: Dict, 
                                       airport_analysis: Dict,
                                       railway_analysis: Dict,
                                       region_name: str) -> Dict[str, Any]:
        """
        Combine all infrastructure analyses into final score using unified total caps approach.
        
        Version 2.5: Standardized scoring with total caps + distance weighting
        - Roads: max 35 points
        - Aviation: max 20 points
        - Railways: max 20 points
        - Construction: max 10 points
        """
        
        # Component point allocations (total across all features)
        MAX_ROAD_POINTS = 35
        MAX_RAILWAY_POINTS = 20
        MAX_AVIATION_POINTS = 20
        MAX_CONSTRUCTION_POINTS = 10
        
        # Get raw scores from component analyses
        road_score_raw = road_analysis['score']
        airport_score_raw = airport_analysis['score']
        railway_score_raw = railway_analysis['score']
        
        # Apply total caps to raw scores
        # Raw scores already include distance weighting from component analyzers
        # Now we just need to cap them to prevent accumulation
        
        # Scale raw accumulations to fit within caps
        # Higher factors since out center yields lower per-element scores than out geom
        road_score = min(MAX_ROAD_POINTS, road_score_raw * 0.7)
        aviation_score = min(MAX_AVIATION_POINTS, airport_score_raw * 0.5)
        railway_score = min(MAX_RAILWAY_POINTS, railway_score_raw * 0.5)
        
        # Construction bonus: Cap at 10 points based on construction activity
        construction_roads = road_analysis.get('construction_roads', [])
        construction_score = min(MAX_CONSTRUCTION_POINTS, len(construction_roads) * 2)
        
        # Calculate base score
        base_score = road_score + aviation_score + railway_score + construction_score
        # Maximum possible: 35 + 20 + 20 + 10 = 85 points
        
        # Accessibility adjustment based on overall connectivity (±10 points)
        # High road network density increases accessibility
        accessibility_adjustment = 0.0
        if road_score_raw > 300:  # Exceptional connectivity
            accessibility_adjustment = 10
        elif road_score_raw > 200:  # Excellent connectivity
            accessibility_adjustment = 7
        elif road_score_raw > 100:  # Good connectivity
            accessibility_adjustment = 4
        elif road_score_raw > 50:  # Basic connectivity
            accessibility_adjustment = 2
        # Below 50: no adjustment (neutral)
        
        # Final score: base + accessibility adjustment (capped at 100)
        # Typical range: 30-70, exceptional: 70-90, world-class: 90-100
        final_score = min(100, base_score + accessibility_adjustment)
        
        # Final score: base + accessibility adjustment (capped at 100)
        # Typical range: 30-70, exceptional: 70-90, world-class: 90-100
        final_score = min(100, base_score + accessibility_adjustment)
        
        # Generate reasoning
        reasoning = []
        
        # Road infrastructure
        major_roads = road_analysis['major_roads']
        construction_roads = road_analysis['construction_roads']
        
        if major_roads:
            reasoning.append(f"🛣️ {len(major_roads)} major roads within range ({road_score:.0f}/{MAX_ROAD_POINTS} pts)")
        if construction_roads:
            reasoning.append(f"🚧 {len(construction_roads)} roads under construction ({construction_score:.0f}/{MAX_CONSTRUCTION_POINTS} pts)")
        
        # Airport infrastructure  
        airports = airport_analysis['airports']
        if airports:
            closest_airport = min(airports, key=lambda x: x['distance_km'])
            reasoning.append(f"✈️ Airport: {closest_airport['name']} ({closest_airport['distance_km']:.0f}km, {aviation_score:.0f}/{MAX_AVIATION_POINTS} pts)")
        
        # Railway infrastructure
        railways = railway_analysis['railways']
        if railways:
            reasoning.append(f"🚄 {len(railways)} railway lines ({railway_score:.0f}/{MAX_RAILWAY_POINTS} pts)")
        
        # Overall assessment
        if final_score >= 80:
            reasoning.append("🌟 EXCELLENT infrastructure connectivity")
        elif final_score >= 60:
            reasoning.append("✅ Good infrastructure access")
        elif final_score >= 40:
            reasoning.append("⚠️ Basic infrastructure present")
        else:
            reasoning.append("⚠️ Limited infrastructure - higher risk")
        
        # Determine data source and confidence
        has_osm_data = bool(major_roads or airports or railways or construction_roads)
        data_source = 'osm_live' if has_osm_data else 'regional_fallback'
        data_confidence = 0.85 if has_osm_data else 0.50
        
        return {
            'infrastructure_score': round(final_score, 1),
            'major_features': major_roads + airports + railways,
            'construction_projects': construction_roads,
            'accessibility_score': round(road_score_raw, 1),
            'logistics_score': round((road_score_raw + railway_score_raw) / 2, 1),
            'reasoning': reasoning,
            'data_source': data_source,
            'data_confidence': data_confidence,
            # Component breakdown for transparency
            'component_breakdown': {
                'roads': round(road_score, 1),
                'railways': round(railway_score, 1),
                'aviation': round(aviation_score, 1),
                'construction': round(construction_score, 1),
                'accessibility_adj': round(accessibility_adjustment, 1)
            },
            'component_max': {
                'roads': MAX_ROAD_POINTS,
                'railways': MAX_RAILWAY_POINTS,
                'aviation': MAX_AVIATION_POINTS,
                'construction': MAX_CONSTRUCTION_POINTS
            }
        }

    def _get_regional_infrastructure_fallback(self, region_name: str) -> Dict[str, Any]:
        """
        🆕 IMPROVED: Comprehensive fallback infrastructure scoring using regional knowledge database
        
        Uses detailed regional infrastructure patterns collected from:
        - Government infrastructure reports
        - Local planning documents  
        - Historical OSM data patterns
        - Regional development plans
        """
        
        # Check if region exists in comprehensive database
        if region_name in self.regional_infrastructure_database:
            region_data = self.regional_infrastructure_database[region_name]
            
            # Build detailed reasoning based on infrastructure counts
            reasoning = []
            
            if region_data['highways'] >= 5:
                reasoning.append(f"🛣️ Excellent highway connectivity ({region_data['highways']} major roads)")
            elif region_data['highways'] >= 3:
                reasoning.append(f"🛣️ Good highway access ({region_data['highways']} major roads)")
            elif region_data['highways'] >= 1:
                reasoning.append(f"🛣️ Basic highway access ({region_data['highways']} major roads)")
            else:
                reasoning.append("⚠️ Limited highway infrastructure")
            
            if region_data['ports'] >= 2:
                reasoning.append(f"🚢 Multiple port facilities ({region_data['ports']} ports)")
            elif region_data['ports'] == 1:
                reasoning.append("🚢 Port access available")
            
            if region_data['airports'] >= 1:
                reasoning.append(f"✈️ Airport within range ({region_data['airports']} airports)")
            
            if region_data['railways'] >= 2:
                reasoning.append(f"🚄 Strong railway connectivity ({region_data['railways']} lines)")
            elif region_data['railways'] == 1:
                reasoning.append("🚄 Railway access available")
            
            if not reasoning:
                reasoning.append("📍 Basic regional infrastructure")
            
            reasoning.append("ℹ️ Based on regional infrastructure database (OSM data unavailable)")
            
            return {
                'infrastructure_score': region_data['infra_score'],
                'reasoning': reasoning,
                'data_source': 'regional_fallback',
                'data_confidence': 0.65,  # Moderate-good confidence for known regions
                'major_features': [],
                'construction_projects': [],
                'accessibility_score': region_data['infra_score'],
                'logistics_score': region_data['infra_score']
            }
        
        # Legacy fallback for backward compatibility
        legacy_regional_scores = {
            'solo_expansion': {
                'infrastructure_score': 85,
                'reasoning': ['✈️ Solo Airport expansion planned', '🛣️ Major highway access', '🚄 Railway connectivity']
            },
            'yogyakarta_periurban': {
                'infrastructure_score': 80,
                'reasoning': ['✈️ New International Airport corridor', '🛣️ Ring road development']
            },
            'gunungkidul_east': {
                'infrastructure_score': 70,
                'reasoning': ['🛣️ Coastal highway planned', '🌊 Tourism corridor development']
            },
            'kulonprogo_west': {
                'infrastructure_score': 82,
                'reasoning': ['✈️ New International Airport', '🛣️ Airport connector roads']
            },
            'semarang_industrial': {
                'infrastructure_score': 88,
                'reasoning': ['🚢 Major port access', '🛣️ Industrial highway', '🚄 Railway freight']
            },
            'surakarta_suburbs': {
                'infrastructure_score': 75,
                'reasoning': ['🛣️ Ring road planned', '🏭 Logistics hub development']
            }
        }
        
        if region_name in legacy_regional_scores:
            result = legacy_regional_scores[region_name].copy()
            result['data_source'] = 'regional_fallback'
            result['data_confidence'] = 0.60
            result['major_features'] = []
            result['construction_projects'] = []
            return result
        
        # Unknown region - return neutral baseline with clear warning
        logger.warning(f"⚠️ Region '{region_name}' not found in infrastructure database - using neutral baseline")
        
        return {
            'infrastructure_score': 50,
            'reasoning': [
                '📍 Region not found in infrastructure database',
                '⚠️ OSM API queries failed',
                'ℹ️ Using neutral baseline score (50/100)',
                '💡 Recommendation: Add region to regional_infrastructure_database'
            ],
            'data_source': 'unavailable',
            'data_confidence': 0.30,  # Low confidence for unknown regions
            'major_features': [],
            'construction_projects': [],
            'accessibility_score': 50,
            'logistics_score': 50
        }