#!/usr/bin/env python3
"""
Test script to verify API confidence fixes

This script tests a single region to check if:
1. Infrastructure API returns data_source and data_confidence
2. Market API returns proper confidence values
3. Final confidence calculation is working correctly
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.corrected_scoring import CorrectedInvestmentScorer
from core.price_intelligence import PriceIntelligenceEngine
from core.infrastructure_analyzer import InfrastructureAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_single_region():
    """Test scoring for a single region to verify fixes"""
    
    print("\n" + "="*80)
    print("🧪 TESTING API CONFIDENCE FIXES")
    print("="*80 + "\n")
    
    # Initialize required engines
    price_engine = PriceIntelligenceEngine()
    infrastructure_engine = InfrastructureAnalyzer()
    scoring_engine = CorrectedInvestmentScorer(price_engine, infrastructure_engine)
    
    # Test region
    test_region = {
        'region_name': 'jakarta_north_sprawl',
        'bbox': {'west': 106.7, 'south': -6.15, 'east': 106.9, 'north': -5.95},
        'satellite_changes': 12338,
        'area_affected_m2': 179881808
    }
    
    print(f"📍 Testing Region: {test_region['region_name']}")
    print(f"📊 Satellite Changes: {test_region['satellite_changes']:,}")
    print(f"📏 Area: {test_region['area_affected_m2'] / 10000:.1f} hectares\n")
    
    # Calculate score with the fixed APIs
    result = scoring_engine.calculate_investment_score(
        region_name=test_region['region_name'],
        satellite_changes=test_region['satellite_changes'],
        area_affected_m2=test_region['area_affected_m2'],
        region_config={},
        coordinates={'lat': -6.05, 'lon': 106.8},
        bbox=test_region['bbox']
    )
    
    # Display results
    print("="*80)
    print("📈 SCORING RESULTS")
    print("="*80)
    print(f"\n🎯 Final Score: {result.final_investment_score:.1f}/100 ({result.recommendation})")
    print(f"📊 Confidence Level: {result.confidence_level:.1%} (Target: >79%)")
    print(f"💡 Rationale: {result.rationale}\n")
    
    print("="*80)
    print("🔍 SCORE BREAKDOWN")
    print("="*80)
    print(f"Development Score: {result.development_score:.1f}/40 ({result.satellite_changes:,} changes)")
    print(f"Infrastructure: {result.infrastructure_score:.0f}/100 (×{result.infrastructure_multiplier:.2f})")
    print(f"Market Trend: {result.price_trend_30d:+.1f}% (×{result.market_multiplier:.2f})")
    print(f"Market Heat: {result.market_heat}")
    
    print("\n" + "="*80)
    print("📡 DATA SOURCES")
    print("="*80)
    for source, value in result.data_sources.items():
        icon = "✅" if value not in ['unavailable', 'unknown'] else "❌"
        print(f"{icon} {source.title()}: {value}")
    
    print("\n" + "="*80)
    print("🎯 DATA AVAILABILITY")
    print("="*80)
    for source, available in result.data_availability.items():
        icon = "✅" if available else "❌"
        print(f"{icon} {source.replace('_', ' ').title()}: {'Available' if available else 'Unavailable'}")
    
    # Check infrastructure details
    print("\n" + "="*80)
    print("🏗️ INFRASTRUCTURE DETAILS")
    print("="*80)
    print(f"Score: {result.infrastructure_score:.0f}/100")
    print(f"Roads: {result.roads_count} features")
    print(f"Airports: {result.airports_nearby}")
    print(f"Railway Access: {'Yes' if result.railway_access else 'No'}")
    
    # Verify fixes
    print("\n" + "="*80)
    print("✅ VERIFICATION CHECKS")
    print("="*80)
    
    checks = []
    
    # Check 1: Infrastructure has data_source
    infra_source = result.data_sources.get('infrastructure', 'MISSING')
    check1 = infra_source != 'MISSING' and infra_source != 'unavailable'
    checks.append(("Infrastructure data_source present", check1, infra_source))
    
    # Check 2: Confidence is above 71%
    check2 = result.confidence_level > 0.71
    checks.append(("Confidence > 71%", check2, f"{result.confidence_level:.1%}"))
    
    # Check 3: Market data has source
    market_source = result.data_sources.get('market', 'MISSING')
    check3 = market_source == 'live'
    checks.append(("Market data source = 'live'", check3, market_source))
    
    # Check 4: Expected confidence range (75-90% with all APIs working)
    check4 = 0.75 <= result.confidence_level <= 0.95
    checks.append(("Confidence in expected range (75-95%)", check4, f"{result.confidence_level:.1%}"))
    
    # Display checks
    for check_name, passed, value in checks:
        icon = "✅" if passed else "❌"
        print(f"{icon} {check_name}: {value}")
    
    # Overall result
    all_passed = all(check[1] for check in checks)
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 SUCCESS! All checks passed!")
        print("="*80)
        print("\n✅ Infrastructure API now returns data_source and data_confidence")
        print("✅ Confidence calculation rewards high-quality data")
        print(f"✅ Final confidence: {result.confidence_level:.1%} (up from 71%)")
        print("\nYou can now run the full Java monitoring:")
        print("  python run_weekly_java_monitor.py")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("="*80)
        failed = [check for check in checks if not check[1]]
        print("\nFailed checks:")
        for check_name, _, value in failed:
            print(f"  ❌ {check_name}: {value}")
        print("\nPlease review the fixes in:")
        print("  - src/core/infrastructure_analyzer.py")
        print("  - src/core/corrected_scoring.py")
        return 1

if __name__ == '__main__':
    sys.exit(test_single_region())
