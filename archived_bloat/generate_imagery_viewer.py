#!/usr/bin/env python3
"""
Generate HTML satellite imagery viewer from monitoring JSON files
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from core.satellite_imagery_viewer import create_imagery_viewer

def main():
    """Main function to generate imagery viewer from JSON"""
    if len(sys.argv) != 2:
        print("Usage: python generate_imagery_viewer.py <json_file_path>")
        print("\nExample:")
        print("python generate_imagery_viewer.py output/monitoring/weekly_monitoring_20250928_105823.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file not found: {json_file}")
        sys.exit(1)
    
    try:
        print(f"🌐 Generating HTML imagery viewer from: {json_file}")
        html_path = create_imagery_viewer(json_file)
        print(f"✅ HTML imagery viewer generated successfully: {html_path}")
        
        # Try to open the HTML (macOS)
        try:
            os.system(f"open '{html_path}'")
            print("🌐 Imagery viewer opened in browser")
        except:
            print("💡 Tip: You can open the HTML file manually in your browser")
            
    except Exception as e:
        print(f"❌ Error generating imagery viewer: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()