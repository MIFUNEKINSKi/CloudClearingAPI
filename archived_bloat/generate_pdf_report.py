#!/usr/bin/env python3
"""
Generate PDF executive summary from existing monitoring JSON files
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from core.pdf_report_generator import generate_pdf_from_json

def main():
    """Main function to generate PDF from JSON"""
    if len(sys.argv) != 2:
        print("Usage: python generate_pdf_report.py <json_file_path>")
        print("\nExample:")
        print("python generate_pdf_report.py output/monitoring/weekly_monitoring_20250928_105823.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file not found: {json_file}")
        sys.exit(1)
    
    try:
        print(f"📄 Generating PDF executive summary from: {json_file}")
        pdf_path = generate_pdf_from_json(json_file)
        print(f"✅ PDF report generated successfully: {pdf_path}")
        
        # Try to open the PDF (macOS)
        try:
            os.system(f"open '{pdf_path}'")
            print("📖 PDF opened in default viewer")
        except:
            print("💡 Tip: You can open the PDF manually from the output/reports directory")
            
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()