"""
Test RVI (Relative Value Index) Calculation - Phase 2A.3
CloudClearingAPI v2.6-alpha

Tests the RVI calculation logic to ensure:
1. RVI correctly identifies undervalued vs overvalued regions
2. Infrastructure premium calculations are accurate
3. Momentum premium adjustments work correctly
4. Interpretation thresholds are properly applied
5. Edge cases handled gracefully
"""

from src.core.financial_metrics import FinancialMetricsEngine
from src.core.market_config import get_region_tier_info
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_rvi_undervalued_scenario():
    """Test RVI detection of undervalued region"""
    print("\n" + "="*80)
    print("TEST 1: UNDERVALUED REGION (Low price, good infrastructure)")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    # Scenario: Tier 3 region with good infrastructure but low price
    # Expected: RVI < 0.95 (undervalued)
    tier_info = get_region_tier_info('yogyakarta_kulon_progo_airport')
    
    rvi_result = engine.calculate_relative_value_index(
        region_name='yogyakarta_kulon_progo_airport',
        actual_price_m2=2_400_000,  # 20% below tier benchmark (3M)
        infrastructure_score=55,     # 10 points above tier baseline (45)
        satellite_data={
            'vegetation_loss_pixels': 3500,
            'construction_activity_pct': 0.12
        },
        tier_info={
            'tier': 'tier_3_emerging',
            'tier_benchmark_price': 3_000_000,
            'peer_regions': tier_info['peer_regions']
        }
    )
    
    print(f"\nRegion: yogyakarta_kulon_progo_airport (Tier 3 - Emerging)")
    print(f"Actual Price: Rp {rvi_result['actual_price_m2']:,.0f}/m²")
    print(f"Expected Price: Rp {rvi_result['expected_price_m2']:,.0f}/m²")
    print(f"Peer Average: Rp {rvi_result['peer_avg_price_m2']:,.0f}/m²")
    print(f"\nPremium Adjustments:")
    print(f"  Infrastructure Premium: {rvi_result['infrastructure_premium']:.3f}x")
    print(f"  Momentum Premium: {rvi_result['momentum_premium']:.3f}x")
    print(f"\n✓ RVI: {rvi_result['rvi']:.3f}")
    print(f"✓ Interpretation: {rvi_result['interpretation']}")
    print(f"✓ Confidence: {rvi_result['confidence']:.0%}")
    
    # Detailed breakdown
    print(f"\nDetailed Breakdown:")
    for key, value in rvi_result['breakdown'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Validation
    assert rvi_result['rvi'] < 0.95, "Should be undervalued"
    print("\n✅ TEST PASSED: Region correctly identified as undervalued")
    return rvi_result

def test_rvi_overvalued_scenario():
    """Test RVI detection of overvalued region"""
    print("\n" + "="*80)
    print("TEST 2: OVERVALUED REGION (High price, poor infrastructure)")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    # Scenario: Tier 2 region with poor infrastructure but high price
    # Expected: RVI > 1.20 (overvalued - speculation risk)
    tier_info = get_region_tier_info('bandung_north_expansion')
    
    rvi_result = engine.calculate_relative_value_index(
        region_name='bandung_north_expansion',
        actual_price_m2=7_200_000,  # 44% above tier benchmark (5M)
        infrastructure_score=45,     # 15 points below tier baseline (60)
        satellite_data={
            'vegetation_loss_pixels': 800,
            'construction_activity_pct': 0.03
        },
        tier_info={
            'tier': 'tier_2_secondary',
            'tier_benchmark_price': 5_000_000,
            'peer_regions': tier_info['peer_regions']
        }
    )
    
    print(f"\nRegion: bandung_north_expansion (Tier 2 - Secondary)")
    print(f"Actual Price: Rp {rvi_result['actual_price_m2']:,.0f}/m²")
    print(f"Expected Price: Rp {rvi_result['expected_price_m2']:,.0f}/m²")
    print(f"Peer Average: Rp {rvi_result['peer_avg_price_m2']:,.0f}/m²")
    print(f"\nPremium Adjustments:")
    print(f"  Infrastructure Premium: {rvi_result['infrastructure_premium']:.3f}x")
    print(f"  Momentum Premium: {rvi_result['momentum_premium']:.3f}x")
    print(f"\n✓ RVI: {rvi_result['rvi']:.3f}")
    print(f"✓ Interpretation: {rvi_result['interpretation']}")
    print(f"✓ Confidence: {rvi_result['confidence']:.0%}")
    
    # Detailed breakdown
    print(f"\nDetailed Breakdown:")
    for key, value in rvi_result['breakdown'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Validation
    assert rvi_result['rvi'] > 1.20, "Should be overvalued"
    print("\n✅ TEST PASSED: Region correctly identified as overvalued (speculation risk)")
    return rvi_result

def test_rvi_fairly_valued_scenario():
    """Test RVI detection of fairly valued region"""
    print("\n" + "="*80)
    print("TEST 3: FAIRLY VALUED REGION (Balanced fundamentals)")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    # Scenario: Tier 1 region with matched infrastructure and price
    # Expected: RVI 0.95-1.05 (fairly valued)
    tier_info = get_region_tier_info('jakarta_south_suburbs')
    
    rvi_result = engine.calculate_relative_value_index(
        region_name='jakarta_south_suburbs',
        actual_price_m2=8_400_000,  # 5% above tier benchmark (8M)
        infrastructure_score=76,     # 1 point above tier baseline (75)
        satellite_data={
            'vegetation_loss_pixels': 2000,
            'construction_activity_pct': 0.08
        },
        tier_info={
            'tier': 'tier_1_metros',
            'tier_benchmark_price': 8_000_000,
            'peer_regions': tier_info['peer_regions']
        }
    )
    
    print(f"\nRegion: jakarta_south_suburbs (Tier 1 - Metro)")
    print(f"Actual Price: Rp {rvi_result['actual_price_m2']:,.0f}/m²")
    print(f"Expected Price: Rp {rvi_result['expected_price_m2']:,.0f}/m²")
    print(f"Peer Average: Rp {rvi_result['peer_avg_price_m2']:,.0f}/m²")
    print(f"\nPremium Adjustments:")
    print(f"  Infrastructure Premium: {rvi_result['infrastructure_premium']:.3f}x")
    print(f"  Momentum Premium: {rvi_result['momentum_premium']:.3f}x")
    print(f"\n✓ RVI: {rvi_result['rvi']:.3f}")
    print(f"✓ Interpretation: {rvi_result['interpretation']}")
    print(f"✓ Confidence: {rvi_result['confidence']:.0%}")
    
    # Detailed breakdown
    print(f"\nDetailed Breakdown:")
    for key, value in rvi_result['breakdown'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Validation
    assert 0.95 <= rvi_result['rvi'] <= 1.05, "Should be fairly valued"
    print("\n✅ TEST PASSED: Region correctly identified as fairly valued")
    return rvi_result

def test_rvi_high_momentum():
    """Test RVI with high development momentum"""
    print("\n" + "="*80)
    print("TEST 4: HIGH DEVELOPMENT MOMENTUM")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    # Scenario: Tier 4 region with intense development activity
    # Expected: Momentum premium ~1.10x
    tier_info = get_region_tier_info('tegal_brebes_coastal')
    
    rvi_result = engine.calculate_relative_value_index(
        region_name='tegal_brebes_coastal',
        actual_price_m2=1_800_000,  # 20% above tier benchmark (1.5M)
        infrastructure_score=32,     # 2 points above tier baseline (30)
        satellite_data={
            'vegetation_loss_pixels': 6500,  # High activity
            'construction_activity_pct': 0.18  # 18% construction
        },
        tier_info={
            'tier': 'tier_4_frontier',
            'tier_benchmark_price': 1_500_000,
            'peer_regions': tier_info['peer_regions']
        }
    )
    
    print(f"\nRegion: tegal_brebes_coastal (Tier 4 - Frontier)")
    print(f"Actual Price: Rp {rvi_result['actual_price_m2']:,.0f}/m²")
    print(f"Expected Price: Rp {rvi_result['expected_price_m2']:,.0f}/m²")
    print(f"Momentum Premium: {rvi_result['momentum_premium']:.3f}x")
    print(f"Development Activity: {rvi_result['breakdown']['development_activity']}")
    print(f"\n✓ RVI: {rvi_result['rvi']:.3f}")
    print(f"✓ Interpretation: {rvi_result['interpretation']}")
    
    # Validation
    assert rvi_result['momentum_premium'] >= 1.05, "Should have positive momentum premium"
    print("\n✅ TEST PASSED: High momentum correctly detected and applied")
    return rvi_result

def test_rvi_edge_case_no_tier():
    """Test RVI graceful handling when tier unavailable"""
    print("\n" + "="*80)
    print("TEST 5: EDGE CASE - No Tier Classification")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    rvi_result = engine.calculate_relative_value_index(
        region_name='unknown_region',
        actual_price_m2=5_000_000,
        infrastructure_score=50,
        satellite_data={
            'vegetation_loss_pixels': 2000,
            'construction_activity_pct': 0.10
        },
        tier_info={
            'tier': None,
            'tier_benchmark_price': None,
            'peer_regions': None
        }
    )
    
    print(f"\nRegion: unknown_region (No tier classification)")
    print(f"✓ RVI: {rvi_result['rvi']}")
    print(f"✓ Interpretation: {rvi_result['interpretation']}")
    print(f"✓ Confidence: {rvi_result['confidence']:.0%}")
    
    # Validation
    assert rvi_result['rvi'] is None, "RVI should be None when tier unavailable"
    assert rvi_result['confidence'] == 0.0, "Confidence should be 0 when tier unavailable"
    print("\n✅ TEST PASSED: Edge case handled gracefully")
    return rvi_result

def test_rvi_across_tiers():
    """Test RVI calculation across all 4 tiers"""
    print("\n" + "="*80)
    print("TEST 6: RVI ACROSS ALL TIERS")
    print("="*80)
    
    engine = FinancialMetricsEngine(enable_web_scraping=False)
    
    test_regions = [
        ('jakarta_north_sprawl', 'tier_1_metros', 8_000_000, 75),
        ('semarang_port_expansion', 'tier_2_secondary', 5_000_000, 60),
        ('bogor_puncak_highland', 'tier_3_emerging', 3_000_000, 45),
        ('tegal_brebes_coastal', 'tier_4_frontier', 1_500_000, 30),
    ]
    
    results = []
    
    for region_name, tier, benchmark, baseline_infra in test_regions:
        tier_info = get_region_tier_info(region_name)
        
        # Test with price ~10% above benchmark
        rvi_result = engine.calculate_relative_value_index(
            region_name=region_name,
            actual_price_m2=benchmark * 1.10,
            infrastructure_score=baseline_infra + 5,  # Slightly above baseline
            satellite_data={
                'vegetation_loss_pixels': 2500,
                'construction_activity_pct': 0.09
            },
            tier_info={
                'tier': tier,
                'tier_benchmark_price': benchmark,
                'peer_regions': tier_info['peer_regions']
            }
        )
        
        results.append((region_name, tier, rvi_result))
        
        print(f"\n{region_name} ({tier}):")
        print(f"  Actual: Rp {rvi_result['actual_price_m2']:,.0f}/m²")
        print(f"  Expected: Rp {rvi_result['expected_price_m2']:,.0f}/m²")
        print(f"  RVI: {rvi_result['rvi']:.3f} - {rvi_result['interpretation']}")
    
    print("\n" + "="*80)
    print("TIER COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Region':<35} {'Tier':<20} {'RVI':<8} {'Valuation'}")
    print("-" * 80)
    for region, tier, result in results:
        print(f"{region:<35} {tier:<20} {result['rvi']:.3f}   {result['interpretation']}")
    
    print("\n✅ TEST PASSED: RVI calculated successfully across all tiers")
    return results

def run_all_tests():
    """Execute all RVI calculation tests"""
    print("\n" + "="*80)
    print("RVI (RELATIVE VALUE INDEX) CALCULATION TEST SUITE")
    print("CloudClearingAPI v2.6-alpha - Phase 2A.3")
    print("="*80)
    
    tests_passed = 0
    tests_total = 6
    
    try:
        test_rvi_undervalued_scenario()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
    
    try:
        test_rvi_overvalued_scenario()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
    
    try:
        test_rvi_fairly_valued_scenario()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
    
    try:
        test_rvi_high_momentum()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
    
    try:
        test_rvi_edge_case_no_tier()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
    
    try:
        test_rvi_across_tiers()
        tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
    
    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print(f"Success Rate: {tests_passed/tests_total:.0%}")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED - Phase 2A.3 RVI Calculation Complete!")
        print("\nNext Step: Phase 2A.4 - Add RVI to scoring output (non-invasive)")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) failed - review and fix")
    
    print("="*80)

if __name__ == '__main__':
    run_all_tests()
