"""
Sentinel-1 SAR Change Detection Module
CloudClearingAPI - v2.9

Detects ground surface changes using Sentinel-1 SAR (Synthetic Aperture Radar).
SAR sees through clouds, operates day/night, and detects:
- Construction activity (increased surface roughness)
- Land clearing (decreased vegetation backscatter)  
- Road/infrastructure building (linear backscatter changes)

Complements Sentinel-2 optical analysis for year-round coverage.

Band usage:
- VV (Vertical-Vertical): Sensitive to soil moisture and surface roughness
- VH (Vertical-Horizontal): Sensitive to vegetation structure
- VV/VH ratio change: Best indicator of urbanization/construction
"""

import ee  # type: ignore[import]
import json
import hashlib
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SARChangeResult:
    """Result from SAR change detection analysis"""
    region_name: str
    sar_change_pixels: int          # Total pixels with significant backscatter change
    construction_pixels: int        # Pixels indicating construction (VV increase + VH decrease)
    clearing_pixels: int            # Pixels indicating land clearing (VH decrease)
    period_a: str                   # Baseline period
    period_b: str                   # Recent period
    period_a_images: int            # Number of SAR images in period A
    period_b_images: int            # Number of SAR images in period B
    mean_vv_change_db: float        # Mean VV backscatter change (dB)
    mean_vh_change_db: float        # Mean VH backscatter change (dB)
    success: bool
    error_message: Optional[str] = None


class SARChangeDetector:
    """
    Detects land development changes using Sentinel-1 SAR backscatter analysis.
    
    Methodology:
    1. Create monthly median composites of VV and VH backscatter
    2. Calculate change (dB difference) between baseline and recent periods
    3. Classify changes:
       - VV increase + VH decrease = construction/urbanization
       - VH decrease only = vegetation clearing
       - VV increase only = soil disturbance / grading
    4. Count significant change pixels above threshold
    """
    
    def __init__(self, 
                 vv_change_threshold_db: float = 2.0,
                 vh_change_threshold_db: float = -1.5,
                 construction_vv_threshold: float = 1.5,
                 construction_vh_threshold: float = -1.0,
                 cache_dir: str = "./cache/sar",
                 cache_ttl_days: int = 14):
        """
        Args:
            vv_change_threshold_db: Min VV change (dB) to flag as significant (default 2.0)
            vh_change_threshold_db: Min VH change (dB) for clearing detection (default -1.5)
            construction_vv_threshold: VV increase for construction classification
            construction_vh_threshold: VH decrease for construction classification
            cache_dir: Directory for SAR result caching
            cache_ttl_days: Cache time-to-live in days (default 14)
        """
        self.vv_threshold = vv_change_threshold_db
        self.vh_threshold = vh_change_threshold_db
        self.construction_vv_threshold = construction_vv_threshold
        self.construction_vh_threshold = construction_vh_threshold
        
        # Cache setup (mirrors gee_cache.py pattern)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(days=cache_ttl_days)
        
        logger.info(f"🛰️ SAR Change Detector initialized "
                   f"(VV threshold: {vv_change_threshold_db}dB, VH threshold: {vh_change_threshold_db}dB, "
                   f"cache TTL: {cache_ttl_days}d)")
    
    def _get_cache_key(self, region_name: str, period_a_start: str, period_b_end: str) -> str:
        """Generate MD5 cache key from region + date range"""
        key_string = f"sar_{region_name}_{period_a_start}_{period_b_end}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _check_cache(self, region_name: str, period_a_start: str, period_b_end: str) -> Optional[SARChangeResult]:
        """Check for cached SAR result"""
        cache_key = self._get_cache_key(region_name, period_a_start, period_b_end)
        cache_file = self.cache_dir / f"{cache_key}_sar.json"
        
        if not cache_file.exists():
            return None
        
        # Check TTL
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > self.cache_ttl:
            logger.debug(f"SAR cache expired for {region_name} (age: {file_age.days}d)")
            cache_file.unlink(missing_ok=True)
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            result = SARChangeResult(**data)
            age_hours = file_age.total_seconds() / 3600
            logger.info(f"✅ SAR cache HIT for {region_name} ({age_hours:.1f}h old, "
                       f"{result.sar_change_pixels:,} changes)")
            return result
        except Exception as e:
            logger.warning(f"SAR cache corrupted for {region_name}: {e}")
            cache_file.unlink(missing_ok=True)
            return None
    
    def _save_cache(self, result: SARChangeResult, period_a_start: str, period_b_end: str) -> None:
        """Save SAR result to cache"""
        cache_key = self._get_cache_key(result.region_name, period_a_start, period_b_end)
        cache_file = self.cache_dir / f"{cache_key}_sar.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(asdict(result), f, indent=2)
            logger.info(f"💾 SAR cache SAVED for {result.region_name} "
                       f"({result.sar_change_pixels:,} changes)")
        except Exception as e:
            logger.warning(f"Failed to save SAR cache for {result.region_name}: {e}")

    def cleanup_expired(self) -> int:
        """Remove expired SAR cache files. Returns count of files removed."""
        removed = 0
        if not self.cache_dir.exists():
            return removed
        for cache_file in self.cache_dir.glob("*_sar.json"):
            try:
                file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_age > self.cache_ttl:
                    cache_file.unlink(missing_ok=True)
                    removed += 1
            except Exception as e:
                logger.warning(f"Failed to clean up {cache_file}: {e}")
        if removed > 0:
            logger.info(f"🧹 SAR cache cleanup: removed {removed} expired files")
        return removed

    def detect_sar_changes(self,
                           bbox: Dict[str, Any],
                           region_name: str,
                           period_a_start: str,
                           period_a_end: str,
                           period_b_start: str,
                           period_b_end: str) -> SARChangeResult:
        """
        Detect changes between two periods using Sentinel-1 SAR data.
        Uses cache to avoid redundant GEE queries on subsequent runs.
        
        Args:
            bbox: Bounding box dict with north/south/east/west keys
            region_name: Name of the region
            period_a_start: Baseline period start (YYYY-MM-DD)
            period_a_end: Baseline period end (YYYY-MM-DD)
            period_b_start: Recent period start (YYYY-MM-DD)
            period_b_end: Recent period end (YYYY-MM-DD)
            
        Returns:
            SARChangeResult with change statistics
        """
        # CHECK CACHE FIRST
        cached = self._check_cache(region_name, period_a_start, period_b_end)
        if cached:
            return cached
        
        logger.info(f"🛰️ SAR analysis for {region_name}: {period_a_start}→{period_a_end} vs {period_b_start}→{period_b_end}")
        
        try:
            # Create Earth Engine geometry from bbox
            bbox_ee = ee.Geometry.Rectangle([
                bbox['west'], bbox['south'], 
                bbox['east'], bbox['north']
            ])
            
            # Get Sentinel-1 GRD collections for both periods
            s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
                .filter(ee.Filter.eq('instrumentMode', 'IW')) \
                .filterBounds(bbox_ee)
            
            # Period A (baseline) composite
            period_a_col = s1_collection.filterDate(period_a_start, period_a_end)
            period_a_count = period_a_col.size().getInfo()
            
            # Period B (recent) composite
            period_b_col = s1_collection.filterDate(period_b_start, period_b_end)
            period_b_count = period_b_col.size().getInfo()
            
            logger.info(f"   SAR images: Period A={period_a_count}, Period B={period_b_count}")
            
            if period_a_count == 0 or period_b_count == 0:
                logger.warning(f"   ⚠️ Insufficient SAR data for {region_name}")
                return SARChangeResult(
                    region_name=region_name,
                    sar_change_pixels=0,
                    construction_pixels=0,
                    clearing_pixels=0,
                    period_a=f"{period_a_start} to {period_a_end}",
                    period_b=f"{period_b_start} to {period_b_end}",
                    period_a_images=period_a_count,
                    period_b_images=period_b_count,
                    mean_vv_change_db=0.0,
                    mean_vh_change_db=0.0,
                    success=False,
                    error_message=f"Insufficient SAR images: A={period_a_count}, B={period_b_count}"
                )
            
            # Create median composites (SAR data is in dB, median is robust to outliers)
            composite_a = period_a_col.select(['VV', 'VH']).median().clip(bbox_ee)
            composite_b = period_b_col.select(['VV', 'VH']).median().clip(bbox_ee)
            
            # Calculate backscatter change (dB)
            vv_change = composite_b.select('VV').subtract(composite_a.select('VV')).rename('VV_change')
            vh_change = composite_b.select('VH').subtract(composite_a.select('VH')).rename('VH_change')
            
            # Classify change types — explicitly rename so reduceRegion keys
            # are unambiguous (previously all three masks inherited 'VV_change'
            # via .gt()/.And()/.Or() and GEE auto-renamed duplicates to
            # 'VV_change_1', breaking stats.get('VV') / stats.get('VH') which
            # silently returned 0. construction_pixels and clearing_pixels
            # have been zero on every run since the SAR detector shipped).
            #
            # Construction: VV increases (harder surface) AND VH decreases (less vegetation)
            construction_mask = (
                vv_change.gt(self.construction_vv_threshold)
                .And(vh_change.lt(self.construction_vh_threshold))
                .rename('construction')
            )

            # Land clearing: VH decreases significantly (vegetation removal)
            clearing_mask = vh_change.lt(self.vh_threshold).rename('clearing')

            # Any significant change: either VV or VH exceeds threshold
            any_change_mask = (
                vv_change.abs().gt(self.vv_threshold)
                .Or(vh_change.abs().gt(abs(self.vh_threshold)))
                .rename('any_change')
            )

            # Reduce to get pixel counts
            stats = any_change_mask.addBands(construction_mask).addBands(clearing_mask) \
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=bbox_ee,
                    scale=10,  # Sentinel-1 is 10m resolution
                    maxPixels=1e8,
                    bestEffort=True
                ).getInfo()

            sar_change_pixels = int(stats.get('any_change', 0) or 0)
            construction_pixels = int(stats.get('construction', 0) or 0)
            clearing_pixels = int(stats.get('clearing', 0) or 0)
            
            # Get mean change values for reporting
            mean_stats = vv_change.addBands(vh_change).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=bbox_ee,
                scale=10,
                maxPixels=1e8,
                bestEffort=True
            ).getInfo()
            
            mean_vv_change = float(mean_stats.get('VV_change', 0) or 0)
            mean_vh_change = float(mean_stats.get('VH_change', 0) or 0)
            
            logger.info(f"   🛰️ SAR results: {sar_change_pixels:,} change pixels "
                       f"({construction_pixels:,} construction, {clearing_pixels:,} clearing)")
            logger.info(f"   📊 Mean backscatter change: VV={mean_vv_change:+.2f}dB, VH={mean_vh_change:+.2f}dB")
            
            result = SARChangeResult(
                region_name=region_name,
                sar_change_pixels=sar_change_pixels,
                construction_pixels=construction_pixels,
                clearing_pixels=clearing_pixels,
                period_a=f"{period_a_start} to {period_a_end}",
                period_b=f"{period_b_start} to {period_b_end}",
                period_a_images=period_a_count,
                period_b_images=period_b_count,
                mean_vv_change_db=mean_vv_change,
                mean_vh_change_db=mean_vh_change,
                success=True
            )
            
            # SAVE TO CACHE
            self._save_cache(result, period_a_start, period_b_end)
            
            return result
            
        except Exception as e:
            logger.error(f"   ❌ SAR analysis failed for {region_name}: {e}")
            return SARChangeResult(
                region_name=region_name,
                sar_change_pixels=0,
                construction_pixels=0,
                clearing_pixels=0,
                period_a=f"{period_a_start} to {period_a_end}",
                period_b=f"{period_b_start} to {period_b_end}",
                period_a_images=0,
                period_b_images=0,
                mean_vv_change_db=0.0,
                mean_vh_change_db=0.0,
                success=False,
                error_message=str(e)
            )
    
    def fuse_optical_and_sar(self,
                             optical_changes: int,
                             sar_result: SARChangeResult,
                             optical_weight: float = 0.6,
                             sar_weight: float = 0.4) -> Dict[str, Any]:
        """
        Fuse optical (Sentinel-2) and SAR (Sentinel-1) change counts into
        a single combined satellite signal for scoring.
        
        Strategy:
        - If both have data: weighted combination (60% optical, 40% SAR)
        - If only optical: use optical (traditional behavior)
        - If only SAR: use SAR (cloud season fallback - this is the key benefit)
        
        Args:
            optical_changes: Change count from Sentinel-2 optical analysis
            sar_result: Result from SAR change detection
            optical_weight: Weight for optical signal (default 0.6)
            sar_weight: Weight for SAR signal (default 0.4)
            
        Returns:
            Dict with fused_changes, source, and breakdown
        """
        optical_available = optical_changes > 0
        sar_available = sar_result.success and sar_result.sar_change_pixels > 0
        
        if optical_available and sar_available:
            # Both available: weighted fusion with magnitude-cap on SAR.
            # Bug fix 2026-04-27: the nominal 60/40 weighting was meaningless
            # in practice. SAR change counts run 100-1000× larger than optical
            # for the same region (different per-pixel sensitivity, sub-period
            # accumulation), so SAR * 0.4 still dominated optical * 0.6 by
            # ~400×. Spot check showed all 65 regions' fused signal was
            # 99%+ SAR. Capping SAR at SAR_MAX_RATIO × optical preserves
            # SAR as a corroborating signal without letting it drown optical.
            SAR_MAX_RATIO = 20  # SAR can contribute at most 20× the optical count
            sar_capped = min(sar_result.sar_change_pixels, SAR_MAX_RATIO * optical_changes)
            sar_was_capped = sar_capped < sar_result.sar_change_pixels
            fused = int(optical_changes * optical_weight + sar_capped * sar_weight)
            source = 'optical+sar_fusion'
            confidence_boost = 0.10  # Higher confidence with dual-sensor

            cap_note = f' (SAR capped to {sar_capped:,} from {sar_result.sar_change_pixels:,})' if sar_was_capped else ''
            logger.info(
                f"   🔗 Sensor fusion: {optical_changes:,} optical + {sar_result.sar_change_pixels:,} SAR "
                f"→ {fused:,} fused (weights: {optical_weight:.0%}/{sar_weight:.0%}){cap_note}"
            )
            
        elif optical_available:
            # Optical only (SAR failed or no changes)
            fused = optical_changes
            source = 'optical_only'
            confidence_boost = 0.0
            
            logger.info(f"   📡 Optical only: {fused:,} changes (SAR unavailable)")
            
        elif sar_available:
            # SAR only (optical failed due to clouds, OR optical legitimately
            # returned zero changes — both end up here when optical_changes==0).
            # Bug fix 2026-04-25: previously fused = sar_pixels uncapped, which
            # let port/coastal regions (Merak 4.6M SAR pixels) saturate the
            # activity log-scale at ~38 and then evade the SAR-only confidence
            # cap (because data_source provenance was also wrong — see
            # automated_monitor.py fix). Cap sar_only at SAR_ONLY_MAX so the
            # signal stays visible in the JSON for debugging without
            # dominating the score.
            SAR_ONLY_MAX = 500_000  # ~comparable scale to post-cap fusion mode
            sar_capped = min(sar_result.sar_change_pixels, SAR_ONLY_MAX)
            sar_was_capped = sar_capped < sar_result.sar_change_pixels
            fused = sar_capped
            source = 'sar_only'
            confidence_boost = 0.05  # Slight boost over no data at all

            cap_note = f' (capped from {sar_result.sar_change_pixels:,})' if sar_was_capped else ''
            logger.info(f"   🛰️ SAR fallback: {fused:,} changes (optical unavailable or 0){cap_note}")
            
        else:
            # Neither available
            fused = 0
            source = 'no_satellite_data'
            confidence_boost = 0.0
            
            logger.warning(f"   ⚠️ No satellite data available (both optical and SAR failed)")
        
        return {
            'fused_changes': fused,
            'source': source,
            'optical_changes': optical_changes,
            'sar_changes': sar_result.sar_change_pixels if sar_result.success else 0,
            'sar_construction': sar_result.construction_pixels if sar_result.success else 0,
            'sar_clearing': sar_result.clearing_pixels if sar_result.success else 0,
            'confidence_boost': confidence_boost,
            'sar_available': sar_available,
            'optical_available': optical_available,
            'sar_images_used': sar_result.period_b_images if sar_result.success else 0,
            'mean_vv_change_db': sar_result.mean_vv_change_db,
            'mean_vh_change_db': sar_result.mean_vh_change_db,
        }
