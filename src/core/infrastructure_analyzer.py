"""
Infrastructure Intelligence Module

Integrates real infrastructure data (roads, utilities, planned developments) 
to enhance speculative scoring accuracy beyond heuristics.

Author: CloudClearingAPI Team  
Date: September 2025
"""

import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, box
import numpy as np
from datetime import datetime, timedelta
import ee

# 🆕 v2.8: OSM Infrastructure Caching
from src.core.osm_cache import OSMInfrastructureCache

logger = logging.getLogger(__name__)

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
        # Alternative Overpass API endpoints for failover
        self.osm_fallback_urls = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter"
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
        
        # 🆕 COMPREHENSIVE: Regional fallback database with known infrastructure patterns
        self.regional_infrastructure_database = {
            # Jakarta Metro Area
            'jakarta_north_sprawl': {'infra_score': 95, 'highways': 8, 'ports': 2, 'airports': 2, 'railways': 3},
            'jakarta_south_suburbs': {'infra_score': 90, 'highways': 7, 'ports': 1, 'airports': 2, 'railways': 2},
            'tangerang_bsd_corridor': {'infra_score': 92, 'highways': 7, 'ports': 1, 'airports': 2, 'railways': 1},
            'bekasi_industrial_belt': {'infra_score': 88, 'highways': 6, 'ports': 1, 'airports': 1, 'railways': 2},
            
            # Bandung Area
            'bandung_north_expansion': {'infra_score': 82, 'highways': 5, 'ports': 0, 'airports': 1, 'railways': 2},
            'bandung_periurban': {'infra_score': 78, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'cimahi_expansion': {'infra_score': 75, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            
            # Central Java
            'semarang_suburbs': {'infra_score': 80, 'highways': 5, 'ports': 2, 'airports': 1, 'railways': 2},
            'solo_periphery': {'infra_score': 72, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'yogyakarta_north': {'infra_score': 75, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'yogyakarta_south': {'infra_score': 73, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'magelang_corridor': {'infra_score': 68, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 0},
            'purwokerto_area': {'infra_score': 65, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 1},
            
            # East Java
            'surabaya_west': {'infra_score': 88, 'highways': 6, 'ports': 2, 'airports': 1, 'railways': 2},
            'surabaya_south': {'infra_score': 85, 'highways': 6, 'ports': 1, 'airports': 1, 'railways': 1},
            'malang_suburbs': {'infra_score': 70, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 1},
            'sidoarjo_delta': {'infra_score': 82, 'highways': 5, 'ports': 1, 'airports': 1, 'railways': 1},
            
            # Banten
            'serang_cilegon_industrial': {'infra_score': 85, 'highways': 5, 'ports': 2, 'airports': 1, 'railways': 1},
            'cilegon_corridor': {'infra_score': 83, 'highways': 5, 'ports': 2, 'airports': 0, 'railways': 1},
            'merak_port': {'infra_score': 90, 'highways': 4, 'ports': 3, 'airports': 0, 'railways': 1},
            'anyer_carita_coastal': {'infra_score': 60, 'highways': 2, 'ports': 1, 'airports': 0, 'railways': 0},
            
            # Regional/Coastal Areas
            'cirebon_port_industrial': {'infra_score': 75, 'highways': 4, 'ports': 2, 'airports': 1, 'railways': 1},
            'tegal_industrial': {'infra_score': 68, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'pekalongan_coast': {'infra_score': 65, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'jepara_coast': {'infra_score': 62, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 0},
            'probolinggo_corridor': {'infra_score': 68, 'highways': 3, 'ports': 1, 'airports': 0, 'railways': 1},
            'banyuwangi_ferry': {'infra_score': 70, 'highways': 3, 'ports': 2, 'airports': 0, 'railways': 0},
            'jember_southern_coast': {'infra_score': 58, 'highways': 2, 'ports': 0, 'airports': 0, 'railways': 0},
            'kediri_suburbs': {'infra_score': 65, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 1},
            'blitar_area': {'infra_score': 62, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 1},
            'madiun_suburbs': {'infra_score': 68, 'highways': 3, 'ports': 0, 'airports': 0, 'railways': 1},
            
            # Yogyakarta Special Regions
            'yogyakarta_kulon_progo_airport': {'infra_score': 82, 'highways': 4, 'ports': 0, 'airports': 1, 'railways': 0},
            'bogor_puncak_highland': {'infra_score': 70, 'highways': 4, 'ports': 0, 'airports': 0, 'railways': 0},
        }

    def analyze_infrastructure_context(self, 
                                     bbox: Dict[str, float],
                                     region_name: str) -> Dict[str, Any]:
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
            
            # Cache miss - query OSM API
            logger.info(f"🔴 Cache miss for {region_name} - querying OSM API")
            
            # 🆕 IMPROVED: Expand bbox for infrastructure search (look 50km beyond region for rural areas)
            expanded_bbox = self._expand_bbox(bbox, expansion_km=50)
            
            logger.info(f"📡 Querying OSM infrastructure for {region_name}...")
            
            # Query OpenStreetMap for infrastructure with retry logic
            roads_data = self._query_osm_roads(expanded_bbox)
            airports_data = self._query_osm_airports(expanded_bbox)
            railways_data = self._query_osm_railways(expanded_bbox)
            
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
            
        except Exception as e:
            logger.warning(f"Failed to process cached infrastructure for {region_name}: {e}")
            # Fallback to regional knowledge on cache processing failure
            analysis.update(self._get_regional_infrastructure_fallback(region_name))
        
        return analysis

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

    def _query_osm_roads(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for road infrastructure with retry logic and failover"""
        
        overpass_query = f"""
        [out:json][timeout:45];
        (
          way["highway"~"^(motorway|trunk|primary|secondary)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"~"^(motorway|trunk|primary)_construction$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        return self._query_overpass_with_retry(overpass_query, "roads")

    def _query_osm_airports(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for airports with retry logic and failover"""
        
        overpass_query = f"""
        [out:json][timeout:45];
        (
          way["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["aeroway"="airport"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        return self._query_overpass_with_retry(overpass_query, "airports")

    def _query_osm_railways(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for railway infrastructure with retry logic and failover"""
        
        overpass_query = f"""
        [out:json][timeout:45];
        (
          way["railway"="rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="light_rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="construction"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        return self._query_overpass_with_retry(overpass_query, "railways")
    
    def _query_overpass_with_retry(self, query: str, feature_type: str, 
                                   max_retries: int = 3) -> List[Dict]:
        """
        🆕 IMPROVED: Query Overpass API with exponential backoff retry and failover
        
        Retry strategy:
        - Attempt 1: Primary server, 45s timeout
        - Attempt 2: Primary server, 60s timeout, 2s delay
        - Attempt 3: Fallback server 1, 60s timeout, 4s delay
        - Attempt 4: Fallback server 2, 60s timeout, 8s delay
        """
        import time
        
        # Build list of (url, timeout) pairs to try
        attempts = [
            (self.osm_base_url, 45),
            (self.osm_base_url, 60),
        ]
        # Add fallback servers
        for fallback_url in self.osm_fallback_urls:
            attempts.append((fallback_url, 60))
        
        last_error = None
        
        for attempt_num, (api_url, timeout) in enumerate(attempts, 1):
            try:
                # Apply exponential backoff delay (skip on first attempt)
                if attempt_num > 1:
                    delay = 2 ** (attempt_num - 2)  # 2s, 4s, 8s...
                    logger.info(f"  Retry {attempt_num}/{len(attempts)} for {feature_type} after {delay}s delay...")
                    time.sleep(delay)
                
                logger.debug(f"Querying {api_url} for {feature_type} (timeout: {timeout}s)")
                
                response = requests.post(
                    api_url, 
                    data={'data': query}, 
                    timeout=timeout,
                    headers={'User-Agent': 'CloudClearingAPI/2.0'}
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                elements = data.get('elements', [])
                
                # Success!
                if attempt_num > 1:
                    logger.info(f"  ✅ {feature_type} query succeeded on attempt {attempt_num}")
                
                return elements
                
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout after {timeout}s"
                logger.warning(f"  ⏱️ OSM {feature_type} query timeout (attempt {attempt_num}/{len(attempts)})")
                continue
                
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP error: {e.response.status_code}"
                logger.warning(f"  ❌ OSM {feature_type} HTTP error: {e.response.status_code} (attempt {attempt_num}/{len(attempts)})")
                
                # Rate limit (429) or server error (5xx) - worth retrying
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    continue
                else:
                    # Client error (4xx) - don't retry
                    break
                    
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(f"  ❌ OSM {feature_type} request error: {e} (attempt {attempt_num}/{len(attempts)})")
                continue
                
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON response"
                logger.warning(f"  ❌ OSM {feature_type} invalid JSON (attempt {attempt_num}/{len(attempts)})")
                continue
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.warning(f"  ❌ OSM {feature_type} unexpected error: {e} (attempt {attempt_num}/{len(attempts)})")
                continue
        
        # All attempts failed
        logger.error(f"❌ All {len(attempts)} attempts failed for {feature_type} query. Last error: {last_error}")
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
                
                # Calculate distance to target region
                if road.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in road['geometry']]
                    if len(coords) >= 2:
                        road_line = LineString(coords)
                        distance_km = target_center.distance(road_line) * 111  # Rough km conversion
                        
                        # Apply distance decay
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
                
                # Get airport location
                if airport['type'] == 'node':
                    airport_point = Point(airport['lon'], airport['lat'])
                elif airport.get('geometry'):
                    # For ways, use centroid
                    coords = [(node['lon'], node['lat']) for node in airport['geometry']]
                    if coords:
                        airport_polygon = Polygon(coords) if len(coords) > 2 else Point(coords[0])
                        airport_point = airport_polygon.centroid
                    else:
                        continue
                else:
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
                
                if railway.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in railway['geometry']]
                    if len(coords) >= 2:
                        railway_line = LineString(coords)
                        distance_km = target_center.distance(railway_line) * 111
                        
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
        
        # Roads: Cap at 35 points (typically ~20 major roads = full allocation)
        road_score = min(MAX_ROAD_POINTS, road_score_raw * 0.35)  # Scale down from raw accumulation
        
        # Aviation: Cap at 20 points (1-2 airports = full allocation)
        aviation_score = min(MAX_AVIATION_POINTS, airport_score_raw * 0.20)  # Scale down
        
        # Railways: Cap at 20 points (typically ~10 rail lines = full allocation)
        railway_score = min(MAX_RAILWAY_POINTS, railway_score_raw * 0.20)  # Scale down
        
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