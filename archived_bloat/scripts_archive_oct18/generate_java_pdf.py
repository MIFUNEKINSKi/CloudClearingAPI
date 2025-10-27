#!/usr/bin/env python3
"""
Generate Executive Summary PDF from Java Monitoring Results
Uses the improved PDF formatting with detailed investment factors
"""

import json
from pathlib import Path
from src.core.pdf_report_generator import generate_pdf_from_json

def main():
    # Load the Java monitoring results
    monitoring_file = "output/monitoring/weekly_monitoring_20251005_193651.json"
    
    print("🎨 Generating Executive Summary PDF from Java Monitoring Results")
    print(f"📂 Source: {monitoring_file}")
    print()
    
    if not Path(monitoring_file).exists():
        print(f"❌ Error: Monitoring file not found: {monitoring_file}")
        return
    
    # Load the data to show preview
    with open(monitoring_file, 'r') as f:
        data = json.load(f)
    
    # Check what we have
    regions_analyzed = data.get('regions_analyzed', [])
    print(f"✅ Loaded data for {len(regions_analyzed)} regions")
    
    # Show some region names
    if regions_analyzed:
        print(f"\n📍 Sample regions:")
        for region in regions_analyzed[:5]:
            region_name = region.get('region_name', 'Unknown').replace('_', ' ').title()
            changes = region.get('change_count', 0)
            print(f"   • {region_name}: {changes:,} changes")
        if len(regions_analyzed) > 5:
            print(f"   ... and {len(regions_analyzed) - 5} more")
    
    print()
    
    # Generate the PDF using the function
    print("🔨 Generating PDF with improved formatting...")
    print("   ✓ Methodology explanation (once at beginning)")
    print("   ✓ Detailed investment factors for each region")
    print("   ✓ Market dynamics and infrastructure scores")
    print("   ✓ Clear vegetation change analysis")
    print()
    
    output_file = generate_pdf_from_json(monitoring_file)
    
    print()
    print("=" * 70)
    print("✅ PDF GENERATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"📄 Output: {output_file}")
    print()
    
    # Show investment summary
    investment_analysis = data.get('investment_analysis', {})
    yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
    buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
    
    if buy_recs:
        print(f"💰 Top Investment Opportunities in PDF:")
        for i, rec in enumerate(buy_recs[:5], 1):
            region = rec.get('region', 'Unknown').replace('_', ' ').title()
            score = rec.get('investment_score', rec.get('score', 0))
            confidence = rec.get('confidence_level', rec.get('confidence', 0))
            changes = rec.get('satellite_changes', 0)
            print(f"   {i}. {region}")
            print(f"      Score: {score:.1f}/100 | Confidence: {confidence:.0%} | Changes: {changes:,}")
    
    print()
    print("🎯 Next Steps:")
    print(f"   • Open the PDF: open {output_file}")
    print("   • Review investment factors for top opportunities")
    print("   • Check confidence levels and data availability")
    print("   • Compare across Java regions")
    print()

if __name__ == "__main__":
    main()
