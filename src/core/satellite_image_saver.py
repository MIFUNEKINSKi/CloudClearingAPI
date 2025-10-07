#!/usr/bin/env python3
"""
Satellite Image Saver for Weekly Reports

Downloads and saves satellite images from Google Earth Engine URLs
for integration into PDF reports and local storage.
"""

import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import hashlib
import time

logger = logging.getLogger(__name__)

class SatelliteImageSaver:
    """
    Downloads and saves satellite images from Earth Engine URLs
    """
    
    def __init__(self, base_output_dir: str = "output/satellite_images"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.weekly_dir = self.base_output_dir / "weekly"
        self.thumbnails_dir = self.base_output_dir / "thumbnails"
        self.weekly_dir.mkdir(exist_ok=True)
        self.thumbnails_dir.mkdir(exist_ok=True)
    
    def save_satellite_images(self, satellite_images: Dict[str, Any], 
                            region_name: str, 
                            week_a: str, 
                            week_b: str) -> Dict[str, str]:
        """
        Download and save satellite images locally
        
        Args:
            satellite_images: Dict containing Earth Engine image URLs
            region_name: Name of the region being analyzed
            week_a: Start week date
            week_b: End week date
            
        Returns:
            Dict mapping image types to local file paths
        """
        if 'error' in satellite_images:
            logger.warning(f"Cannot save satellite images for {region_name}: {satellite_images['error']}")
            return {}
        
        logger.info(f"📸 Saving satellite images for {region_name} ({week_a} to {week_b})")
        
        # Create region-specific directory
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        region_dir = self.weekly_dir / f"{region_name}_{date_str}"
        region_dir.mkdir(exist_ok=True)
        
        saved_images = {}
        
        # Define image types to save
        image_mappings = {
            'week_a_true_color': f"{region_name}_before_true_color_{week_a.replace('-', '')}.png",
            'week_b_true_color': f"{region_name}_after_true_color_{week_b.replace('-', '')}.png",
            'week_a_false_color': f"{region_name}_before_false_color_{week_a.replace('-', '')}.png",
            'week_b_false_color': f"{region_name}_after_false_color_{week_b.replace('-', '')}.png",
            'ndvi_change': f"{region_name}_ndvi_change_{week_a.replace('-', '')}_to_{week_b.replace('-', '')}.png"
        }
        
        for url_key, filename in image_mappings.items():
            if url_key in satellite_images:
                url = satellite_images[url_key]
                if url and url.startswith('http'):
                    try:
                        file_path = region_dir / filename
                        success = self._download_image(url, file_path)
                        
                        if success:
                            saved_images[url_key] = str(file_path)
                            logger.info(f"   ✅ Saved {url_key}: {filename}")
                        else:
                            logger.warning(f"   ❌ Failed to save {url_key}")
                            saved_images[url_key] = None
                    except Exception as e:
                        logger.error(f"Error saving {url_key}: {e}")
                        saved_images[url_key] = None
                else:
                    logger.warning(f"Invalid URL for {url_key}: {url}")
                    saved_images[url_key] = None
        
        # Save metadata
        metadata = {
            'region_name': region_name,
            'week_a': week_a,
            'week_b': week_b,
            'saved_timestamp': datetime.now().isoformat(),
            'saved_images': saved_images,
            'original_urls': satellite_images
        }
        
        metadata_path = region_dir / "metadata.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"📁 Saved {len([p for p in saved_images.values() if p])} images to {region_dir}")
        
        return saved_images
    
    def _download_image(self, url: str, file_path: Path, max_retries: int = 3) -> bool:
        """
        Download image from URL with retry logic
        """
        for attempt in range(max_retries):
            try:
                # Add timeout and proper headers
                headers = {
                    'User-Agent': 'CloudClearingAPI/1.0 (Satellite Image Downloader)'
                }
                
                response = requests.get(url, timeout=30, headers=headers)
                
                if response.status_code == 200:
                    # Check if response contains actual image data
                    if len(response.content) < 1000:  # Suspiciously small image
                        logger.warning(f"Image too small ({len(response.content)} bytes), may be error page")
                        return False
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    if 'image' not in content_type and 'png' not in content_type:
                        logger.warning(f"Unexpected content type: {content_type}")
                        # Continue anyway, sometimes EE returns images without proper headers
                    
                    # Save the image
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Verify file was saved
                    if file_path.exists() and file_path.stat().st_size > 0:
                        return True
                    else:
                        logger.warning(f"File save verification failed for {file_path}")
                        return False
                        
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error downloading image: {e}")
                return False
        
        return False
    
    def create_image_summary(self, saved_images: Dict[str, str], region_name: str) -> Dict[str, Any]:
        """
        Create summary of saved images for reporting
        """
        summary = {
            'region_name': region_name,
            'images_saved': 0,
            'images_failed': 0,
            'available_images': {},
            'pdf_ready': False
        }
        
        for image_type, file_path in saved_images.items():
            if file_path and Path(file_path).exists():
                summary['images_saved'] += 1
                summary['available_images'][image_type] = {
                    'path': file_path,
                    'exists': True,
                    'size_bytes': Path(file_path).stat().st_size
                }
            else:
                summary['images_failed'] += 1
                summary['available_images'][image_type] = {
                    'path': file_path,
                    'exists': False,
                    'error': 'Download failed or file not found'
                }
        
        # Determine if we have enough images for PDF integration
        critical_images = ['week_a_true_color', 'week_b_true_color']
        pdf_ready = all(
            summary['available_images'].get(img, {}).get('exists', False) 
            for img in critical_images
        )
        summary['pdf_ready'] = pdf_ready
        
        return summary
    
    def get_latest_images_for_region(self, region_name: str) -> Optional[Dict[str, str]]:
        """
        Get the most recent saved images for a region
        """
        region_dirs = list(self.weekly_dir.glob(f"{region_name}_*"))
        if not region_dirs:
            return None
        
        # Sort by creation time (newest first)
        latest_dir = max(region_dirs, key=lambda d: d.stat().st_ctime)
        
        metadata_path = latest_dir / "metadata.json"
        if metadata_path.exists():
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata.get('saved_images', {})
        
        return None
    
    def cleanup_old_images(self, days_to_keep: int = 30):
        """
        Clean up old satellite images to save disk space
        """
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        cleaned_count = 0
        for region_dir in self.weekly_dir.iterdir():
            if region_dir.is_dir() and region_dir.stat().st_ctime < cutoff_time:
                import shutil
                shutil.rmtree(region_dir)
                cleaned_count += 1
                logger.info(f"🗑️ Cleaned up old images: {region_dir.name}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} old image directories")

def test_image_saver():
    """
    Test the satellite image saver
    """
    print("🧪 Testing Satellite Image Saver")
    print("=" * 50)
    
    saver = SatelliteImageSaver()
    
    # Test with mock data (in real use, this comes from change_detector)
    mock_satellite_images = {
        'week_a_true_color': 'https://earthengine.googleapis.com/...',  # Mock URL
        'week_b_true_color': 'https://earthengine.googleapis.com/...',  # Mock URL
        'ndvi_change': 'https://earthengine.googleapis.com/...',  # Mock URL
        'week_a_date': '2025-09-21',
        'week_b_date': '2025-09-28'
    }
    
    print(f"📁 Output directory: {saver.base_output_dir}")
    print(f"📸 Ready to save satellite images")
    print(f"🎯 Integration with PDF reports: Enabled")
    
    return saver

if __name__ == '__main__':
    test_image_saver()