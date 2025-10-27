#!/usr/bin/env python3
"""
Regenerate PDF report from existing monitoring JSON using UPDATED pdf_report_generator.py
This allows us to test PDF fixes without re-running the entire monitoring process.
"""
import sys
from datetime import datetime
from src.core.pdf_report_generator import generate_pdf_from_json

def main():
    # Use the latest monitoring JSON
    json_path = "output/monitoring/weekly_monitoring_20251011_124800.json"
    
    print(f"📄 Regenerating PDF from: {json_path}")
    print(f"🔨 Using UPDATED pdf_report_generator.py with all 6 fixes...")
    
    # Generate new PDF with UPDATED code
    output_path = generate_pdf_from_json(json_path, "output/reports")
    
    print(f"\n✅ PDF regenerated: {output_path}")
    print(f"\n📊 This PDF should now have:")
    print(f"   1. ✅ Table sorted by score (highest to lowest)")
    print(f"   2. ✅ Top imagery sections with full investment details")
    print(f"   3. ✅ Correct local storage path note")
    print(f"   4. ✅ All 39 regions with visible scores (including PASS <25)")
    print(f"   5. ✅ Division by zero protection")
    print(f"   6. ✅ All recommendation lists included (BUY + WATCH + PASS)")
    
    return output_path

if __name__ == '__main__':
    output_path = main()
    # Open the new PDF
    import subprocess
    subprocess.run(['open', output_path])
