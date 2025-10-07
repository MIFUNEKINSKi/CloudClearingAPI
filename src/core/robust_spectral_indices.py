#!/usr/bin/env python3
"""
Enhanced change detector with robust empty composite handling.
"""

import ee
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RobustSpectralIndices:
    """
    Spectral indices calculation with robust error handling for empty composites.
    """
    
    @staticmethod
    def safe_ndvi(image: ee.Image, fallback_value: float = 0.0) -> ee.Image:
        """
        Calculate NDVI with fallback for empty composites.
        
        Args:
            image: Earth Engine image
            fallback_value: Value to use if bands are missing
            
        Returns:
            NDVI image or constant image if calculation fails
        """
        try:
            # Check if required bands exist
            band_names = image.bandNames()
            has_b8 = band_names.contains('B8')
            has_b4 = band_names.contains('B4')
            
            def calculate_ndvi():
                return image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            
            def create_fallback():
                return ee.Image.constant(fallback_value).rename('NDVI').clip(image.geometry())
            
            # Use conditional to handle missing bands
            ndvi = ee.Algorithms.If(
                has_b8.And(has_b4),
                calculate_ndvi(),
                create_fallback()
            )
            
            return ee.Image(ndvi)
            
        except Exception as e:
            logger.warning(f"NDVI calculation failed, using fallback: {e}")
            return ee.Image.constant(fallback_value).rename('NDVI')
    
    @staticmethod
    def safe_ndbi(image: ee.Image, fallback_value: float = 0.0) -> ee.Image:
        """
        Calculate NDBI with fallback for empty composites.
        
        Args:
            image: Earth Engine image
            fallback_value: Value to use if bands are missing
            
        Returns:
            NDBI image or constant image if calculation fails
        """
        try:
            band_names = image.bandNames()
            has_b11 = band_names.contains('B11')
            has_b8 = band_names.contains('B8')
            
            def calculate_ndbi():
                return image.expression(
                    '(SWIR - NIR) / (SWIR + NIR)', {
                        'SWIR': image.select('B11'),
                        'NIR': image.select('B8')
                    }).rename('NDBI')
            
            def create_fallback():
                return ee.Image.constant(fallback_value).rename('NDBI').clip(image.geometry())
            
            ndbi = ee.Algorithms.If(
                has_b11.And(has_b8),
                calculate_ndbi(),
                create_fallback()
            )
            
            return ee.Image(ndbi)
            
        except Exception as e:
            logger.warning(f"NDBI calculation failed, using fallback: {e}")
            return ee.Image.constant(fallback_value).rename('NDBI')
    
    @staticmethod
    def check_composite_validity(image: ee.Image) -> Dict[str, Any]:
        """
        Check if a composite has valid data.
        
        Args:
            image: Earth Engine image to check
            
        Returns:
            Dictionary with validity information
        """
        try:
            band_names = image.bandNames().getInfo()
            pixel_count = image.select(band_names[0] if band_names else []).reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=image.geometry(),
                scale=30,
                maxPixels=1e6
            ).getInfo()
            
            return {
                'valid': len(band_names) > 0,
                'band_count': len(band_names),
                'band_names': band_names,
                'has_pixels': any(count > 0 for count in pixel_count.values()) if pixel_count else False,
                'pixel_count': pixel_count
            }
            
        except Exception as e:
            logger.error(f"Error checking composite validity: {e}")
            return {
                'valid': False,
                'band_count': 0,
                'band_names': [],
                'has_pixels': False,
                'error': str(e)
            }

def enhance_change_detector_with_robust_handling():
    """
    Create a patch for the change detector to handle empty composites robustly.
    """
    
    patch_code = '''
# Enhanced change detection with robust empty composite handling

def robust_detect_changes(self, start_date_a: str, end_date_a: str, 
                         start_date_b: str, end_date_b: str,
                         geometry) -> Dict[str, Any]:
    """
    Detect changes between two time periods with robust error handling.
    """
    try:
        logger.info(f"Analyzing changes from {start_date_a} to {start_date_b}")
        
        # Create composites
        composite_a = self.create_weekly_composite(start_date_a, end_date_a, geometry)
        composite_b = self.create_weekly_composite(start_date_b, end_date_b, geometry)
        
        logger.info(f"Created composite from {start_date_a} to {end_date_a}")
        logger.info(f"Created composite from {start_date_b} to {end_date_b}")
        
        # Check composite validity
        validity_a = RobustSpectralIndices.check_composite_validity(composite_a)
        validity_b = RobustSpectralIndices.check_composite_validity(composite_b)
        
        if not validity_a['valid'] or not validity_b['valid']:
            logger.warning(f"Empty composites detected - A: {validity_a['valid']}, B: {validity_b['valid']}")
            return {
                'total_changes': 0,
                'change_areas': [],
                'composite_validity': {
                    'period_a': validity_a,
                    'period_b': validity_b
                },
                'status': 'no_data_available',
                'message': 'Insufficient satellite data for change detection'
            }
        
        # Calculate indices with robust handling
        ndvi_a = RobustSpectralIndices.safe_ndvi(composite_a)
        ndvi_b = RobustSpectralIndices.safe_ndvi(composite_b)
        
        ndbi_a = RobustSpectralIndices.safe_ndbi(composite_a)
        ndbi_b = RobustSpectralIndices.safe_ndbi(composite_b)
        
        # Calculate changes
        ndvi_change = ndvi_b.subtract(ndvi_a).rename('ndvi_change')
        ndbi_change = ndbi_b.subtract(ndbi_a).rename('ndbi_change')
        
        # Detect significant changes
        vegetation_loss = ndvi_change.lt(self.config.ndvi_loss_threshold)
        infrastructure_gain = ndbi_change.gt(self.config.ndbi_gain_threshold)
        
        # Combine change indicators
        significant_changes = vegetation_loss.Or(infrastructure_gain)
        
        # Convert to features and count
        change_vectors = significant_changes.selfMask().reduceToVectors(
            geometryType='polygon',
            reducer=ee.Reducer.countEvery(),
            scale=30,
            maxPixels=1e8
        )
        
        # Export task for detailed analysis
        task_id = f"robust_changes_{start_date_a}_to_{start_date_b}"
        task = ee.batch.Export.table.toDrive(
            collection=change_vectors,
            description=task_id,
            folder='earth_engine_exports'
        )
        task.start()
        logger.info(f"Export task started: {task_id}")
        
        # Count changes
        change_count = change_vectors.size().getInfo()
        
        return {
            'total_changes': change_count,
            'change_areas': [],  # Will be populated after export completes
            'composite_validity': {
                'period_a': validity_a,
                'period_b': validity_b
            },
            'indices': {
                'ndvi_change_mean': ndvi_change.reduceRegion(ee.Reducer.mean(), geometry, 30).getInfo(),
                'ndbi_change_mean': ndbi_change.reduceRegion(ee.Reducer.mean(), geometry, 30).getInfo()
            },
            'status': 'success',
            'task_id': task_id
        }
        
    except Exception as e:
        logger.error(f"Robust change detection failed: {e}")
        return {
            'total_changes': 0,
            'change_areas': [],
            'status': 'error',
            'error': str(e),
            'message': 'Change detection failed due to technical error'
        }
'''
    
    return patch_code

def test_robust_spectral_indices():
    """Test the robust spectral indices with different scenarios."""
    
    print("Testing robust spectral indices...")
    
    # Initialize Earth Engine
    try:
        ee.Initialize(project='gen-lang-client-0401113271')
        print("✓ Earth Engine initialized")
    except Exception as e:
        print(f"✗ Earth Engine initialization failed: {e}")
        return
    
    # Test with empty image
    print("\\n1. Testing with empty image...")
    empty_image = ee.Image.constant(0).select([])  # Image with no bands
    
    try:
        ndvi_result = RobustSpectralIndices.safe_ndvi(empty_image)
        print(f"✓ NDVI fallback successful: {ndvi_result.bandNames().getInfo()}")
    except Exception as e:
        print(f"✗ NDVI fallback failed: {e}")
    
    try:
        ndbi_result = RobustSpectralIndices.safe_ndbi(empty_image)
        print(f"✓ NDBI fallback successful: {ndbi_result.bandNames().getInfo()}")
    except Exception as e:
        print(f"✗ NDBI fallback failed: {e}")
    
    # Test with valid Sentinel-2 image
    print("\\n2. Testing with valid Sentinel-2 image...")
    point = ee.Geometry.Point([110.3695, -7.7956])
    
    try:
        s2_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                   .filterBounds(point)
                   .filterDate('2024-06-01', '2024-06-30')
                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                   .first())
        
        if s2_image:
            validity = RobustSpectralIndices.check_composite_validity(s2_image)
            print(f"✓ Composite validity check: {validity}")
            
            if validity['valid']:
                ndvi_result = RobustSpectralIndices.safe_ndvi(s2_image)
                ndbi_result = RobustSpectralIndices.safe_ndbi(s2_image)
                print(f"✓ NDVI calculation successful: {ndvi_result.bandNames().getInfo()}")
                print(f"✓ NDBI calculation successful: {ndbi_result.bandNames().getInfo()}")
            else:
                print("✗ No valid data available for test location")
        else:
            print("✗ No Sentinel-2 images found for test")
            
    except Exception as e:
        print(f"✗ Valid image test failed: {e}")
    
    print("\\n✅ Robust spectral indices testing completed")

if __name__ == '__main__':
    test_robust_spectral_indices()