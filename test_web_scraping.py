"""
Test script for web scraping and financial metrics integration
CloudClearingAPI - October 19, 2025

Tests the complete flow:
1. Live scraping from Lamudi and Rumah.com
2. Cache persistence and expiry
3. Fallback to static benchmarks
4. Integration with financial metrics engine
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.scraper_orchestrator import LandPriceOrchestrator
from src.core.financial_metrics import FinancialMetricsEngine
from types import SimpleNamespace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_orchestrator():
    """Test the scraper orchestrator with cascading fallback"""
    print("\n" + "="*80)
    print("TEST 1: Scraper Orchestrator (Live → Cache → Fallback)")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True
    )
    
    # Test regions
    test_regions = [
        "Sleman Yogyakarta",
        "Bantul Yogyakarta",
        "Jakarta Selatan"
    ]
    
    for region in test_regions:
        print(f"\n{'─'*80}")
        print(f"Testing: {region}")
        print(f"{'─'*80}")
        
        result = orchestrator.get_land_price(region, max_listings=10)
        
        print(f"✓ Success: {result['success']}")
        print(f"✓ Data Source: {result['data_source']}")
        print(f"✓ Average Price: Rp {result['average_price_per_m2']:,.0f}/m²")
        print(f"✓ Median Price: Rp {result['median_price_per_m2']:,.0f}/m²")
        print(f"✓ Listings: {result['listing_count']}")
        print(f"✓ Confidence: {result.get('data_confidence', 0):.0%}")
        
        if 'cache_age_hours' in result:
            print(f"✓ Cache Age: {result['cache_age_hours']:.1f} hours")
        
        if 'benchmark_region' in result:
            print(f"✓ Benchmark Used: {result['benchmark_region']}")
        
        # Show sample listings if available
        if result.get('listings'):
            print(f"\n  Sample Listings (top 3):")
            for i, listing in enumerate(result['listings'][:3], 1):
                print(f"    {i}. {listing['location']}")
                print(f"       Rp {listing['price_per_m2']:,.0f}/m² ({listing['size_m2']:,.0f} m²)")


def test_cache_persistence():
    """Test cache persistence and expiry logic"""
    print("\n" + "="*80)
    print("TEST 2: Cache Persistence")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True
    )
    
    region = "Sleman Yogyakarta"
    
    print(f"\nFirst request (should scrape live or use cache)...")
    result1 = orchestrator.get_land_price(region, max_listings=5)
    print(f"✓ Data Source: {result1['data_source']}")
    
    print(f"\nSecond request (should use cache)...")
    result2 = orchestrator.get_land_price(region, max_listings=5)
    print(f"✓ Data Source: {result2['data_source']}")
    
    # Verify cache is working
    if 'cached' in result2['data_source']:
        print(f"✓ Cache is working!")
        print(f"✓ Cache Age: {result2.get('cache_age_hours', 0):.2f} hours")
    else:
        print(f"⚠ Cache may not be working (data source: {result2['data_source']})")


def test_fallback_to_benchmark():
    """Test fallback to static benchmark when scraping fails"""
    print("\n" + "="*80)
    print("TEST 3: Fallback to Static Benchmark")
    print("="*80)
    
    # Disable live scraping to force fallback
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=False
    )
    
    # Clear cache to force fallback
    orchestrator.lamudi.clear_cache()
    orchestrator.rumah_com.clear_cache()
    
    region = "Unknown Region XYZ"
    
    print(f"\nTesting with unknown region (should fallback to benchmark)...")
    result = orchestrator.get_land_price(region, max_listings=10)
    
    print(f"✓ Success: {result['success']}")
    print(f"✓ Data Source: {result['data_source']}")
    print(f"✓ Benchmark Used: {result.get('benchmark_region', 'N/A')}")
    print(f"✓ Average Price: Rp {result['average_price_per_m2']:,.0f}/m²")
    
    if result['data_source'] == 'static_benchmark':
        print(f"✓ Fallback working correctly!")
    else:
        print(f"⚠ Unexpected data source: {result['data_source']}")


def test_financial_metrics_integration():
    """Test integration with financial metrics engine"""
    print("\n" + "="*80)
    print("TEST 4: Financial Metrics Integration")
    print("="*80)
    
    # Initialize financial engine with web scraping enabled
    engine = FinancialMetricsEngine(
        enable_web_scraping=True,
        cache_expiry_hours=24
    )
    
    # Mock data
    satellite_data = {
        'vegetation_loss_pixels': 5000,
        'total_pixels': 10000,
        'construction_activity_pct': 15
    }
    
    infrastructure_data = {
        'infrastructure_score': 72,
        'major_features': ['Highway A', 'Highway B'],
        'data_confidence': 0.85,
        'data_source': 'osm_live'
    }
    
    market_data = {
        'price_trend_30d': 10,
        'market_heat': 'warming',
        'data_confidence': 0.75
    }
    
    scoring_result = SimpleNamespace(final_investment_score=68)
    
    # Test multiple regions
    test_regions = ["Sleman North", "Bantul Yogyakarta"]
    
    for region in test_regions:
        print(f"\n{'─'*80}")
        print(f"Testing Financial Projection: {region}")
        print(f"{'─'*80}")
        
        projection = engine.calculate_financial_projection(
            region,
            satellite_data,
            infrastructure_data,
            market_data,
            scoring_result
        )
        
        print(f"\n✓ Current Land Value: Rp {projection.current_land_value_per_m2:,.0f}/m²")
        print(f"✓ 3-Year Projection: Rp {projection.estimated_future_value_per_m2:,.0f}/m²")
        print(f"✓ Appreciation Rate: {projection.appreciation_rate_annual:.1%}")
        print(f"✓ Development Cost Index: {projection.development_cost_index:.0f}/100")
        print(f"✓ 3-Year ROI: {projection.projected_roi_3yr:.1%}")
        print(f"✓ Break-Even: {projection.break_even_years:.1f} years")
        print(f"✓ Recommended Plot: {projection.recommended_plot_size_m2:,.0f} m²")
        print(f"✓ Total Investment: Rp {(projection.total_acquisition_cost + projection.total_development_cost):,.0f}")
        print(f"✓ Data Sources: {', '.join(projection.data_sources)}")


def test_scraping_resilience():
    """Test scraping resilience with invalid regions"""
    print("\n" + "="*80)
    print("TEST 5: Scraping Resilience (Error Handling)")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True
    )
    
    # Test with various problematic inputs
    test_cases = [
        ("Invalid Region 12345", "Should fallback to benchmark"),
        ("", "Empty string"),
        ("北京", "Non-Latin characters"),
    ]
    
    for region, description in test_cases:
        print(f"\n{'─'*80}")
        print(f"Testing: {description}")
        print(f"Region: '{region}'")
        print(f"{'─'*80}")
        
        try:
            result = orchestrator.get_land_price(region, max_listings=5)
            print(f"✓ Handled gracefully")
            print(f"✓ Data Source: {result['data_source']}")
            print(f"✓ Success: {result['success']}")
            
            if result['success']:
                print(f"✓ Price: Rp {result['average_price_per_m2']:,.0f}/m²")
        except Exception as e:
            print(f"✗ Exception raised: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("WEB SCRAPING & FINANCIAL METRICS - INTEGRATION TEST SUITE")
    print("CloudClearingAPI - October 19, 2025")
    print("="*80)
    
    try:
        # Test 1: Orchestrator
        test_orchestrator()
        
        # Test 2: Cache persistence
        test_cache_persistence()
        
        # Test 3: Fallback logic
        test_fallback_to_benchmark()
        
        # Test 4: Financial metrics integration
        test_financial_metrics_integration()
        
        # Test 5: Error handling
        test_scraping_resilience()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        print("\nNOTE: Some tests may show warnings or fallback to benchmarks")
        print("This is expected behavior when live scraping fails.")
        print("\nCache location: output/scraper_cache/")
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
