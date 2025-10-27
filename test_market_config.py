"""
Test script to validate market_config.py tier classifications

This script checks that all 29 Java regions are properly classified
and that the tier system is working correctly.
"""

import sys
sys.path.insert(0, '/Users/chrismoore/Desktop/CloudClearingAPI')

from src.core.market_config import (
    classify_region_tier,
    get_region_tier_info,
    get_tier_summary_stats,
    validate_region_classifications,
    compare_to_java_regions
)
from src.indonesia_expansion_regions import get_all_java_region_names

def main():
    print("="*80)
    print("MARKET CONFIG VALIDATION TEST")
    print("="*80)
    
    # Test 1: Validate no duplicates
    print("\nTest 1: Validating Tier Classifications...")
    validation = validate_region_classifications()
    if validation['valid']:
        print(f"✅ PASS: All {validation['total_regions']} regions uniquely classified")
    else:
        print(f"❌ FAIL: {validation['message']}")
        print(f"   Duplicates: {validation['duplicates']}")
        return False
    
    # Test 2: Compare against actual Java regions
    print("\nTest 2: Comparing Against Java Regions List...")
    java_regions = get_all_java_region_names()
    comparison = compare_to_java_regions(java_regions)
    
    print(f"   Total Java regions: {comparison['total_java_regions']}")
    print(f"   Total classified: {comparison['total_classified']}")
    print(f"   Coverage: {comparison['coverage_pct']:.1f}%")
    
    if comparison['unclassified_regions']:
        print(f"\n⚠️  WARNING: {len(comparison['unclassified_regions'])} Java regions NOT classified:")
        for region in comparison['unclassified_regions']:
            print(f"      - {region}")
    else:
        print(f"✅ PASS: All Java regions are classified")
    
    if comparison['extra_classified_regions']:
        print(f"\n⚠️  WARNING: {len(comparison['extra_classified_regions'])} classified regions DON'T EXIST in Java list:")
        for region in comparison['extra_classified_regions']:
            print(f"      - {region}")
    
    # Test 3: Tier Distribution
    print("\nTest 3: Tier Distribution Summary...")
    stats = get_tier_summary_stats()
    
    print(f"\n   Tier 1 (Metros): {stats['tier_1_metros']['count']} regions")
    print(f"      Price: Rp {stats['tier_1_metros']['avg_price']:,}/m²")
    print(f"      Growth: {stats['tier_1_metros']['expected_growth']:.1%}/year")
    
    print(f"\n   Tier 2 (Secondary): {stats['tier_2_secondary']['count']} regions")
    print(f"      Price: Rp {stats['tier_2_secondary']['avg_price']:,}/m²")
    print(f"      Growth: {stats['tier_2_secondary']['expected_growth']:.1%}/year")
    
    print(f"\n   Tier 3 (Emerging): {stats['tier_3_emerging']['count']} regions")
    print(f"      Price: Rp {stats['tier_3_emerging']['avg_price']:,}/m²")
    print(f"      Growth: {stats['tier_3_emerging']['expected_growth']:.1%}/year")
    
    print(f"\n   Tier 4 (Frontier): {stats['tier_4_frontier']['count']} regions")
    print(f"      Price: Rp {stats['tier_4_frontier']['avg_price']:,}/m²")
    print(f"      Growth: {stats['tier_4_frontier']['expected_growth']:.1%}/year")
    
    # Test 4: Sample Classifications
    print("\nTest 4: Sample Region Classifications...")
    test_regions = [
        'jakarta_north_sprawl',
        'bandung_north_expansion',
        'yogyakarta_kulon_progo_airport',
        'tegal_brebes_coastal'
    ]
    
    for region in test_regions:
        tier = classify_region_tier(region)
        info = get_region_tier_info(region)
        print(f"\n   {region}:")
        print(f"      Tier: {tier}")
        print(f"      Expected Price: Rp {info['benchmarks']['avg_price_m2']:,}/m²")
        print(f"      Expected Growth: {info['benchmarks']['expected_growth']:.1%}/year")
        print(f"      Liquidity: {info['benchmarks']['liquidity']}")
    
    # Test 5: Coverage check
    print("\n" + "="*80)
    if comparison['coverage_pct'] == 100.0 and validation['valid']:
        print("✅ ALL TESTS PASSED - Market config is valid and complete!")
    else:
        print("⚠️  TESTS INCOMPLETE - See warnings above")
    print("="*80)
    
    return comparison['coverage_pct'] == 100.0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
