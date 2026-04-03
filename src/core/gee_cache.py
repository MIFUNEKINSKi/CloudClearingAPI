"""
Google Earth Engine Image Caching System

Caches satellite imagery and analysis results to reduce API calls and improve performance.
Similar to OSM cache, but specialized for GEE image collections and change detection results.

Cache Strategy:
- 14-day TTL (longer than OSM due to satellite revisit frequency)
- Stores both metadata (JSON) and processed imagery (PNG)
- Cache key: region_name + date_range + indices
- Automatic cleanup of expired entries

Author: CloudClearingAPI Team
Date: October 2025
Version: 2.9.0 (CCAPI-27.5)
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import base64

logger = logging.getLogger(__name__)


@dataclass
class GEECacheMetadata:
    """Metadata for cached GEE imagery"""
    region_name: str
    date_range_start: str
    date_range_end: str
    indices_used: list  # ['NDVI', 'NDBI', 'BSI']
    cache_timestamp: str
    cloud_coverage_pct: float
    total_changes: int
    vegetation_loss_pixels: int
    construction_activity_pixels: int
    bare_soil_pixels: int
    area_affected_m2: float
    
    # Image file paths (relative to cache dir)
    week_a_image_path: Optional[str] = None
    week_b_image_path: Optional[str] = None
    
    # Analysis metadata
    confidence: float = 1.0
    data_source: str = "sentinel-2"


class GEEImageCache:
    """
    Caching system for Google Earth Engine imagery and change detection results.
    
    Similar architecture to OSMInfrastructureCache but optimized for satellite data:
    - Longer TTL (14 days vs 7 days) due to satellite revisit frequency
    - Stores both metadata and image files
    - Cache key includes date range and indices used
    """
    
    def __init__(self, cache_dir: str = "./cache/gee", ttl_days: int = 14):
        """
        Initialize GEE cache.
        
        Args:
            cache_dir: Directory for cache storage
            ttl_days: Time-to-live in days (default 14 days)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_days = ttl_days
        self.ttl = timedelta(days=ttl_days)
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized GEE cache: dir={cache_dir}, TTL={ttl_days} days")
    
    def _generate_cache_key(
        self,
        region_name: str,
        date_range_start: str,
        date_range_end: str,
        indices: list = None
    ) -> str:
        """
        Generate unique cache key from region + date range + indices.
        
        Args:
            region_name: Region identifier
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            indices: List of indices used (e.g., ['NDVI', 'NDBI', 'BSI'])
        
        Returns:
            Cache key (MD5 hash)
        """
        if indices is None:
            indices = ['NDVI', 'NDBI', 'BSI']
        
        # Sort indices for consistent hashing
        indices_str = '_'.join(sorted(indices))
        
        # Create composite key
        key_string = f"{region_name}_{date_range_start}_{date_range_end}_{indices_str}"
        
        # Generate MD5 hash for filename safety
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return cache_key
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get path to cache metadata file"""
        return self.cache_dir / f"{cache_key}_metadata.json"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Check if cache file exists and is within TTL.
        
        Args:
            cache_file: Path to cache metadata file
        
        Returns:
            True if cache is valid (exists and fresh)
        """
        if not cache_file.exists():
            return False
        
        # Check file age
        file_modified = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_modified
        
        if age > self.ttl:
            logger.debug(f"Cache expired: {cache_file.name}, age={age.days} days")
            return False
        
        return True
    
    def check_cache(
        self,
        region_name: str,
        date_range_start: str,
        date_range_end: str,
        indices: list = None
    ) -> Optional[GEECacheMetadata]:
        """
        Check if valid cached data exists for this query.
        
        Args:
            region_name: Region identifier
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            indices: List of indices used
        
        Returns:
            GEECacheMetadata if cache hit, None if cache miss
        """
        cache_key = self._generate_cache_key(
            region_name, date_range_start, date_range_end, indices
        )
        cache_file = self._get_cache_file_path(cache_key)
        
        # Check if cache exists and is valid
        if not self._is_cache_valid(cache_file):
            return None
        
        # Load and parse cache metadata
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            metadata = GEECacheMetadata(**cache_data)
            
            # Calculate cache age for logging
            cache_timestamp = datetime.fromisoformat(metadata.cache_timestamp)
            age_hours = (datetime.now() - cache_timestamp).total_seconds() / 3600
            
            logger.info(
                f"✅ GEE cache HIT: {region_name} "
                f"({date_range_start} to {date_range_end}), "
                f"age={age_hours:.1f}h, changes={metadata.total_changes}"
            )
            
            return metadata
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache file corrupted: {cache_file.name}, error={e}")
            # Delete corrupted cache
            cache_file.unlink(missing_ok=True)
            return None
    
    def save_cache(
        self,
        region_name: str,
        date_range_start: str,
        date_range_end: str,
        indices: list,
        change_detection_result: Dict[str, Any],
        week_a_image: Optional[bytes] = None,
        week_b_image: Optional[bytes] = None
    ) -> None:
        """
        Save GEE imagery and analysis results to cache.
        
        Args:
            region_name: Region identifier
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            indices: List of indices used
            change_detection_result: Dict with change detection analysis
            week_a_image: Optional PNG bytes for week A composite
            week_b_image: Optional PNG bytes for week B composite
        """
        cache_key = self._generate_cache_key(
            region_name, date_range_start, date_range_end, indices
        )
        
        # Save images if provided
        week_a_path = None
        week_b_path = None
        
        if week_a_image:
            week_a_path = f"{cache_key}_week_a.png"
            image_file = self.cache_dir / week_a_path
            with open(image_file, 'wb') as f:
                f.write(week_a_image)
        
        if week_b_image:
            week_b_path = f"{cache_key}_week_b.png"
            image_file = self.cache_dir / week_b_path
            with open(image_file, 'wb') as f:
                f.write(week_b_image)
        
        # Create metadata object
        metadata = GEECacheMetadata(
            region_name=region_name,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            indices_used=indices,
            cache_timestamp=datetime.now().isoformat(),
            cloud_coverage_pct=change_detection_result.get('cloud_coverage_pct', 0),
            total_changes=change_detection_result.get('total_changes', 0),
            vegetation_loss_pixels=change_detection_result.get('vegetation_loss_pixels', 0),
            construction_activity_pixels=change_detection_result.get('construction_activity_pixels', 0),
            bare_soil_pixels=change_detection_result.get('bare_soil_pixels', 0),
            area_affected_m2=change_detection_result.get('area_affected_m2', 0),
            week_a_image_path=week_a_path,
            week_b_image_path=week_b_path,
            confidence=change_detection_result.get('confidence', 1.0)
        )
        
        # Save metadata JSON
        cache_file = self._get_cache_file_path(cache_key)
        with open(cache_file, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
        
        logger.info(
            f"💾 GEE cache SAVED: {region_name} "
            f"({date_range_start} to {date_range_end}), "
            f"changes={metadata.total_changes}, "
            f"images={'yes' if week_a_image else 'no'}"
        )
    
    def get_cached_images(
        self,
        cache_metadata: GEECacheMetadata
    ) -> Tuple[Optional[bytes], Optional[bytes]]:
        """
        Retrieve cached image files.
        
        Args:
            cache_metadata: Metadata from check_cache()
        
        Returns:
            Tuple of (week_a_image_bytes, week_b_image_bytes)
        """
        week_a_bytes = None
        week_b_bytes = None
        
        if cache_metadata.week_a_image_path:
            image_file = self.cache_dir / cache_metadata.week_a_image_path
            if image_file.exists():
                with open(image_file, 'rb') as f:
                    week_a_bytes = f.read()
        
        if cache_metadata.week_b_image_path:
            image_file = self.cache_dir / cache_metadata.week_b_image_path
            if image_file.exists():
                with open(image_file, 'rb') as f:
                    week_b_bytes = f.read()
        
        return week_a_bytes, week_b_bytes
    
    def cleanup_expired(self) -> int:
        """
        Remove cache entries older than TTL.
        
        Returns:
            Number of entries cleaned up
        """
        cleaned = 0
        
        for cache_file in self.cache_dir.glob("*_metadata.json"):
            if not self._is_cache_valid(cache_file):
                # Get cache key to delete associated images
                cache_key = cache_file.stem.replace('_metadata', '')
                
                # Delete metadata
                cache_file.unlink(missing_ok=True)
                cleaned += 1
                
                # Delete associated images
                for img_file in self.cache_dir.glob(f"{cache_key}_*.png"):
                    img_file.unlink(missing_ok=True)
        
        if cleaned > 0:
            logger.info(f"🧹 Cleaned up {cleaned} expired GEE cache entries")
        
        return cleaned
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats (total_entries, total_size_mb, oldest_entry_days)
        """
        metadata_files = list(self.cache_dir.glob("*_metadata.json"))
        
        total_size = 0
        oldest_age = timedelta(0)
        
        for cache_file in metadata_files:
            total_size += cache_file.stat().st_size
            
            # Check associated images
            cache_key = cache_file.stem.replace('_metadata', '')
            for img_file in self.cache_dir.glob(f"{cache_key}_*.png"):
                total_size += img_file.stat().st_size
            
            # Check age
            file_modified = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - file_modified
            if age > oldest_age:
                oldest_age = age
        
        return {
            'total_entries': len(metadata_files),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_entry_days': oldest_age.days,
            'cache_directory': str(self.cache_dir)
        }


# Singleton instance for global use
_gee_cache_instance = None


def get_gee_cache(cache_dir: str = "./cache/gee", ttl_days: int = 14) -> GEEImageCache:
    """
    Get or create singleton GEE cache instance.
    
    Args:
        cache_dir: Cache directory
        ttl_days: Time-to-live in days
    
    Returns:
        GEEImageCache singleton instance
    """
    global _gee_cache_instance
    
    if _gee_cache_instance is None:
        _gee_cache_instance = GEEImageCache(cache_dir=cache_dir, ttl_days=ttl_days)
    
    return _gee_cache_instance
