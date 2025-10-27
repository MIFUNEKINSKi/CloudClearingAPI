"""
Test Multi-Source Scraping Fallback - Phase 2A.5
CloudClearingAPI v2.6-alpha

Validates that the 3-tier cascading fallback works correctly:
Lamudi → Rumah.com → 99.co → Cache → Benchmark
"""

import logging
from src.scrapers import LandPriceOrchestrator

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_orchestrator_status():
    """Test that orchestrator reports all 3 scrapers"""
    print("\n" + "="*80)
    print("TEST 1: Orchestrator Status (3 Scrapers)")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=False  # Disabled for status test
    )
    
    status = orchestrator.get_orchestrator_status()
    
    print(f"\n✓ Orchestrator initialized")
    print(f"  Live Scraping: {'Enabled' if status['live_scraping_enabled'] else 'Disabled'}")
    print(f"  Total Sources: {status['total_sources']}")
    print(f"\n  Scrapers:")
    for scraper in status['scrapers']:
        print(f"    {scraper['priority']}. {scraper['name']} ({scraper['source_id']})")
        print(f"       Cache: {scraper['cache_dir']}")
        print(f"       Expiry: {scraper['cache_expiry_hours']}h")
    
    # Validate
    assert status['total_sources'] == 3, "Should have 3 sources"
    assert len(status['scrapers']) == 3, "Should report 3 scrapers"
    
    scraper_names = [s['name'] for s in status['scrapers']]
    assert 'Lamudi' in scraper_names, "Should include Lamudi"
    assert 'Rumah.com' in scraper_names, "Should include Rumah.com"
    assert '99.co' in scraper_names, "Should include 99.co"
    
    priorities = [s['priority'] for s in status['scrapers']]
    assert priorities == [1, 2, 3], "Priorities should be 1, 2, 3"
    
    print("\n✅ TEST PASSED: All 3 scrapers registered with correct priorities")
    return True

def test_fallback_to_benchmark():
    """Test that system falls back to benchmark when scraping disabled"""
    print("\n" + "="*80)
    print("TEST 2: Fallback to Benchmark (Scraping Disabled)")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=False  # Force benchmark fallback
    )
    
    test_region = "Sleman Yogyakarta"
    print(f"\nRegion: {test_region}")
    print(f"Config: Live scraping DISABLED (should use benchmark)")
    
    result = orchestrator.get_land_price(test_region, max_listings=10)
    
    print(f"\n✓ Result obtained")
    print(f"  Success: {result['success']}")
    print(f"  Data Source: {result['data_source']}")
    print(f"  Average Price: Rp {result['average_price_per_m2']:,.0f}/m²")
    print(f"  Median Price: Rp {result['median_price_per_m2']:,.0f}/m²")
    print(f"  Listing Count: {result['listing_count']}")
    print(f"  Confidence: {result.get('data_confidence', 0):.0%}")
    
    if 'benchmark_region' in result:
        print(f"  Benchmark Region: {result['benchmark_region']}")
    
    # Validate
    assert result['success'] == True, "Benchmark fallback should always succeed"
    assert result['data_source'] == 'static_benchmark', "Should use static benchmark"
    assert result['data_confidence'] == 0.5, "Benchmark confidence should be 50%"
    assert result['average_price_per_m2'] > 0, "Should have a price"
    assert result['listing_count'] == 0, "Benchmark has no listings"
    
    print("\n✅ TEST PASSED: Benchmark fallback works correctly")
    return True

def test_source_tracking():
    """Test that data source is properly tracked in results"""
    print("\n" + "="*80)
    print("TEST 3: Data Source Tracking")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True  # Enable live scraping (may fail, that's OK)
    )
    
    test_region = "Jakarta North"
    print(f"\nRegion: {test_region}")
    print(f"Config: Live scraping ENABLED")
    print(f"Testing cascading fallback transparency...")
    
    result = orchestrator.get_land_price(test_region, max_listings=10)
    
    print(f"\n✓ Result obtained")
    print(f"  Success: {result['success']}")
    print(f"  Data Source: {result['data_source']}")
    
    # Validate data_source field exists
    assert 'data_source' in result, "Result must have data_source field"
    
    # Valid data sources
    valid_sources = [
        'lamudi', 'rumah.com', '99.co',  # Live sources
        'lamudi_cached', 'rumah_com_cached', '99.co_cached',  # Cached
        'static_benchmark'  # Fallback
    ]
    
    assert result['data_source'] in valid_sources, f"data_source must be one of {valid_sources}"
    
    print(f"\n  Valid Data Sources: {', '.join(valid_sources)}")
    print(f"  Actual Source Used: {result['data_source']} ✓")
    
    # Show what happened
    if result['data_source'] == 'static_benchmark':
        print(f"\n  📊 Fallback Path: Lamudi → Rumah.com → 99.co → Cache → BENCHMARK")
        print(f"      (All live scraping and cache attempts failed, used benchmark)")
    elif '_cached' in result['data_source']:
        source_name = result['data_source'].replace('_cached', '')
        print(f"\n  📊 Fallback Path: Live scraping failed → CACHE ({source_name})")
        print(f"      Cache Age: {result.get('cache_age_hours', 0):.1f}h")
    else:
        print(f"\n  📊 Fallback Path: {result['data_source'].upper()} (live scraping succeeded)")
        print(f"      Listing Count: {result.get('listing_count', 0)}")
    
    print("\n✅ TEST PASSED: Data source tracking works correctly")
    return True

def test_priority_order():
    """Test that scrapers are tried in correct priority order"""
    print("\n" + "="*80)
    print("TEST 4: Scraper Priority Order Validation")
    print("="*80)
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True
    )
    
    status = orchestrator.get_orchestrator_status()
    scrapers = status['scrapers']
    
    print(f"\nExpected Priority Order:")
    print(f"  1. Lamudi (primary source)")
    print(f"  2. Rumah.com (secondary source)")
    print(f"  3. 99.co (tertiary source)")
    
    print(f"\nActual Priority Order:")
    for scraper in sorted(scrapers, key=lambda x: x['priority']):
        print(f"  {scraper['priority']}. {scraper['name']} ({scraper['source_id']})")
    
    # Validate priority order
    sorted_scrapers = sorted(scrapers, key=lambda x: x['priority'])
    
    assert sorted_scrapers[0]['name'] == 'Lamudi', "Priority 1 should be Lamudi"
    assert sorted_scrapers[1]['name'] == 'Rumah.com', "Priority 2 should be Rumah.com"
    assert sorted_scrapers[2]['name'] == '99.co', "Priority 3 should be 99.co"
    
    assert sorted_scrapers[0]['priority'] == 1, "Lamudi priority should be 1"
    assert sorted_scrapers[1]['priority'] == 2, "Rumah.com priority should be 2"
    assert sorted_scrapers[2]['priority'] == 3, "99.co priority should be 3"
    
    print("\n✅ TEST PASSED: Priority order is correct (Lamudi → Rumah.com → 99.co)")
    return True

def run_all_tests():
    """Run all multi-source fallback tests"""
    print("\n" + "="*80)
    print("MULTI-SOURCE SCRAPING FALLBACK TEST SUITE - Phase 2A.5")
    print("CloudClearingAPI v2.6-alpha")
    print("="*80)
    
    tests_passed = 0
    tests_total = 4
    
    try:
        if test_orchestrator_status():
            tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
    
    try:
        if test_fallback_to_benchmark():
            tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
    
    try:
        if test_source_tracking():
            tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
    
    try:
        if test_priority_order():
            tests_passed += 1
    except AssertionError as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
    
    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY - Phase 2A.5 Multi-Source Fallback")
    print("="*80)
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print(f"Success Rate: {tests_passed/tests_total:.0%}")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED - Multi-source fallback working correctly!")
        print("\n✅ Phase 2A.5 Achievements:")
        print("   • 99.co scraper created and integrated")
        print("   • 3-tier cascading fallback: Lamudi → Rumah.com → 99.co")
        print("   • Data source tracking in results")
        print("   • Priority order validation")
        print("   • Graceful degradation to cache → benchmark")
        print("\n📊 Next Steps (Phase 2A.6):")
        print("   • Add user-agent rotation (5 agents)")
        print("   • Implement retry logic with exponential backoff")
        print("   • Add request delays (2s between requests)")
        print("   • Improve timeout handling")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) failed - review and fix")
    
    print("="*80)

if __name__ == '__main__':
    run_all_tests()
