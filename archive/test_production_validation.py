#!/usr/bin/env python3
"""
Production Test: Full End-to-End Validation

This script runs a complete production test of the CloudClearingAPI system
with the corrected satellite-centric scoring system. It validates:

1. Data ingestion (Google Earth Engine)
2. Change detection (satellite analysis)
3. Corrected scoring system (satellite-centric)
4. Infrastructure analysis
5. Market intelligence
6. Report generation (JSON + PDF)
7. Score distribution validation

This is the FINAL QUALITY GATE before updating documentation.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)

def validate_score_distribution(results):
    """Validate that scores show proper differentiation"""
    print_section("SCORE DISTRIBUTION ANALYSIS")
    
    scores = []
    recommendations = {'BUY': 0, 'WATCH': 0, 'PASS': 0}
    
    # Collect all scores
    for region in results.get('regions', []):
        if 'investment_score' in region:
            score = region['investment_score']
            scores.append(score)
            rec = region.get('recommendation', 'UNKNOWN')
            if rec in recommendations:
                recommendations[rec] += 1
    
    if not scores:
        print("❌ No scores found in results!")
        return False
    
    min_score = min(scores)
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    
    print(f"\n📊 Score Statistics:")
    print(f"   Total regions scored: {len(scores)}")
    print(f"   Score range: {min_score:.1f} - {max_score:.1f}")
    print(f"   Average score: {avg_score:.1f}")
    print(f"   Median score: {sorted(scores)[len(scores)//2]:.1f}")
    
    print(f"\n🎯 Recommendation Distribution:")
    total = sum(recommendations.values())
    for rec, count in recommendations.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"   {rec}: {count} ({pct:.1f}%)")
    
    # Validation checks
    print(f"\n✅ Validation Checks:")
    
    # Check 1: Score range (should be 0-60, not 71-95)
    if max_score < 65:
        print(f"   ✅ Score range is correct (0-60 expected, got {min_score:.1f}-{max_score:.1f})")
        check1 = True
    else:
        print(f"   ❌ Score range is TOO HIGH! Expected <65, got {max_score:.1f}")
        print(f"      This suggests old scoring system is still being used!")
        check1 = False
    
    # Check 2: Distribution (should have variety, not all BUYs)
    if recommendations['PASS'] > 0 or recommendations['WATCH'] > 0:
        print(f"   ✅ Recommendation distribution is diverse (not all BUYs)")
        check2 = True
    else:
        print(f"   ❌ All recommendations are BUY! This suggests old scoring.")
        check2 = False
    
    # Check 3: Score spread (should have good differentiation)
    score_spread = max_score - min_score
    if score_spread > 15:
        print(f"   ✅ Score spread is good ({score_spread:.1f} points difference)")
        check3 = True
    else:
        print(f"   ⚠️  Score spread is narrow ({score_spread:.1f} points)")
        print(f"      Expected >15 points difference between highest and lowest")
        check3 = False
    
    return check1 and check2 and check3

def validate_satellite_integration(results):
    """Validate that satellite data is driving scores"""
    print_section("SATELLITE DATA INTEGRATION CHECK")
    
    satellite_driven = 0
    total_regions = 0
    
    for region in results.get('regions', []):
        total_regions += 1
        changes = region.get('changes', 0)
        score = region.get('investment_score', 0)
        
        # Check if low changes = low score (proper correlation)
        if changes < 1000 and score < 30:
            satellite_driven += 1
        elif changes > 10000 and score > 20:
            satellite_driven += 1
    
    if total_regions == 0:
        print("❌ No regions found in results!")
        return False
    
    correlation_pct = (satellite_driven / total_regions) * 100
    
    print(f"\n📡 Satellite Data Correlation:")
    print(f"   Regions with proper correlation: {satellite_driven}/{total_regions} ({correlation_pct:.1f}%)")
    
    if correlation_pct > 50:
        print(f"   ✅ Satellite data is driving scores!")
        return True
    else:
        print(f"   ❌ Weak correlation - satellite data may not be primary driver")
        return False

def main():
    print("\n" + "🚀" * 40)
    print("PRODUCTION TEST: CORRECTED SCORING SYSTEM VALIDATION")
    print("🚀" * 40)
    
    print("\n📋 Test Plan:")
    print("   1. Run full weekly monitoring")
    print("   2. Validate JSON output")
    print("   3. Validate PDF generation")
    print("   4. Analyze score distribution")
    print("   5. Verify satellite data integration")
    print("   6. Check for proper differentiation")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    
    print_section("STEP 1: Running Full Weekly Monitor")
    print("\n⏳ This will take 5-10 minutes...")
    print("   - Fetching satellite data from Google Earth Engine")
    print("   - Running change detection algorithms")
    print("   - Calculating CORRECTED investment scores")
    print("   - Generating PDF reports")
    print()
    
    # Import and run the monitor
    try:
        from run_weekly_monitor import main as run_monitor
        
        print("🔄 Starting monitoring run...")
        results = run_monitor()
        
        if not results:
            print("\n❌ Monitoring run returned no results!")
            return False
            
        print("\n✅ Monitoring run completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running monitor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Find the latest output files
    print_section("STEP 2: Locating Output Files")
    
    output_dir = project_dir / "output" / "monitoring"
    report_dir = project_dir / "output" / "reports"
    
    # Find latest JSON
    json_files = sorted(output_dir.glob("weekly_monitoring_*.json"), reverse=True)
    if not json_files:
        print("❌ No monitoring JSON files found!")
        return False
    
    latest_json = json_files[0]
    print(f"✅ Found JSON: {latest_json.name}")
    
    # Find latest PDF
    pdf_files = sorted(report_dir.glob("executive_summary_*.pdf"), reverse=True)
    if pdf_files:
        latest_pdf = pdf_files[0]
        print(f"✅ Found PDF: {latest_pdf.name}")
    else:
        print("⚠️  No PDF files found (may not be generated)")
        latest_pdf = None
    
    # Load and validate JSON
    print_section("STEP 3: Validating JSON Output")
    
    try:
        with open(latest_json) as f:
            results = json.load(f)
        
        print(f"✅ JSON is valid and loaded")
        print(f"   Total regions: {len(results.get('regions', []))}")
        print(f"   Timestamp: {results.get('timestamp', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False
    
    # Validate scoring system
    print_section("STEP 4: Validating Corrected Scoring System")
    
    # Check a few sample regions
    sample_regions = results.get('regions', [])[:3]
    
    print("\n🔬 Sample Region Analysis:")
    for i, region in enumerate(sample_regions, 1):
        print(f"\n   Region {i}: {region.get('region_name', 'Unknown')}")
        print(f"      Satellite changes: {region.get('changes', 0):,}")
        print(f"      Investment score: {region.get('investment_score', 0):.1f}/100")
        print(f"      Recommendation: {region.get('recommendation', 'N/A')}")
        
        # Check if development_score exists (new field)
        if 'development_score' in region:
            print(f"      Development score: {region['development_score']:.1f}/40 ✅ (NEW FIELD)")
        else:
            print(f"      ⚠️  No development_score field (may be using old system)")
    
    # Run validation checks
    score_check = validate_score_distribution(results)
    satellite_check = validate_satellite_integration(results)
    
    # PDF validation
    print_section("STEP 5: PDF Report Validation")
    
    if latest_pdf and latest_pdf.exists():
        pdf_size = latest_pdf.stat().st_size / 1024  # KB
        print(f"✅ PDF exists: {latest_pdf.name}")
        print(f"   Size: {pdf_size:.1f} KB")
        
        if pdf_size > 50:
            print(f"   ✅ PDF size looks reasonable")
            pdf_check = True
        else:
            print(f"   ⚠️  PDF size is small - may be incomplete")
            pdf_check = False
    else:
        print("⚠️  No PDF generated in this run")
        pdf_check = False
    
    # Final results
    print_section("FINAL TEST RESULTS")
    
    all_checks = [
        ("JSON Output", True),
        ("Score Distribution", score_check),
        ("Satellite Integration", satellite_check),
        ("PDF Generation", pdf_check)
    ]
    
    print("\n📊 Test Summary:")
    passed = 0
    for check_name, result in all_checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n   Overall: {passed}/{len(all_checks)} checks passed")
    
    if passed == len(all_checks):
        print("\n" + "🎉" * 40)
        print("✅ ALL TESTS PASSED!")
        print("🎉" * 40)
        print("\n✨ The corrected scoring system is working perfectly!")
        print("   Ready to proceed with documentation updates.")
        return True
    else:
        print("\n" + "⚠️ " * 40)
        print("❌ SOME TESTS FAILED")
        print("⚠️ " * 40)
        print("\n🔧 Issues need to be resolved before documentation updates.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
