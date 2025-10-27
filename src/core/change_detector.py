"""
CloudClearingAPI - Core Change Detection Module

This module implements the core algorithms for detecting land development changes
using satellite imagery analysis, specifically designed for monitoring around Yogyakarta.

Author: CloudClearingAPI Team
Date: September 2025
"""

import ee  # type: ignore[import]
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import geopandas as gpd
from datetime import datetime, timedelta
import json
import logging
from shapely.geometry import shape, Polygon
from dataclasses import dataclass
from pathlib import Path
from .satellite_image_saver import SatelliteImageSaver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChangeDetectionConfig:
    """Configuration class for change detection parameters"""
    # NDVI thresholds
    ndvi_loss_threshold: float = -0.20
    ndvi_gain_threshold: float = 0.15
    
    # NDBI thresholds  
    ndbi_gain_threshold: float = 0.15
    ndbi_loss_threshold: float = -0.10
    
    # Area thresholds (square meters)
    min_change_area: float = 200.0
    min_road_area: float = 100.0
    min_building_area: float = 50.0
    
    # Morphological parameters
    erosion_kernel_size: int = 2
    dilation_kernel_size: int = 3
    
    # Cloud parameters
    max_cloud_cover: float = 20.0
    cloud_buffer_meters: int = 100
    
    # Advanced cloud masking parameters
    use_s2cloudless: bool = True
    cloud_probability_threshold: int = 50
    cloud_buffer_distance: int = 50
    use_qa60: bool = True
    use_cirrus_mask: bool = True

class SentinelProcessor:
    """Handles Sentinel-2 data processing via Google Earth Engine"""
    
    def __init__(self, config: ChangeDetectionConfig):
        self.config = config
        try:
            # Try to initialize with project from environment or config
            try:
                from .config import get_config
                app_config = get_config()
                if app_config.gee_project:
                    ee.Initialize(project=app_config.gee_project)
                else:
                    ee.Initialize()
            except:
                ee.Initialize()
            logger.info("Google Earth Engine initialized successfully")
            
            # Set default timeout for Earth Engine operations
            # This affects HTTP calls to Earth Engine API
            import socket
            self._original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(60)  # 60 second timeout for all socket operations
            logger.info("Set socket default timeout to 60 seconds")
            
            # Monkey-patch Google API client to reduce retries from 5 to 2
            try:
                import googleapiclient.http  # type: ignore
                if hasattr(googleapiclient.http, '_RETRY_DEFAULT_MAX_RETRIES'):
                    googleapiclient.http._RETRY_DEFAULT_MAX_RETRIES = 2  # type: ignore
                    logger.info("Reduced API retry count from 5 to 2")
            except Exception as e:
                logger.warning(f"Could not reduce retry count: {e}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Earth Engine: {e}")
            raise
        
        # Load s2cloudless collection if available
        try:
            self.s2cloudless = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')  # type: ignore
            self.use_s2cloudless = True
            logger.info("s2cloudless collection loaded successfully")
        except Exception as e:
            logger.warning(f"s2cloudless not available: {e}")
            self.use_s2cloudless = False
        
        # Initialize satellite image saver
        try:
            self.image_saver = SatelliteImageSaver()
            logger.info("📸 Satellite image saver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize satellite image saver: {e}")
            self.image_saver = None
    
    def find_best_available_dates(self, bbox, # type: ignore 
                                 target_end_date: Optional[str] = None,
                                 lookback_days: int = 30) -> Dict[str, Any]:
        """
        Find the best available Sentinel-2 dates by working backwards from target date
        
        Args:
            bbox: Area of interest
            target_end_date: Desired end date (YYYY-MM-DD), defaults to today-7 days
            lookback_days: How many days to look back for available imagery
            
        Returns:
            Dict with 'week_a_start', 'week_b_start', 'actual_images_found' keys
        """
        if not target_end_date:
            target_end_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
        logger.info(f"Finding best available Sentinel-2 dates around {target_end_date}")
        
        target_date = datetime.strptime(target_end_date, '%Y-%m-%d')
        
        # Check for available imagery working backwards
        for days_back in range(0, lookback_days, 7):  # Check weekly intervals
            check_date = target_date - timedelta(days=days_back)
            week_b_start = check_date.strftime('%Y-%m-%d')
            week_a_start = (check_date - timedelta(days=14)).strftime('%Y-%m-%d')
            
            # Test if we have imagery for both periods
            try:
                # Quick test for week B (recent)
                week_b_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')  # type: ignore
                    .filterBounds(bbox)
                    .filterDate(week_b_start, (check_date + timedelta(days=7)).strftime('%Y-%m-%d'))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', self.config.max_cloud_cover))  # type: ignore
                )
                
                # Quick test for week A (baseline)
                week_a_end = check_date - timedelta(days=7)
                week_a_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')  # type: ignore
                    .filterBounds(bbox)
                    .filterDate(week_a_start, week_a_end.strftime('%Y-%m-%d'))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', self.config.max_cloud_cover))  # type: ignore
                )
                
                # Test if collections have images
                week_b_count = week_b_collection.size().getInfo()
                week_a_count = week_a_collection.size().getInfo()
                
                if week_b_count > 0 and week_a_count > 0:
                    logger.info(f"Found available imagery: Week A ({week_a_start}): {week_a_count} images, Week B ({week_b_start}): {week_b_count} images")
                    return {
                        'week_a_start': week_a_start,
                        'week_b_start': week_b_start,
                        'actual_images_found': True,
                        'week_a_count': week_a_count,
                        'week_b_count': week_b_count,
                        'days_back_from_target': days_back
                    }
                    
            except Exception as e:
                logger.debug(f"Error checking dates {week_a_start}/{week_b_start}: {e}")
                continue
                
        # If no good dates found, return the original target dates with a warning
        logger.warning(f"No suitable imagery found within {lookback_days} days of {target_end_date}")
        logger.warning("Returning target dates - may result in empty composites")
        
        week_b_start = target_end_date
        week_a_start = (target_date - timedelta(days=14)).strftime('%Y-%m-%d')
        
        return {
            'week_a_start': week_a_start,
            'week_b_start': week_b_start,
            'actual_images_found': False,
            'week_a_count': 0,
            'week_b_count': 0,
            'days_back_from_target': lookback_days
        }
    
    def mask_s2_clouds_advanced(self, image: ee.Image) -> ee.Image:  # type: ignore
        """
        Advanced cloud masking using s2cloudless + QA60 + cirrus detection
        
        Args:
            image: Sentinel-2 image with QA60 band
            
        Returns:
            Cloud-masked image with scaled surface reflectance values
        """
        # Start with basic QA60 mask
        qa = image.select('QA60')
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11
        
        # Basic cloud and cirrus mask
        qa_mask = (qa.bitwiseAnd(cloud_bit_mask).eq(0)
                  .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0)))
        
        # Enhanced s2cloudless masking if available
        if self.use_s2cloudless:
            try:
                # Get cloud probability for the same image
                cloud_prob = (self.s2cloudless
                            .filterDate(image.date(), image.date().advance(1, 'day'))
                            .filterBounds(image.geometry())
                            .mean())
                
                # Create cloud probability mask (default threshold 50%)
                cloud_threshold = getattr(self.config, 'cloud_probability_threshold', 50)
                s2cloudless_mask = cloud_prob.select('probability').lt(cloud_threshold)
                
                # Buffer cloud mask to catch cloud shadows
                buffer_distance = getattr(self.config, 'cloud_buffer_distance', 50)
                if buffer_distance > 0:
                    cloud_pixels = s2cloudless_mask.Not()
                    buffered_clouds = (cloud_pixels
                                     .fastDistanceTransform(256)
                                     .sqrt()
                                     .multiply(ee.Image.pixelArea().sqrt())
                                     .lt(buffer_distance))
                    s2cloudless_mask = s2cloudless_mask.And(buffered_clouds.Not())
                
                # Combine QA60 and s2cloudless masks
                combined_mask = qa_mask.And(s2cloudless_mask)
                logger.debug("Applied s2cloudless + QA60 cloud masking")
                
            except Exception as e:
                logger.warning(f"s2cloudless masking failed, using QA60 only: {e}")
                combined_mask = qa_mask
        else:
            combined_mask = qa_mask
        
        # Note: B10 (cirrus) not available in harmonized collection
        # QA60 already handles cirrus detection via bit masking
        
        # Scale surface reflectance and apply combined mask
        return image.updateMask(combined_mask).divide(10000)
    
    def mask_s2_clouds(self, image: ee.Image) -> ee.Image:  # type: ignore
        """
        Backward compatibility wrapper - uses advanced masking
        """
        return self.mask_s2_clouds_advanced(image)
    
    def create_weekly_composite(self, 
                              start_date: str, 
                              end_date: str, 
                              bbox: ee.Geometry) -> ee.Image:  # type: ignore
        """
        Create weekly median composite from Sentinel-2 collection
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format  
            bbox: Bounding box geometry
            
        Returns:
            Weekly median composite image
        """
        # Use the harmonized Sentinel-2 collection (replaces deprecated S2_SR)
        # First, let's try without cloud masking to test basic functionality
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')  # type: ignore
                     .filterDate(start_date, end_date)
                     .filterBounds(bbox)
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))  # type: ignore
                     .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12']))  # Only select needed bands
        
        # Create median composite and clip to area
        composite = collection.median().clip(bbox)
        
        # Add image count as metadata
        count = collection.size()
        composite = composite.set('image_count', count)
        
        # Debug: Check if composite has bands
        try:
            band_count = composite.bandNames().size().getInfo()
            if band_count == 0:
                logger.warning(f"Empty composite created for {start_date} to {end_date}")
        except:
            pass  # Don't fail on debug info
        
        logger.info(f"Created composite from {start_date} to {end_date}")
        return composite

class SpectralIndices:
    """Calculate various spectral indices for change detection"""
    
    @staticmethod
    def ndvi(image: ee.Image) -> ee.Image:  # type: ignore
        """
        Calculate Normalized Difference Vegetation Index
        NDVI = (NIR - Red) / (NIR + Red)
        
        Handles empty composites by checking for band availability.
        """
        try:
            # Check if required bands exist
            band_names = image.bandNames()
            band_count = band_names.size()
            
            # If no bands, return constant fallback
            fallback = ee.Image.constant(0.0).rename('NDVI').clip(image.geometry())
            
            # Only calculate NDVI if bands are available
            ndvi_calc = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            # Use conditional to return appropriate result
            result = ee.Algorithms.If(band_count.gt(0), ndvi_calc, fallback)
            return ee.Image(result)
        except Exception as e:
            logger.warning(f"NDVI calculation failed, using fallback: {e}")
            return ee.Image.constant(0.0).rename('NDVI')
    
    @staticmethod  
    def ndbi(image: ee.Image) -> ee.Image:  # type: ignore
        """
        Calculate Normalized Difference Built-up Index
        NDBI = (SWIR - NIR) / (SWIR + NIR)
        
        Handles empty composites by checking for band availability.
        """
        try:
            # Check if required bands exist
            band_names = image.bandNames()
            band_count = band_names.size()
            
            # If no bands, return constant fallback
            fallback = ee.Image.constant(0.0).rename('NDBI').clip(image.geometry())
            
            # Only calculate NDBI if bands are available
            ndbi_calc = image.expression(
                '(SWIR - NIR) / (SWIR + NIR)', {
                    'SWIR': image.select('B11'),
                    'NIR': image.select('B8')
                }).rename('NDBI')
            
            # Use conditional to return appropriate result
            result = ee.Algorithms.If(band_count.gt(0), ndbi_calc, fallback)
            return ee.Image(result)
        except Exception as e:
            logger.warning(f"NDBI calculation failed, using fallback: {e}")
            return ee.Image.constant(0.0).rename('NDBI')
    
    @staticmethod
    def bsi(image: ee.Image) -> ee.Image:  # type: ignore
        """
        Calculate Bare Soil Index
        BSI = ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))
        """
        return image.expression(
            '((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))', {
                'SWIR': image.select('B11'),
                'RED': image.select('B4'),
                'NIR': image.select('B8'),
                'BLUE': image.select('B2')
            }).rename('BSI')
    
    @staticmethod
    def ndwi(image: ee.Image) -> ee.Image:  # type: ignore
        """
        Calculate Normalized Difference Water Index
        NDWI = (Green - NIR) / (Green + NIR)
        """
        return image.normalizedDifference(['B3', 'B8']).rename('NDWI')

class ChangeDetector:
    """Main class for detecting land development changes"""
    
    def __init__(self, config: Optional[ChangeDetectionConfig] = None):
        self.config = config or ChangeDetectionConfig()
        self.processor = SentinelProcessor(self.config)
        self.indices = SpectralIndices()
        
    def detect_weekly_changes(self,
                            week_a_start: Optional[str] = None,
                            week_b_start: Optional[str] = None,
                            bbox = None,  # type: ignore
                            export_results: bool = True,
                            auto_find_dates: bool = True,
                            region_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect changes between two weekly composites with automatic date finding
        
        Args:
            week_a_start: Start date of first week (YYYY-MM-DD), optional if auto_find_dates=True
            week_b_start: Start date of second week (YYYY-MM-DD), optional if auto_find_dates=True
            bbox: Area of interest geometry (can be dict or ee.Geometry)
            export_results: Whether to export results to Google Drive
            auto_find_dates: If True, automatically find best available dates
            
        Returns:
            Dictionary containing change detection results
        """
        # Convert bbox to Earth Engine geometry if it's a dictionary
        if isinstance(bbox, dict):
            bbox_ee = ee.Geometry.Polygon(bbox['coordinates'])
            bbox_dict = bbox
        else:
            bbox_ee = bbox
            bbox_dict = bbox.getInfo() if bbox else None
            
        # Auto-find best available dates if requested
        if auto_find_dates and (not week_a_start or not week_b_start):
            if bbox_ee is None:
                raise ValueError("bbox is required when auto_find_dates=True")
            logger.info("Auto-finding best available Sentinel-2 imagery dates...")
            date_info = self.processor.find_best_available_dates(bbox_ee, week_b_start)
            week_a_start = date_info['week_a_start']
            week_b_start = date_info['week_b_start']
            
            if date_info['actual_images_found']:
                logger.info(f"✅ Using optimized dates: {week_a_start} → {week_b_start}")
                logger.info(f"   Week A: {date_info['week_a_count']} images, Week B: {date_info['week_b_count']} images")
                if date_info['days_back_from_target'] > 0:
                    logger.info(f"   📅 Adjusted {date_info['days_back_from_target']} days back to find available imagery")
            else:
                logger.warning(f"⚠️  Using fallback dates: {week_a_start} → {week_b_start} (may have no imagery)")
        
        # Validate required parameters
        if not week_a_start or not week_b_start or bbox_ee is None:
            raise ValueError("week_a_start, week_b_start, and bbox are required")
            
        logger.info(f"Analyzing changes from {week_a_start} to {week_b_start}")
        
        # Calculate the end dates for each week
        week_a_end = (datetime.strptime(week_a_start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        week_b_end = (datetime.strptime(week_b_start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Create weekly composites
        composite_a = self.processor.create_weekly_composite(
            week_a_start, week_a_end, bbox_ee)
        composite_b = self.processor.create_weekly_composite(
            week_b_start, week_b_end, bbox_ee)
        
        # Calculate spectral indices for both weeks
        ndvi_a = self.indices.ndvi(composite_a)
        ndvi_b = self.indices.ndvi(composite_b)
        ndbi_a = self.indices.ndbi(composite_a) 
        ndbi_b = self.indices.ndbi(composite_b)
        bsi_a = self.indices.bsi(composite_a)
        bsi_b = self.indices.bsi(composite_b)
        
        # Calculate differences
        ndvi_diff = ndvi_b.subtract(ndvi_a).rename('NDVI_DIFF')
        ndbi_diff = ndbi_b.subtract(ndbi_a).rename('NDBI_DIFF')
        bsi_diff = bsi_b.subtract(bsi_a).rename('BSI_DIFF')
        
        # Apply change detection rules
        changes = self._apply_change_rules(ndvi_diff, ndbi_diff, bsi_diff)
        
        # Vectorize changes
        change_vectors = self._vectorize_changes(changes, bbox_ee)
        
        # Get statistics
        stats = self._calculate_statistics(change_vectors, changes)
        
        # Export if requested
        if export_results:
            self._export_results(change_vectors, week_a_start, week_b_start)
        
        # Generate satellite image URLs for investment analysis
        try:
            satellite_images = self._generate_satellite_image_urls(
                composite_a, composite_b, bbox_ee, week_a_start, week_b_start)
        except Exception as e:
            logger.warning(f"Satellite image generation failed: {e}")
            satellite_images = {
                'week_a_date': week_a_start,
                'week_b_date': week_b_start,
                'error': str(e),
                'note': 'Satellite image generation encountered an error'
            }
        
        # 📸 Save satellite images for PDF integration if region_name provided
        saved_images = {}
        if region_name and satellite_images and 'error' not in satellite_images and self.image_saver:
            try:
                saved_images = self.image_saver.save_satellite_images(
                    satellite_images, region_name, week_a_start, week_b_start
                )
                logger.info(f"📸 Saved {len([p for p in saved_images.values() if p])} satellite images for {region_name}")
            except Exception as e:
                logger.warning(f"Failed to save satellite images for {region_name}: {e}")
        elif region_name and not self.image_saver:
            logger.warning(f"Image saver not available, skipping image saving for {region_name}")
        
        return {
            'change_count': stats['polygon_count'],
            'total_area': stats['total_area_m2'],
            'change_types': stats['change_types'],
            'week_a': f"{week_a_start} to {week_a_end}",
            'week_b': f"{week_b_start} to {week_b_end}",
            'bbox': bbox_dict,
            'vectors': change_vectors,
            'satellite_images': satellite_images,
            'saved_images': saved_images  # Local file paths for PDF integration
        }
    
    def _generate_satellite_image_urls(self, composite_a, composite_b, bbox, week_a: str, week_b: str):
        """Generate satellite image visualization URLs for investment analysis"""
        try:
            # Define visualization parameters for different image types
            true_color_viz = {
                'bands': ['B4', 'B3', 'B2'],  # Red, Green, Blue
                'min': 0.0,
                'max': 0.3,
                'gamma': 1.2
            }
            
            false_color_viz = {
                'bands': ['B8', 'B4', 'B3'],  # NIR, Red, Green - highlights vegetation
                'min': 0.0,
                'max': 0.3,
                'gamma': 1.2
            }
            
            # Generate thumbnail URLs for before/after comparison
            week_a_true_color = composite_a.getThumbURL({
                **true_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_b_true_color = composite_b.getThumbURL({
                **true_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_a_false_color = composite_a.getThumbURL({
                **false_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_b_false_color = composite_b.getThumbURL({
                **false_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            # Create NDVI change visualization
            ndvi_a = self.indices.ndvi(composite_a)
            ndvi_b = self.indices.ndvi(composite_b)
            ndvi_diff = ndvi_b.subtract(ndvi_a)
            
            ndvi_change_viz = {
                'min': -0.5,
                'max': 0.5,
                'palette': ['red', 'white', 'green']  # Red=loss, Green=gain
            }
            
            ndvi_change_url = ndvi_diff.getThumbURL({
                **ndvi_change_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            return {
                'week_a_true_color': week_a_true_color,
                'week_b_true_color': week_b_true_color,
                'week_a_false_color': week_a_false_color,
                'week_b_false_color': week_b_false_color,
                'ndvi_change': ndvi_change_url,
                'week_a_date': week_a,
                'week_b_date': week_b,
                'description': {
                    'true_color': 'Natural color satellite imagery (Red, Green, Blue bands)',
                    'false_color': 'False color imagery highlighting vegetation (NIR, Red, Green)',
                    'ndvi_change': 'NDVI change map: Red=vegetation loss, Green=vegetation gain'
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate satellite image URLs: {e}")
            return {
                'error': f"Image generation failed: {str(e)}",
                'week_a_date': week_a,
                'week_b_date': week_b
            }
            # Define visualization parameters for true color and false color
            true_color_viz = {
                'bands': ['B4', 'B3', 'B2'],
                'min': 0.0,
                'max': 0.3,
                'gamma': 1.2
            }
            
            false_color_viz = {
                'bands': ['B8', 'B4', 'B3'],
                'min': 0.0,
                'max': 0.3,
                'gamma': 1.2
            }
            
            # Generate URLs (Note: These are temporary URLs that expire)
            week_a_true_color = composite_a.getThumbURL({
                **true_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_b_true_color = composite_b.getThumbURL({
                **true_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_a_false_color = composite_a.getThumbURL({
                **false_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            week_b_false_color = composite_b.getThumbURL({
                **false_color_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            # Create NDVI visualization to highlight vegetation changes
            ndvi_a = self.indices.ndvi(composite_a)
            ndvi_b = self.indices.ndvi(composite_b)
            ndvi_diff = ndvi_b.subtract(ndvi_a)
            
            ndvi_change_viz = {
                'min': -0.5,
                'max': 0.5,
                'palette': ['red', 'white', 'green']
            }
            
            ndvi_change_url = ndvi_diff.getThumbURL({
                **ndvi_change_viz,
                'region': bbox,
                'dimensions': 512,
                'format': 'png'
            })
            
            return {
                'week_a_true_color': week_a_true_color,
                'week_b_true_color': week_b_true_color,
                'week_a_false_color': week_a_false_color,
                'week_b_false_color': week_b_false_color,
                'ndvi_change': ndvi_change_url,
                'week_a_date': week_a,
                'week_b_date': week_b,
                'description': {
                    'true_color': 'Natural color satellite imagery (Red, Green, Blue bands)',
                    'false_color': 'False color imagery highlighting vegetation (NIR, Red, Green)',
                    'ndvi_change': 'NDVI change map: Red=vegetation loss, Green=vegetation gain'
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate satellite image URLs: {e}")
            return {
                'error': f"Image generation failed: {str(e)}",
                'week_a_date': week_a,
                'week_b_date': week_b
            }
    
    def _apply_change_rules(self, 
                          ndvi_diff: ee.Image,  # type: ignore
                          ndbi_diff: ee.Image,  # type: ignore
                          bsi_diff: ee.Image) -> ee.Image:  # type: ignore
        """Apply heuristic rules to identify different change types"""
        
        # Rule 1: Vegetation loss + built-up gain = Development
        development = (ndvi_diff.lt(self.config.ndvi_loss_threshold)
                      .And(ndbi_diff.gt(self.config.ndbi_gain_threshold)))
        
        # Rule 2: Significant bare soil increase = Land clearing
        clearing = bsi_diff.gt(0.20)
        
        # Rule 3: NDBI increase with linear morphology = Roads
        road_candidate = (ndbi_diff.gt(0.10)
                         .And(ndvi_diff.lt(-0.10)))
        
        # Combine change types (use different pixel values for each type)
        changes = (development.multiply(1)
                  .add(clearing.multiply(2))
                  .add(road_candidate.multiply(3)))
        
        return changes.selfMask()
    
    def _vectorize_changes(self, 
                          changes: ee.Image,  # type: ignore
                          bbox: ee.Geometry) -> ee.FeatureCollection:  # type: ignore
        """Convert change raster to vector polygons with timeout handling"""
        
        try:
            # Use higher tileScale to reduce memory/computation
            # This processes smaller tiles at a time
            vectors = changes.reduceToVectors(
                geometry=bbox,
                scale=10,
                geometryType='polygon',
                eightConnected=False,
                labelProperty='change_type',
                maxPixels=int(1e9),
                tileScale=4  # Increased from 2 to reduce computation load
            )
        except Exception as e:
            logger.warning(f"Failed to vectorize changes at scale 10, trying scale 20: {e}")
            # Fallback to coarser resolution if computation fails
            vectors = changes.reduceToVectors(
                geometry=bbox,
                scale=20,
                geometryType='polygon',
                eightConnected=False,
                labelProperty='change_type',
                maxPixels=int(1e9),
                tileScale=4
            )
        
        # Add area calculation to each polygon
        def add_area(feature):
            # Add error margin (1 meter) for geometry operations
            area = feature.geometry().area(maxError=1)
            return feature.set('area_m2', area)
        
        vectors = vectors.map(add_area)
        
        # Filter by minimum area
        vectors = vectors.filter(ee.Filter.gte('area_m2', 
                                              self.config.min_change_area))
        
        return vectors
    
    def _calculate_statistics(self, 
                            vectors: ee.FeatureCollection,  # type: ignore
                            changes: ee.Image) -> Dict[str, Any]:  # type: ignore
        """Calculate summary statistics for detected changes with timeout handling"""
        
        import signal
        from functools import wraps
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Earth Engine computation timed out")
        
        def with_timeout(seconds):
            def decorator(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    # Set timeout for macOS/Linux
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(seconds)
                    try:
                        result = func(*args, **kwargs)
                        signal.alarm(0)
                        return result
                    except TimeoutError:
                        logger.warning(f"{func.__name__} timed out after {seconds} seconds")
                        raise
                    finally:
                        signal.signal(signal.SIGALRM, old_handler)
                return wrapper
            return decorator
        
        @with_timeout(60)  # 60 second timeout per operation
        def get_polygon_count():
            return vectors.size().getInfo()
        
        @with_timeout(60)
        def get_total_area():
            def sum_areas(feature, previous):
                return ee.Number(previous).add(feature.get('area_m2'))
            total_area = vectors.iterate(sum_areas, 0)
            return ee.Number(total_area).getInfo()
        
        @with_timeout(60)
        def get_change_types():
            return vectors.aggregate_histogram('change_type').getInfo()
        
        try:
            # Count polygons with timeout
            polygon_count = get_polygon_count()
            
            # Calculate total area with timeout
            total_area_m2 = get_total_area()
            
            # Count change types with timeout
            change_types = get_change_types()
            
            return {
                'polygon_count': polygon_count,
                'total_area_m2': total_area_m2,
                'change_types': change_types
            }
        except TimeoutError as e:
            logger.error(f"Statistics calculation timed out: {e}")
            # Return minimal stats on timeout
            return {
                'polygon_count': 0,
                'total_area_m2': 0.0,
                'change_types': {},
                'error': 'computation_timeout'
            }
        except Exception as e:
            logger.error(f"Statistics calculation failed: {e}")
            return {
                'polygon_count': 0,
                'total_area_m2': 0.0,
                'change_types': {},
                'error': str(e)
            }
    
    def _export_results(self, 
                       vectors: ee.FeatureCollection,  # type: ignore
                       week_a: str, 
                       week_b: str) -> None:
        """Export change vectors to Google Drive"""
        
        description = f'yogya_changes_{week_a}_to_{week_b}'
        
        task = ee.batch.Export.table.toDrive(
            collection=vectors,
            description=description,
            folder='CloudClearingAPI_Results',
            fileFormat='GeoJSON'
        )
        
        task.start()
        logger.info(f"Export task started: {description}")
        logger.info(f"Task status: {task.status()}")

def main():
    """Example usage of the ChangeDetector"""
    
    # Configuration
    config = ChangeDetectionConfig(
        ndvi_loss_threshold=-0.15,
        ndbi_gain_threshold=0.12,
        min_change_area=150.0
    )
    
    # Initialize detector
    detector = ChangeDetector(config)
    
    # Define area of interest (Yogyakarta region)
    bbox = ee.Geometry.Rectangle([110.25, -7.95, 110.55, -7.65])
    
    # Analyze recent changes (adjust dates as needed)
    results = detector.detect_weekly_changes(
        week_a_start='2025-09-01',
        week_b_start='2025-09-08', 
        bbox=bbox,
        export_results=True
    )
    
    # Print results
    print(f"\n🔍 Change Detection Results:")
    print(f"📊 Changes detected: {results['change_count']} polygons")
    print(f"📏 Total affected area: {results['total_area']:.2f} m²")
    print(f"📅 Analysis period: {results['week_a']} → {results['week_b']}")
    print(f"🗺️  Change types: {results['change_types']}")

if __name__ == "__main__":
    main()