"""
Web-based Satellite Imagery Viewer for CloudClearingAPI

This creates a simple HTML page to view satellite imagery from monitoring results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

def create_imagery_viewer(json_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Create an HTML page to view satellite imagery from monitoring results
    
    Args:
        json_file_path: Path to monitoring JSON file
        output_dir: Directory to save HTML file
        
    Returns:
        Path to generated HTML file
    """
    # Load monitoring data
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Setup output directory
    if output_dir is None:
        output_path = Path('./output/imagery_viewer')
    else:
        output_path = Path(output_dir)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_filename = output_path / f"imagery_viewer_{timestamp}.html"
    
    # Get regions with imagery
    regions_analyzed = data.get('regions_analyzed', [])
    regions_with_imagery = [r for r in regions_analyzed if r.get('satellite_images', {}).get('week_a_true_color')]
    
    # Generate HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudClearing Satellite Imagery Viewer</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #2E86AB, #A23B72);
            color: white;
            border-radius: 10px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .region-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        .region-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .region-card:hover {{
            transform: translateY(-5px);
        }}
        .region-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #2E86AB;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        .region-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-box {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .stat-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: #A23B72;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .imagery-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .image-container {{
            text-align: center;
        }}
        .image-label {{
            font-size: 0.9em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #555;
        }}
        .satellite-image {{
            width: 100%;
            height: 200px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
            cursor: pointer;
        }}
        .satellite-image:hover {{
            transform: scale(1.05);
        }}
        .image-date {{
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }}
        .no-imagery {{
            text-align: center;
            color: #888;
            font-style: italic;
            padding: 40px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }}
        .modal-content {{
            margin: auto;
            display: block;
            width: 80%;
            max-width: 700px;
            margin-top: 5%;
        }}
        .close {{
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover {{
            color: #bbb;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ CloudClearing Satellite Imagery Viewer</h1>
        <p>Analysis Period: {data.get('period', 'Unknown')} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
    
    <div class="region-grid">
"""
    
    if not regions_with_imagery:
        html_content += """
        <div class="no-imagery">
            <h2>No Satellite Imagery Available</h2>
            <p>No regions in this analysis have satellite imagery data available.</p>
        </div>
        """
    else:
        for region in regions_with_imagery:
            region_name = region['region_name'].replace('_', ' ').title()
            change_count = region.get('change_count', 0)
            area_ha = region.get('total_area_m2', 0) / 10000
            analysis_type = region.get('analysis_type', 'unknown').replace('_', ' ').title()
            
            sat_images = region.get('satellite_images', {})
            week_a_date = sat_images.get('week_a_date', 'Unknown')
            week_b_date = sat_images.get('week_b_date', 'Unknown')
            
            html_content += f"""
        <div class="region-card">
            <div class="region-title">{region_name}</div>
            <div class="region-stats">
                <div class="stat-box">
                    <div class="stat-number">{change_count:,}</div>
                    <div class="stat-label">Changes</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{area_ha:.1f}</div>
                    <div class="stat-label">Hectares</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{analysis_type}</div>
                    <div class="stat-label">Type</div>
                </div>
            </div>
            <div class="imagery-grid">
                <div class="image-container">
                    <div class="image-label">🌍 Before (True Color)</div>
                    <img src="{sat_images.get('week_a_true_color', '')}" 
                         alt="Before - True Color" 
                         class="satellite-image"
                         onclick="openModal(this.src)"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                         onload="if(this.naturalWidth === 0 || this.naturalHeight === 0) {{ this.style.display='none'; this.nextElementSibling.style.display='block'; }}">
                    <div style="display:none; padding:20px; background:#fff3cd; border:1px solid #ffeaa7; border-radius:8px; margin-top:10px;">
                        <p style="margin:0 0 10px 0;"><strong>🔒 Authentication Required</strong></p>
                        <p style="margin:0 0 10px 0; font-size:14px;">This Google Earth Engine image requires authentication tokens.</p>
                        <button onclick="window.open('{sat_images.get('week_a_true_color', '')}', '_blank')" 
                                style="padding:8px 16px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">
                            🚀 Open in New Tab
                        </button>
                    </div>
                    <div class="image-date">{week_a_date}</div>
                </div>
                <div class="image-container">
                    <div class="image-label">🌍 After (True Color)</div>
                    <img src="{sat_images.get('week_b_true_color', '')}" 
                         alt="After - True Color" 
                         class="satellite-image"
                         onclick="openModal(this.src)"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                         onload="if(this.naturalWidth === 0 || this.naturalHeight === 0) {{ this.style.display='none'; this.nextElementSibling.style.display='block'; }}">
                    <div style="display:none; padding:20px; background:#fff3cd; border:1px solid #ffeaa7; border-radius:8px; margin-top:10px;">
                        <p style="margin:0 0 10px 0;"><strong>🔒 Authentication Required</strong></p>
                        <p style="margin:0 0 10px 0; font-size:14px;">This Google Earth Engine image requires authentication tokens.</p>
                        <button onclick="window.open('{sat_images.get('week_b_true_color', '')}', '_blank')" 
                                style="padding:8px 16px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">
                            🚀 Open in New Tab
                        </button>
                    </div>
                    <div class="image-date">{week_b_date}</div>
                </div>
                <div class="image-container">
                    <div class="image-label">🌱 NDVI Change</div>
                    <img src="{sat_images.get('ndvi_change', '')}" 
                         alt="NDVI Change" 
                         class="satellite-image"
                         onclick="openModal(this.src)"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                         onload="if(this.naturalWidth === 0 || this.naturalHeight === 0) {{ this.style.display='none'; this.nextElementSibling.style.display='block'; }}">
                    <div style="display:none; padding:20px; background:#d1ecf1; border:1px solid #bee5eb; border-radius:8px; margin-top:10px;">
                        <p style="margin:0 0 10px 0;"><strong>🌱 NDVI Change Analysis</strong></p>
                        <p style="margin:0 0 10px 0; font-size:14px;">Red areas = vegetation loss, Green areas = vegetation gain</p>
                        <button onclick="window.open('{sat_images.get('ndvi_change', '')}', '_blank')" 
                                style="padding:8px 16px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer;">
                            🚀 Open in New Tab
                        </button>
                    </div>
                    <div class="image-date">Change Analysis</div>
                </div>
            </div>
        </div>
            """
    
    html_content += """
    </div>
    
    <div class="footer">
        <p><strong>Legend:</strong></p>
        <p>🌍 True Color: Natural appearance (Red, Green, Blue bands)</p>
        <p>🌿 False Color: Vegetation analysis (NIR, Red, Green bands)</p>
        <p>🌱 NDVI Change: Red = vegetation loss, Green = vegetation gain</p>
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <p>Generated by CloudClearing Automated Monitor | © 2025 CloudClearing Intelligence</p>
    </div>
    
    <!-- Modal for enlarged images -->
    <div id="imageModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>
    
    <script>
        function openModal(imgSrc) {
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = imgSrc;
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        // Close modal when clicking outside the image
        window.onclick = function(event) {
            var modal = document.getElementById('imageModal');
            if (event.target == modal) {
                closeModal();
            }
        }
        
        // Enhanced image loading detection
        function checkImageLoad(img) {
            return new Promise((resolve) => {
                if (img.complete) {
                    resolve(img.naturalWidth > 0 && img.naturalHeight > 0);
                } else {
                    img.onload = () => resolve(img.naturalWidth > 0 && img.naturalHeight > 0);
                    img.onerror = () => resolve(false);
                }
            });
        }
        
        // Check all images after page load
        window.addEventListener('load', async function() {
            const images = document.querySelectorAll('.satellite-image');
            for (let img of images) {
                const loaded = await checkImageLoad(img);
                if (!loaded) {
                    img.style.display = 'none';
                    img.nextElementSibling.style.display = 'block';
                }
            }
            
            // Add loading indicators
            const containers = document.querySelectorAll('.image-container');
            containers.forEach(container => {
                const img = container.querySelector('.satellite-image');
                const fallback = container.querySelector('div[style*="display:none"]');
                
                if (img && img.style.display !== 'none') {
                    img.style.background = 'linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0), linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0)';
                    img.style.backgroundSize = '20px 20px';
                    img.style.backgroundPosition = '0 0, 10px 10px';
                }
            });
        });
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(html_filename, 'w') as f:
        f.write(html_content)
    
    return str(html_filename)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        html_path = create_imagery_viewer(sys.argv[1])
        print(f"HTML imagery viewer generated: {html_path}")
        
        # Try to open in browser (macOS)
        try:
            import os
            os.system(f"open '{html_path}'")
            print("🌐 Imagery viewer opened in browser")
        except:
            print("💡 Tip: Open the HTML file in your browser to view satellite imagery")
    else:
        print("Usage: python satellite_imagery_viewer.py <json_file_path>")