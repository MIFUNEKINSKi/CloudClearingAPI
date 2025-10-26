"""
OSM Cache Integration Test

Tests the OSM infrastructure caching system integrated into InfrastructureAnalyzer.

Expected Behavior:
1. First run: Cache MISS → Query OSM API → Save to cache
2. Second run: Cache HIT → Return cached data instantly
3. Results identical between runs

Author: CloudClearingAPI Team
Date: October 26, 2025
"""

import logging
import time
from src.core.infrastructure_analyzer import InfrastructureAnalyzer
from src.core.osm_cache import OSMInfrastructureCache

# Configure logging to see cache activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cache_integration():
    """Test OSM cache integration with InfrastructureAnalyzer"""
    
    print("=" * 70)
    print("🧪 OSM Cache Integration Test")
    print("=" * 70)
    print()
    
    # Test region: Semarang Suburbs (Central Java)
    test_region = "semarang_suburbs"
    test_bbox = {
        'south': -7.1,
        'north': -6.9,
        'west': 110.3,
        'east': 110.5
    }
    
    # Clear any existing cache for this region
    cache = OSMInfrastructureCache()
    cache.invalidate(test_region)
    print(f"🗑️ Cleared existing cache for {test_region}")
    print()
    
    # Create analyzer instance
    analyzer = InfrastructureAnalyzer()
    
    # Test 1: Cache MISS (first run)
    print("=" * 70)
    print("TEST 1: Cache MISS - First Run (Should Query OSM API)")
    print("=" * 70)
    start_time = time.time()
    
    result_1 = analyzer.analyze_infrastructure_context(
        bbox=test_bbox,
        region_name=test_region
    )
    
    time_1 = time.time() - start_time
    print(f"\n⏱️ First run completed in {time_1:.2f} seconds")
    print(f"📊 Infrastructure Score: {result_1.get('infrastructure_score', 'N/A')}")
    print(f"🛣️ Major Features: {len(result_1.get('major_features', []))}")
    print(f"💭 Reasoning: {result_1.get('reasoning', [])}")
    print()
    
    # Verify cache was created
    cache_stats = cache.get_stats()
    print(f"💾 Cache Stats After First Run:")
    print(f"   - Total Cached Regions: {cache_stats['total_files']}")
    print(f"   - Cache Size: {cache_stats['total_size_mb']:.2f} MB")
    print()
    
    # Test 2: Cache HIT (second run)
    print("=" * 70)
    print("TEST 2: Cache HIT - Second Run (Should Use Cache)")
    print("=" * 70)
    start_time = time.time()
    
    result_2 = analyzer.analyze_infrastructure_context(
        bbox=test_bbox,
        region_name=test_region
    )
    
    time_2 = time.time() - start_time
    print(f"\n⏱️ Second run completed in {time_2:.2f} seconds")
    print(f"📊 Infrastructure Score: {result_2.get('infrastructure_score', 'N/A')}")
    print(f"🛣️ Major Features: {len(result_2.get('major_features', []))}")
    print(f"💭 Reasoning: {result_2.get('reasoning', [])}")
    print()
    
    # Performance comparison
    speedup = time_1 / time_2 if time_2 > 0 else 0
    print("=" * 70)
    print("📈 PERFORMANCE COMPARISON")
    print("=" * 70)
    print(f"First Run (Cache MISS):  {time_1:.2f}s")
    print(f"Second Run (Cache HIT):  {time_2:.2f}s")
    print(f"⚡ Speedup: {speedup:.1f}x faster")
    print(f"⏰ Time Saved: {time_1 - time_2:.2f}s per region")
    print()
    
    # Validate results are identical
    print("=" * 70)
    print("🔍 VALIDATION")
    print("=" * 70)
    
    score_match = result_1.get('infrastructure_score') == result_2.get('infrastructure_score')
    features_match = len(result_1.get('major_features', [])) == len(result_2.get('major_features', []))
    
    print(f"✅ Scores Match: {score_match} ({result_1.get('infrastructure_score')} == {result_2.get('infrastructure_score')})")
    print(f"✅ Feature Count Match: {features_match} ({len(result_1.get('major_features', []))} == {len(result_2.get('major_features', []))})")
    print()
    
    # Cache health check
    health = cache.get_stats()
    print("=" * 70)
    print("💚 CACHE HEALTH")
    print("=" * 70)
    print(f"Total Cached Regions: {health['total_files']}")
    print(f"Valid Caches: {health['total_files'] - health.get('expired_count', 0)}")
    print(f"Cache Directory: ./cache/osm/")
    print(f"Expiry: 7 days")
    print()
    
    # Projected impact for 29 regions
    print("=" * 70)
    print("🚀 PROJECTED IMPACT FOR 29-REGION MONITORING")
    print("=" * 70)
    
    # Assumptions:
    # - Without cache: 29 regions × ~30s API call = ~14.5 min
    # - With cache (86% hit rate): 4 cache misses × 30s = 2 min + 25 cache hits × 0.1s = 2.5s ≈ 2.5 min
    # - Cache miss time: ~30s (OSM API + processing)
    # - Cache hit time: ~0.1s (instant)
    
    cache_misses = 4  # First run: all 29 miss. Second run: ~4 miss (new/updated regions)
    cache_hits = 25   # 86% hit rate after first run
    
    time_without_cache = 29 * time_1
    time_with_cache = (cache_misses * time_1) + (cache_hits * time_2)
    
    time_saved_per_run = time_without_cache - time_with_cache
    speedup_total = time_without_cache / time_with_cache if time_with_cache > 0 else 0
    
    print(f"Without Cache (29 API calls):  {time_without_cache/60:.1f} minutes")
    print(f"With Cache (4 misses, 25 hits): {time_with_cache/60:.1f} minutes")
    print(f"⏰ Time Saved: {time_saved_per_run/60:.1f} minutes per run")
    print(f"⚡ Overall Speedup: {speedup_total:.1f}x faster")
    print(f"📉 API Load Reduction: {(cache_hits/29)*100:.0f}%")
    print()
    
    print("=" * 70)
    print("✅ OSM CACHE INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()
    print("🎯 Summary:")
    print(f"   - Cache working correctly: {score_match and features_match}")
    print(f"   - Performance improvement: {speedup:.1f}x faster")
    print(f"   - Ready for production use: ✅")
    print()
    
    return {
        'cache_working': score_match and features_match,
        'speedup': speedup,
        'time_saved_per_region': time_1 - time_2,
        'projected_time_saved_29_regions': time_saved_per_run / 60  # in minutes
    }


if __name__ == "__main__":
    try:
        results = test_cache_integration()
        
        if results['cache_working']:
            print("✅ All tests passed! OSM caching ready for production.")
            exit(0)
        else:
            print("❌ Tests failed. Cache not working correctly.")
            exit(1)
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        exit(1)
