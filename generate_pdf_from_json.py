#!/usr/bin/env python3
"""
Quick script to generate PDF report from monitoring JSON
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.pdf_report_generator import PDFReportGenerator

# Load the latest monitoring results
json_file = "output/monitoring/weekly_monitoring_20251019_120730.json"
print(f"📊 Using monitoring data from {json_file}...")

# Generate PDF
generator = PDFReportGenerator()
print("📄 Generating PDF report...")

pdf_path = generator.generate_executive_summary(json_file)

print(f"✅ PDF report generated successfully!")
print(f"📁 Saved to: {pdf_path}")
