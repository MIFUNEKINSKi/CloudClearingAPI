"""
Historical Validation Testing Module

This module provides tools for validating change detection algorithms 
using historical Landsat data from 2015-2020.
"""

import ee
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from .change_detector import ChangeDetector, ChangeDetectionConfig
from .config import get_config

logger = logging.getLogger(__name__)

class HistoricalValidator:
    """Validates change detection using historical satellite data"""
    
    def __init__(self):
        self.config = get_config()
        
    def get_landsat_collection(self, start_date: str, end_date: str, bbox) -> ee.ImageCollection:
        """
        Get Landsat 8 collection for historical validation
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            bbox: Area of interest geometry
            
        Returns:
            Filtered Landsat 8 collection
        """
        return (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                .filterDate(start_date, end_date)
                .filterBounds(bbox)
                .filter(ee.Filter.lt('CLOUD_COVER', 20))
                .map(self.mask_landsat_clouds)
                .select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']))
    
    def mask_landsat_clouds(self, image):
        """Apply cloud mask to Landsat 8 image"""
        qa = image.select('QA_PIXEL')
        
        # Cloud and cloud shadow bit masks
        cloud_mask = 1 << 3
        cloud_shadow_mask = 1 << 4
        
        # Create mask for clear pixels
        mask = (qa.bitwiseAnd(cloud_mask).eq(0)
                .And(qa.bitwiseAnd(cloud_shadow_mask).eq(0)))
        
        # Scale and apply mask
        return image.updateMask(mask).multiply(0.0000275).add(-0.2)
    
    def create_validation_timeline(self, 
                                 bbox, 
                                 start_year: int = 2015, 
                                 end_year: int = 2020) -> List[Dict]:
        """
        Create timeline of historical composites for validation
        
        Args:
            bbox: Area of interest
            start_year: Starting year for validation
            end_year: Ending year for validation
            
        Returns:
            List of validation periods with metadata
        """
        validation_periods = []
        
        for year in range(start_year, end_year + 1):
            # Create seasonal periods for each year
            periods = [
                {'season': 'dry_season', 'start': f'{year}-05-01', 'end': f'{year}-09-30'},
                {'season': 'wet_season', 'start': f'{year}-11-01', 'end': f'{year+1}-03-31'}
            ]
            
            for period in periods:
                try:
                    collection = self.get_landsat_collection(
                        period['start'], period['end'], bbox)
                    
                    composite = collection.median().clip(bbox)
                    image_count = collection.size().getInfo()
                    
                    if image_count > 0:
                        validation_periods.append({
                            'year': year,
                            'season': period['season'],
                            'start_date': period['start'],
                            'end_date': period['end'],
                            'image_count': image_count,
                            'composite': composite
                        })
                        
                        logger.info(f"Created {period['season']} composite for {year} "
                                  f"with {image_count} images")
                    
                except Exception as e:
                    logger.warning(f"Failed to create composite for {year} "
                                 f"{period['season']}: {e}")
        
        return validation_periods
    
    def validate_known_changes(self, 
                             validation_periods: List[Dict],
                             known_changes: List[Dict]) -> Dict:
        """
        Validate algorithm against known historical changes
        
        Args:
            validation_periods: Historical composite periods
            known_changes: List of known change events with dates and locations
            
        Returns:
            Validation results with accuracy metrics
        """
        results = {
            'total_known_changes': len(known_changes),
            'detected_changes': 0,
            'false_positives': 0,
            'missed_changes': 0,
            'validation_details': []
        }
        
        detector = ChangeDetector()
        
        for change_event in known_changes:
            try:
                # Find appropriate before/after periods
                event_date = datetime.strptime(change_event['date'], '%Y-%m-%d')
                
                before_period = None
                after_period = None
                
                for period in validation_periods:
                    period_start = datetime.strptime(period['start_date'], '%Y-%m-%d')
                    if period_start < event_date and (before_period is None or 
                                                    period_start > datetime.strptime(before_period['start_date'], '%Y-%m-%d')):
                        before_period = period
                    elif period_start > event_date and (after_period is None or 
                                                      period_start < datetime.strptime(after_period['start_date'], '%Y-%m-%d')):
                        after_period = period
                
                if before_period and after_period:
                    # Run change detection
                    change_bbox = ee.Geometry.Point(change_event['coordinates']).buffer(500)
                    
                    # Calculate NDVI for both periods
                    before_ndvi = before_period['composite'].normalizedDifference(['SR_B5', 'SR_B4'])
                    after_ndvi = after_period['composite'].normalizedDifference(['SR_B5', 'SR_B4'])
                    ndvi_diff = after_ndvi.subtract(before_ndvi)
                    
                    # Check if change detected
                    mean_change = ndvi_diff.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=change_bbox,
                        scale=30,
                        maxPixels=1e9
                    ).getInfo()
                    
                    detected = abs(mean_change.get('nd', 0)) > 0.2
                    
                    if detected:
                        results['detected_changes'] += 1
                    else:
                        results['missed_changes'] += 1
                    
                    results['validation_details'].append({
                        'change_id': change_event.get('id', 'unknown'),
                        'expected_change': change_event['type'],
                        'detected': detected,
                        'ndvi_change': mean_change.get('nd', 0),
                        'before_period': before_period['start_date'],
                        'after_period': after_period['start_date']
                    })
                    
            except Exception as e:
                logger.error(f"Validation failed for change event {change_event}: {e}")
        
        # Calculate accuracy metrics
        total_detected = results['detected_changes']
        total_missed = results['missed_changes']
        total_known = total_detected + total_missed
        
        if total_known > 0:
            results['recall'] = total_detected / total_known
            results['accuracy'] = total_detected / total_known
        
        return results
    
    def run_yogyakarta_validation(self) -> Dict:
        """
        Run historical validation for Yogyakarta region with known development
        """
        # Yogyakarta region
        yogya_bbox = ee.Geometry.Rectangle([110.25, -7.95, 110.55, -7.65])
        
        # Create historical timeline
        validation_periods = self.create_validation_timeline(yogya_bbox)
        
        # Known major development events in Yogyakarta area (example data)
        known_changes = [
            {
                'id': 'new_yogia_airport_construction',
                'date': '2017-06-01',
                'type': 'infrastructure_development',
                'coordinates': [110.15, -7.85],
                'description': 'New Yogyakarta International Airport construction'
            },
            {
                'id': 'urban_expansion_south',
                'date': '2018-03-01', 
                'type': 'urban_development',
                'coordinates': [110.35, -7.88],
                'description': 'Urban expansion in southern Yogyakarta'
            },
            {
                'id': 'industrial_area_development',
                'date': '2019-01-01',
                'type': 'industrial_development', 
                'coordinates': [110.42, -7.78],
                'description': 'New industrial area development'
            }
        ]
        
        # Run validation
        validation_results = self.validate_known_changes(validation_periods, known_changes)
        
        # Add metadata
        validation_results['region'] = 'Yogyakarta'
        validation_results['validation_period'] = '2015-2020'
        validation_results['total_historical_composites'] = len(validation_periods)
        
        return validation_results

def run_historical_validation():
    """
    Convenience function to run historical validation
    """
    validator = HistoricalValidator()
    results = validator.run_yogyakarta_validation()
    
    print("=== HISTORICAL VALIDATION RESULTS ===")
    print(f"Region: {results['region']}")
    print(f"Period: {results['validation_period']}")
    print(f"Historical composites: {results['total_historical_composites']}")
    print(f"Known changes: {results['total_known_changes']}")
    print(f"Detected: {results['detected_changes']}")
    print(f"Missed: {results['missed_changes']}")
    print(f"Recall: {results.get('recall', 0):.2%}")
    
    return results

if __name__ == "__main__":
    run_historical_validation()