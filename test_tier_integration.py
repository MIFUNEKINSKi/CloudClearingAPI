"""
Test script to validate tier-based benchmark integration in financial_metrics.py

This script tests Phase 2A.2 implementation:
- Tier-based benchmarks replacing 6 static benchmarks
- Tier info populated in FinancialProjection dataclass
- Sample regions from each tier
"""

import sys
sys.path.insert(0, '/Users/chrismoore/Desktop/CloudClearingAPI')

from src.core.financial_metrics import FinancialMetricsEngine
from types import SimpleNamespace

def test_tier_integration():
    """Test tier-based benchmark integration with sample regions from each tier"""
    
    print("="*80)
    print("TIER-BASED BENCHMARK INTEGRATION TEST (Phase 2A.2)")
    print("="*80)
    
    # Initialize financial engine
    engine = FinancialMetricsEngine(enable_web_scraping=False)  # Disable scraping for testing
    
    # Test regions (one from each tier)
    test_regions = [
        {
            'name': 'jakarta_north_sprawl',
            'expected_tier': 'tier_1_metros',
            'expected_benchmark': 8_000_000
        },
        {
            'name': 'bandung_north_expansion',
            'expected_tier': 'tier_2_secondary',
            'expected_benchmark': 5_000_000
        },
        {
            'name': 'yogyakarta_kulon_progo_airport',
            'expected_tier': 'tier_3_emerging',
            'expected_benchmark': 3_000_000
        },
        {
            'name': 'tegal_brebes_coastal',
            'expected_tier': 'tier_4_frontier',
            'expected_benchmark': 1_500_000
        }
    ]
    
    # Mock data (same for all tests)
    satellite_data = {
        'vegetation_loss_pixels': 2000,
        'total_pixels': 10000,
        'construction_activity_pct': 10
    }
    
    infrastructure_data = {
        'infrastructure_score': 65,
        'major_features': ['Highway A', 'Airport B'],
        'data_confidence': 0.85,
        'data_source': 'osm_live'
    }
    
    market_data = {
        'price_trend_30d': 8,
        'market_heat': 'warming',
        'data_confidence': 0.75
    }
    
    scoring_result = SimpleNamespace(final_investment_score=65)
    
    # Test each region
    results = []
    for region in test_regions:
        print(f"\n{'='*80}")
        print(f"Testing: {region['name']}")
        print(f"Expected Tier: {region['expected_tier']}")
        print(f"Expected Benchmark: Rp {region['expected_benchmark']:,}/m²")
        print(f"{'='*80}")
        
        try:
            # Calculate financial projection
            projection = engine.calculate_financial_projection(
                region['name'],
                satellite_data,
                infrastructure_data,
                market_data,
                scoring_result
            )
            
            # Validate tier assignment
            tier_match = projection.regional_tier == region['expected_tier']
            benchmark_match = projection.tier_benchmark_price == region['expected_benchmark']
            has_peers = projection.peer_regions is not None and len(projection.peer_regions) > 0
            
            print(f"\n✓ Projection Calculated Successfully")
            print(f"\nTier Information:")
            print(f"  Regional Tier: {projection.regional_tier} {'✅' if tier_match else '❌ MISMATCH'}")
            print(f"  Tier Benchmark: Rp {projection.tier_benchmark_price:,}/m² {'✅' if benchmark_match else '❌ MISMATCH'}")
            print(f"  Current Value: Rp {projection.current_land_value_per_m2:,.0f}/m²")
            print(f"  Peer Regions: {len(projection.peer_regions) if projection.peer_regions else 0} regions {'✅' if has_peers else '❌'}")
            
            if projection.peer_regions and len(projection.peer_regions) > 0:
                print(f"    Sample peers: {', '.join(projection.peer_regions[:3])}")
            
            print(f"\nFinancial Metrics:")
            print(f"  3-Year ROI: {projection.projected_roi_3yr:.1%}")
            print(f"  Appreciation Rate: {projection.appreciation_rate_annual:.1%}/year")
            print(f"  Recommended Plot: {projection.recommended_plot_size_m2:,.0f} m²")
            print(f"  Total Investment: Rp {(projection.total_acquisition_cost + projection.total_development_cost):,.0f}")
            
            # Store result
            results.append({
                'region': region['name'],
                'success': True,
                'tier_match': tier_match,
                'benchmark_match': benchmark_match,
                'has_peers': has_peers,
                'projection': projection
            })
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            results.append({
                'region': region['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r['success'])
    tier_matches = sum(1 for r in results if r.get('tier_match', False))
    benchmark_matches = sum(1 for r in results if r.get('benchmark_match', False))
    
    print(f"\nRegions Tested: {len(test_regions)}")
    print(f"Successful Projections: {successful}/{len(test_regions)}")
    print(f"Correct Tier Assignment: {tier_matches}/{len(test_regions)}")
    print(f"Correct Benchmark Price: {benchmark_matches}/{len(test_regions)}")
    
    # Tier comparison table
    print(f"\n{'='*80}")
    print("TIER COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Region':<35} {'Tier':<20} {'Benchmark':>15} {'Actual':>15}")
    print(f"{'-'*35} {'-'*20} {'-'*15} {'-'*15}")
    
    for result in results:
        if result['success']:
            proj = result['projection']
            region_short = result['region'][:33]
            tier_short = (proj.regional_tier or 'N/A')[-17:]
            benchmark = proj.tier_benchmark_price or 0
            actual = proj.current_land_value_per_m2
            
            print(f"{region_short:<35} {tier_short:<20} {f'Rp {benchmark:,.0f}':>15} {f'Rp {actual:,.0f}':>15}")
    
    # Final validation
    print(f"\n{'='*80}")
    if successful == len(test_regions) and tier_matches == len(test_regions) and benchmark_matches == len(test_regions):
        print("✅ ALL TESTS PASSED - Phase 2A.2 Integration Successful!")
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
    print(f"{'='*80}")
    
    return successful == len(test_regions)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    success = test_tier_integration()
    sys.exit(0 if success else 1)
