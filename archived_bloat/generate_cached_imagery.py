#!/usr/bin/env python3
"""
Generate cached satellite imagery viewer with local Earth Engine authentication
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from core.ee_image_downloader import create_cached_imagery_viewer

def main():
    """Main function to generate cached imagery viewer from JSON"""
    if len(sys.argv) != 2:
        print("Usage: python generate_cached_imagery.py <json_file_path>")
        print("\nExample:")
        print("python generate_cached_imagery.py output/monitoring/weekly_monitoring_20250928_105823.json")
        print("\nNote: This requires Google Earth Engine authentication (earthengine authenticate)")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file not found: {json_file}")
        sys.exit(1)
    
    try:
        print(f"🛰️ Creating cached imagery viewer from: {json_file}")
        print("📥 Downloading and caching satellite images (this may take a moment)...")
        
        cache_dir = create_cached_imagery_viewer(json_file)
        
        print(f"✅ Cached imagery viewer generated successfully: {cache_dir}")
        
        # Try to open the HTML viewer
        try:
            html_file = Path(cache_dir) / "index.html"
            os.system(f"open '{html_file}'")
            print("🌐 Cached imagery viewer opened in browser")
        except:
            print("💡 Tip: Open index.html in the cached images directory")
            
    except Exception as e:
        print(f"❌ Error generating cached imagery: {e}")
        if "Earth Engine" in str(e):
            print("💡 Tip: Make sure you're authenticated with Earth Engine:")
            print("   earthengine authenticate")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()