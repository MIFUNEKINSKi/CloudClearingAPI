#!/usr/bin/env python3
"""
Robust imagery handler that checks data availability and provides fallbacks
for satellite imagery display issues.
"""

import ee
import requests
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RobustImageryHandler:
    """
    Handles satellite imagery with robust error checking and fallbacks.
    """
    
    def __init__(self):
        """Initialize the imagery handler."""
        self.session = requests.Session()
        
    def check_data_availability(self, region: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Check data availability for a region and time period.
        
        Args:
            region: Region configuration with geometry
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with availability information
        """
        try:
            # Create geometry
            if 'coordinates' in region:
                geometry = ee.Geometry.Polygon(region['coordinates'])
            else:
                geometry = ee.Geometry.Point([region['center']['lng'], region['center']['lat']]).buffer(region.get('buffer', 1000))
            
            # Check Sentinel-2 collection
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(geometry)
                         .filterDate(start_date, end_date)
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
            
            # Get collection info
            size = collection.size().getInfo()
            
            if size == 0:
                logger.warning(f"No Sentinel-2 data available for {region['name']} between {start_date} and {end_date}")
                return {
                    'available': False,
                    'count': 0,
                    'reason': 'No cloud-free images available',
                    'alternative_dates': self._suggest_alternative_dates(geometry, start_date, end_date)
                }
            
            # Get date range of available data
            dates = collection.aggregate_array('system:time_start').getInfo()
            available_dates = [datetime.fromtimestamp(d/1000).strftime('%Y-%m-%d') for d in dates]
            
            return {
                'available': True,
                'count': size,
                'available_dates': available_dates,
                'first_date': min(available_dates),
                'last_date': max(available_dates)
            }
            
        except Exception as e:
            logger.error(f"Error checking data availability: {e}")
            return {
                'available': False,
                'count': 0,
                'reason': f'Error: {str(e)}',
                'alternative_dates': []
            }
    
    def _suggest_alternative_dates(self, geometry: ee.Geometry, start_date: str, end_date: str) -> List[str]:
        """
        Suggest alternative dates with available data.
        
        Args:
            geometry: Earth Engine geometry
            start_date: Original start date
            end_date: Original end date
            
        Returns:
            List of alternative date ranges
        """
        try:
            alternatives = []
            
            # Check 6 months before and after
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            for months_offset in [-6, -3, 3, 6]:
                alt_start = start_dt + timedelta(days=months_offset * 30)
                alt_end = end_dt + timedelta(days=months_offset * 30)
                
                collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                             .filterBounds(geometry)
                             .filterDate(alt_start.strftime('%Y-%m-%d'), alt_end.strftime('%Y-%m-%d'))
                             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
                
                size = collection.size().getInfo()
                if size > 0:
                    alternatives.append({
                        'start_date': alt_start.strftime('%Y-%m-%d'),
                        'end_date': alt_end.strftime('%Y-%m-%d'),
                        'available_images': size
                    })
                    
            return alternatives[:3]  # Return top 3 alternatives
            
        except Exception as e:
            logger.error(f"Error suggesting alternative dates: {e}")
            return []
    
    def create_robust_composite(self, region: Dict[str, Any], start_date: str, end_date: str, 
                               image_type: str = 'true_color') -> Optional[ee.Image]:
        """
        Create a composite image with robust error handling.
        
        Args:
            region: Region configuration
            start_date: Start date
            end_date: End date
            image_type: Type of image ('true_color', 'ndvi', 'infrastructure')
            
        Returns:
            Earth Engine image or None if failed
        """
        try:
            # Create geometry
            if 'coordinates' in region:
                geometry = ee.Geometry.Polygon(region['coordinates'])
            else:
                geometry = ee.Geometry.Point([region['center']['lng'], region['center']['lat']]).buffer(region.get('buffer', 1000))
            
            # Get collection with multiple fallback strategies
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(geometry)
                         .filterDate(start_date, end_date))
            
            # Try different cloud cover thresholds
            for cloud_threshold in [10, 30, 50, 80]:
                filtered_collection = collection.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
                size = filtered_collection.size().getInfo()
                
                if size > 0:
                    logger.info(f"Found {size} images with <{cloud_threshold}% cloud cover")
                    
                    if image_type == 'true_color':
                        composite = (filtered_collection
                                   .median()
                                   .select(['B4', 'B3', 'B2'])
                                   .multiply(0.0001)
                                   .clamp(0, 0.3)
                                   .multiply(255/0.3))
                    
                    elif image_type == 'ndvi':
                        composite = (filtered_collection
                                   .median()
                                   .normalizedDifference(['B8', 'B4'])
                                   .rename('NDVI'))
                    
                    elif image_type == 'infrastructure':
                        composite = (filtered_collection
                                   .median()
                                   .expression(
                                       '(SWIR1 - NIR) / (SWIR1 + NIR)',
                                       {'NIR': collection.select('B8'), 'SWIR1': collection.select('B11')}
                                   ).rename('NDBI'))
                    
                    return composite
            
            logger.warning(f"No suitable images found for {region['name']} between {start_date} and {end_date}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating composite: {e}")
            return None
    
    def get_robust_thumbnail_url(self, image: ee.Image, region: Dict[str, Any], 
                                image_type: str = 'true_color') -> Optional[str]:
        """
        Get thumbnail URL with robust parameters.
        
        Args:
            image: Earth Engine image
            region: Region configuration
            image_type: Type of image
            
        Returns:
            Thumbnail URL or None if failed
        """
        try:
            # Create geometry
            if 'coordinates' in region:
                geometry = ee.Geometry.Polygon(region['coordinates'])
            else:
                geometry = ee.Geometry.Point([region['center']['lng'], region['center']['lat']]).buffer(region.get('buffer', 1000))
            
            # Get bounds
            bounds = geometry.bounds().getInfo()
            
            # Set visualization parameters based on image type
            if image_type == 'true_color':
                vis_params = {
                    'min': 0,
                    'max': 255,
                    'bands': ['B4', 'B3', 'B2'],
                    'dimensions': 512,
                    'region': bounds,
                    'format': 'png'
                }
            elif image_type == 'ndvi':
                vis_params = {
                    'min': -1,
                    'max': 1,
                    'palette': ['red', 'yellow', 'green'],
                    'dimensions': 512,
                    'region': bounds,
                    'format': 'png'
                }
            elif image_type == 'infrastructure':
                vis_params = {
                    'min': -1,
                    'max': 1,
                    'palette': ['blue', 'white', 'red'],
                    'dimensions': 512,
                    'region': bounds,
                    'format': 'png'
                }
            
            # Get thumbnail URL
            url = image.getThumbURL(vis_params)
            
            # Test the URL
            response = self.session.head(url, timeout=10)
            if response.status_code == 200:
                return url
            else:
                logger.warning(f"Thumbnail URL returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting thumbnail URL: {e}")
            return None
    
    def generate_fallback_summary(self, region: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Generate a summary when imagery is not available.
        
        Args:
            region: Region configuration
            start_date: Start date
            end_date: End date
            
        Returns:
            Fallback summary dictionary
        """
        availability = self.check_data_availability(region, start_date, end_date)
        
        summary = {
            'region_name': region['name'],
            'requested_period': f"{start_date} to {end_date}",
            'data_available': availability['available'],
            'message': 'Satellite imagery not available for requested time period',
            'reason': availability.get('reason', 'Unknown'),
            'suggestions': []
        }
        
        if availability.get('alternative_dates'):
            summary['suggestions'] = [
                f"Try {alt['start_date']} to {alt['end_date']} ({alt['available_images']} images available)"
                for alt in availability['alternative_dates']
            ]
        
        return summary


def test_robust_imagery():
    """Test the robust imagery handler."""
    print("Testing robust imagery handler...")
    
    # Initialize Earth Engine
    try:
        ee.Initialize(project='gen-lang-client-0401113271')
        print("✓ Earth Engine initialized")
    except Exception as e:
        print(f"✗ Earth Engine initialization failed: {e}")
        return
    
    # Test region
    region = {
        'name': 'Yogyakarta Urban',
        'center': {'lat': -7.7956, 'lng': 110.3695},
        'buffer': 5000
    }
    
    handler = RobustImageryHandler()
    
    # Check data availability
    print("\nChecking data availability...")
    availability = handler.check_data_availability(region, '2024-06-01', '2024-06-30')
    print(f"Data available: {availability['available']}")
    if availability['available']:
        print(f"Image count: {availability['count']}")
        print(f"Date range: {availability['first_date']} to {availability['last_date']}")
    else:
        print(f"Reason: {availability['reason']}")
        if availability.get('alternative_dates'):
            print("Alternative periods:")
            for alt in availability['alternative_dates']:
                print(f"  {alt['start_date']} to {alt['end_date']} ({alt['available_images']} images)")
    
    # Try to create composite
    print("\nCreating robust composite...")
    composite = handler.create_robust_composite(region, '2024-06-01', '2024-06-30', 'true_color')
    
    if composite:
        print("✓ Composite created successfully")
        
        # Try to get thumbnail
        url = handler.get_robust_thumbnail_url(composite, region, 'true_color')
        if url:
            print(f"✓ Thumbnail URL generated: {url[:100]}...")
        else:
            print("✗ Failed to generate thumbnail URL")
    else:
        print("✗ Failed to create composite")
        
        # Generate fallback summary
        fallback = handler.generate_fallback_summary(region, '2024-06-01', '2024-06-30')
        print("\nFallback summary:")
        print(json.dumps(fallback, indent=2))


if __name__ == '__main__':
    test_robust_imagery()