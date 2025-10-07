"""
Earth Engine Authenticated Image Viewer

This script creates locally cached satellite images that can be viewed without authentication issues.
"""

import json
import ee
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EEImageDownloader:
    """
    Download and cache Google Earth Engine images locally
    """
    
    def __init__(self):
        """Initialize Earth Engine if not already done"""
        try:
            # Import config to get project ID
            from .config import get_config
            config = get_config()
            project_id = config.gee_project
            
            ee.Initialize(project=project_id)
            logger.info(f"Earth Engine initialized with project: {project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            raise
    
    def download_image(self, image_url: str, output_path: str, timeout: int = 30) -> bool:
        """
        Download an Earth Engine image URL to local file
        
        Args:
            image_url: Google Earth Engine thumbnail URL
            output_path: Local path to save the image
            timeout: Request timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make authenticated request through Earth Engine
            response = requests.get(image_url, timeout=timeout)
            
            if response.status_code == 200:
                # Check if response is actually an image
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type.lower():
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Downloaded image: {output_path}")
                    return True
                else:
                    logger.warning(f"Response is not an image: {content_type}")
                    return False
            else:
                logger.warning(f"Failed to download image: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return False
    
    def create_local_imagery_cache(self, json_file_path: str, output_dir: Optional[str] = None) -> str:
        """
        Create local cache of all satellite images from monitoring results
        
        Args:
            json_file_path: Path to monitoring JSON file
            output_dir: Directory to save cached images
            
        Returns:
            Path to the cached images directory
        """
        # Load monitoring data
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Setup output directory
        if output_dir is None:
            cache_dir = Path('./output/cached_images')
        else:
            cache_dir = Path(output_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_dir = cache_dir / f"session_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        regions_analyzed = data.get('regions_analyzed', [])
        cached_count = 0
        total_images = 0
        
        for region in regions_analyzed:
            satellite_images = region.get('satellite_images', {})
            if not satellite_images:
                continue
            
            region_name = region['region_name']
            region_dir = session_dir / region_name
            region_dir.mkdir(exist_ok=True)
            
            # Download each image type
            image_types = {
                'week_a_true_color': 'before_true_color.png',
                'week_b_true_color': 'after_true_color.png', 
                'week_a_false_color': 'before_false_color.png',
                'week_b_false_color': 'after_false_color.png',
                'ndvi_change': 'ndvi_change.png'
            }
            
            for img_type, filename in image_types.items():
                img_url = satellite_images.get(img_type)
                if img_url:
                    total_images += 1
                    output_path = region_dir / filename
                    
                    if self.download_image(img_url, str(output_path)):
                        cached_count += 1
                    else:
                        # Create placeholder image info
                        placeholder_path = region_dir / f"{filename}.txt"
                        with open(placeholder_path, 'w') as f:
                            f.write(f"Original URL: {img_url}\\n")
                            f.write(f"Failed to download at: {datetime.now()}\\n")
                            f.write("This image requires Google Earth Engine authentication.\\n")
        
        logger.info(f"Cached {cached_count}/{total_images} images in {session_dir}")
        
        # Create an index HTML file
        self._create_cached_viewer(data, session_dir)
        
        return str(session_dir)
    
    def _create_cached_viewer(self, data: Dict[str, Any], cache_dir: Path):
        """Create HTML viewer for cached images"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudClearing Cached Imagery Viewer</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #2E86AB, #A23B72);
            color: white;
            border-radius: 10px;
        }}
        .region-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 30px;
        }}
        .region-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .region-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #2E86AB;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .cached-image {{
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            cursor: pointer;
        }}
        .image-label {{
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
        }}
        .not-available {{
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            min-height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ CloudClearing Cached Imagery</h1>
        <p>Local cached satellite images | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
    
    <div class="region-grid">
"""
        
        regions_analyzed = data.get('regions_analyzed', [])
        regions_with_imagery = [r for r in regions_analyzed if r.get('satellite_images', {}).get('week_a_true_color')]
        
        for region in regions_with_imagery:
            region_name = region['region_name']
            region_title = region_name.replace('_', ' ').title()
            
            html_content += f"""
        <div class="region-card">
            <div class="region-title">{region_title}</div>
            <p>Changes: {region.get('change_count', 0):,} | Area: {region.get('total_area_m2', 0)/10000:.1f} hectares</p>
            
            <div class="image-grid">
                <div>
                    <div class="image-label">🌍 Before (True Color)</div>
"""
            
            # Check if cached images exist
            region_dir = cache_dir / region_name
            image_files = {
                'before_true_color.png': '🌍 Before (True Color)',
                'after_true_color.png': '🌍 After (True Color)', 
                'ndvi_change.png': '🌱 NDVI Change'
            }
            
            for filename, label in image_files.items():
                image_path = region_dir / filename
                if image_path.exists():
                    relative_path = f"{region_name}/{filename}"
                    html_content += f"""
                    <img src="{relative_path}" alt="{label}" class="cached-image" onclick="window.open('{relative_path}', '_blank')">
"""
                else:
                    html_content += f"""
                    <div class="not-available">
                        <div>
                            <p>🔒 Image not cached</p>
                            <small>Authentication required</small>
                        </div>
                    </div>
"""
            
            html_content += """
                </div>
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # Write HTML file
        html_file = cache_dir / "index.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Created cached imagery viewer: {html_file}")

def create_cached_imagery_viewer(json_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Convenience function to create cached imagery viewer
    
    Args:
        json_file_path: Path to monitoring JSON file
        output_dir: Directory to save cached images
        
    Returns:
        Path to cached images directory
    """
    downloader = EEImageDownloader()
    return downloader.create_local_imagery_cache(json_file_path, output_dir)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cache_dir = create_cached_imagery_viewer(sys.argv[1])
        print(f"Cached imagery viewer created: {cache_dir}")
        
        # Try to open the viewer
        try:
            import os
            html_file = Path(cache_dir) / "index.html"
            os.system(f"open '{html_file}'")
            print("🌐 Cached imagery viewer opened in browser")
        except:
            print("💡 Tip: Open index.html in the cached images directory")
    else:
        print("Usage: python ee_image_downloader.py <json_file_path>")