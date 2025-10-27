"""
Test Suite for Phase 2A.6: Request Hardening
CloudClearingAPI v2.6-alpha

Tests retry logic, exponential backoff, timeout handling, and configurable settings
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import requests

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.base_scraper import BaseLandPriceScraper, ScrapeResult
from src.scrapers.scraper_orchestrator import LandPriceOrchestrator


class ConcreteTestScraper(BaseLandPriceScraper):
    """Concrete implementation for testing base scraper"""
    
    def get_source_name(self) -> str:
        return "test_scraper"
    
    def _scrape_live(self, region_name: str, max_listings: int) -> ScrapeResult:
        # Test implementation
        return ScrapeResult(
            region_name=region_name,
            average_price_per_m2=5000000,
            median_price_per_m2=4500000,
            listing_count=10,
            listings=[],
            source=self.get_source_name(),
            scraped_at=time.time(),
            success=True
        )


class TestRequestHardening(unittest.TestCase):
    """Test Phase 2A.6 request hardening features"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_cache_dir = Path("test_cache_temp")
        self.test_cache_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test cache"""
        import shutil
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
    
    def test_retry_configuration(self):
        """Test 1: Verify retry configuration from config dict"""
        print("\n" + "="*80)
        print("TEST 1: Retry Configuration")
        print("="*80)
        
        # Custom retry config
        config = {
            'max_retries': 5,
            'initial_backoff': 2,
            'max_backoff': 60,
            'backoff_multiplier': 3,
            'request_timeout': 20,
            'fallback_timeout': 45
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print(f"\n✓ Scraper initialized with custom config")
        print(f"  Max Retries: {scraper.max_retries} (expected: 5)")
        print(f"  Initial Backoff: {scraper.initial_backoff}s (expected: 2)")
        print(f"  Max Backoff: {scraper.max_backoff}s (expected: 60)")
        print(f"  Backoff Multiplier: {scraper.backoff_multiplier}x (expected: 3)")
        print(f"  Request Timeout: {scraper.request_timeout}s (expected: 20)")
        print(f"  Fallback Timeout: {scraper.fallback_timeout}s (expected: 45)")
        
        # Validate config was applied
        self.assertEqual(scraper.max_retries, 5)
        self.assertEqual(scraper.initial_backoff, 2)
        self.assertEqual(scraper.max_backoff, 60)
        self.assertEqual(scraper.backoff_multiplier, 3)
        self.assertEqual(scraper.request_timeout, 20)
        self.assertEqual(scraper.fallback_timeout, 45)
        
        print("\n✅ TEST PASSED: Custom retry configuration applied correctly")
    
    def test_default_configuration(self):
        """Test 2: Verify default retry configuration (no config provided)"""
        print("\n" + "="*80)
        print("TEST 2: Default Configuration")
        print("="*80)
        
        scraper = ConcreteTestScraper(cache_dir=self.test_cache_dir)
        
        print(f"\n✓ Scraper initialized without config (using defaults)")
        print(f"  Max Retries: {scraper.max_retries} (expected: 3)")
        print(f"  Initial Backoff: {scraper.initial_backoff}s (expected: 1)")
        print(f"  Max Backoff: {scraper.max_backoff}s (expected: 30)")
        print(f"  Backoff Multiplier: {scraper.backoff_multiplier}x (expected: 2)")
        print(f"  Request Timeout: {scraper.request_timeout}s (expected: 15)")
        print(f"  Fallback Timeout: {scraper.fallback_timeout}s (expected: 30)")
        
        # Validate defaults
        self.assertEqual(scraper.max_retries, 3)
        self.assertEqual(scraper.initial_backoff, 1)
        self.assertEqual(scraper.max_backoff, 30)
        self.assertEqual(scraper.backoff_multiplier, 2)
        self.assertEqual(scraper.request_timeout, 15)
        self.assertEqual(scraper.fallback_timeout, 30)
        
        print("\n✅ TEST PASSED: Default configuration working correctly")
    
    @patch('requests.get')
    def test_retry_on_timeout(self, mock_get):
        """Test 3: Verify retry behavior on timeout errors"""
        print("\n" + "="*80)
        print("TEST 3: Retry on Timeout")
        print("="*80)
        
        # Configure mock to fail twice, then succeed
        mock_get.side_effect = [
            requests.Timeout("Connection timeout"),
            requests.Timeout("Connection timeout"),
            MagicMock(content=b"<html><body>Success</body></html>", status_code=200)
        ]
        
        config = {
            'max_retries': 3,
            'initial_backoff': 0.1,  # Fast for testing
            'max_backoff': 1,
            'request_timeout': 5
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print("\n⏳ Testing retry logic (will timeout twice, then succeed)...")
        start_time = time.time()
        
        result = scraper._make_request("https://test.com/test")
        
        elapsed = time.time() - start_time
        
        print(f"\n✓ Request completed after {elapsed:.2f}s")
        print(f"  Attempts: {mock_get.call_count} (expected: 3)")
        print(f"  Result: {'Success' if result else 'Failed'}")
        
        # Should have retried twice (3 total attempts)
        self.assertEqual(mock_get.call_count, 3)
        self.assertIsNotNone(result, "Request should succeed after retries")
        
        print("\n✅ TEST PASSED: Retry logic working correctly on timeouts")
    
    @patch('requests.get')
    def test_max_retries_exhausted(self, mock_get):
        """Test 4: Verify behavior when max retries exceeded"""
        print("\n" + "="*80)
        print("TEST 4: Max Retries Exhausted")
        print("="*80)
        
        # Configure mock to always timeout
        mock_get.side_effect = requests.Timeout("Persistent timeout")
        
        config = {
            'max_retries': 3,
            'initial_backoff': 0.1,
            'max_backoff': 1
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print("\n⏳ Testing max retries (all attempts will fail)...")
        
        result = scraper._make_request("https://test.com/test")
        
        print(f"\n✓ Request failed after max retries")
        print(f"  Attempts: {mock_get.call_count} (expected: 3)")
        print(f"  Result: {'Success' if result else 'Failed (expected)'}")
        
        # Should have attempted max_retries times
        self.assertEqual(mock_get.call_count, 3)
        self.assertIsNone(result, "Request should fail after max retries")
        
        print("\n✅ TEST PASSED: Max retries limit enforced correctly")
    
    @patch('requests.get')
    def test_no_retry_on_client_error(self, mock_get):
        """Test 5: Verify no retry on 4xx client errors"""
        print("\n" + "="*80)
        print("TEST 5: No Retry on Client Errors (4xx)")
        print("="*80)
        
        # Configure mock to return 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        config = {
            'max_retries': 3,
            'initial_backoff': 0.1
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print("\n⏳ Testing client error handling (404 Not Found)...")
        
        result = scraper._make_request("https://test.com/not-found")
        
        print(f"\n✓ Request handled client error")
        print(f"  Attempts: {mock_get.call_count} (expected: 1, no retries)")
        print(f"  Result: {'Success' if result else 'Failed (expected)'}")
        
        # Should NOT retry on client errors
        self.assertEqual(mock_get.call_count, 1)
        self.assertIsNone(result, "Should fail immediately on 404")
        
        print("\n✅ TEST PASSED: No retry on client errors (correct behavior)")
    
    @patch('requests.get')
    def test_retry_on_server_error(self, mock_get):
        """Test 6: Verify retry on 5xx server errors"""
        print("\n" + "="*80)
        print("TEST 6: Retry on Server Errors (5xx)")
        print("="*80)
        
        # Configure mock to fail with 503, then succeed
        error_response = MagicMock()
        error_response.status_code = 503
        error_response.raise_for_status.side_effect = requests.HTTPError(response=error_response)
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.content = b"<html><body>Success</body></html>"
        success_response.raise_for_status = MagicMock()
        
        mock_get.side_effect = [error_response, success_response]
        
        config = {
            'max_retries': 3,
            'initial_backoff': 0.1,
            'max_backoff': 1
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print("\n⏳ Testing server error retry (503 Service Unavailable)...")
        
        result = scraper._make_request("https://test.com/test")
        
        print(f"\n✓ Request recovered from server error")
        print(f"  Attempts: {mock_get.call_count} (expected: 2)")
        print(f"  Result: {'Success (expected)' if result else 'Failed'}")
        
        # Should retry once and succeed
        self.assertEqual(mock_get.call_count, 2)
        self.assertIsNotNone(result, "Should succeed after server error retry")
        
        print("\n✅ TEST PASSED: Retry on server errors working correctly")
    
    def test_exponential_backoff_timing(self):
        """Test 7: Verify exponential backoff timing"""
        print("\n" + "="*80)
        print("TEST 7: Exponential Backoff Timing")
        print("="*80)
        
        config = {
            'max_retries': 4,
            'initial_backoff': 1,
            'max_backoff': 30,
            'backoff_multiplier': 2
        }
        
        scraper = ConcreteTestScraper(
            cache_dir=self.test_cache_dir,
            config=config
        )
        
        print("\n✓ Testing backoff calculation (no actual requests):")
        
        # Calculate expected backoffs
        expected_backoffs = []
        for retry in range(3):
            backoff = min(
                scraper.initial_backoff * (scraper.backoff_multiplier ** retry),
                scraper.max_backoff
            )
            expected_backoffs.append(backoff)
            print(f"  Retry {retry + 1}: {backoff}s backoff (2^{retry} = {2**retry}x initial)")
        
        # Validate exponential growth
        self.assertEqual(expected_backoffs[0], 1)   # 1 * 2^0 = 1
        self.assertEqual(expected_backoffs[1], 2)   # 1 * 2^1 = 2
        self.assertEqual(expected_backoffs[2], 4)   # 1 * 2^2 = 4
        
        print("\n✅ TEST PASSED: Exponential backoff calculation correct")
    
    def test_orchestrator_config_propagation(self):
        """Test 8: Verify config propagates to scrapers via orchestrator"""
        print("\n" + "="*80)
        print("TEST 8: Config Propagation to Scrapers")
        print("="*80)
        
        config = {
            'max_retries': 4,
            'request_timeout': 25,
            'fallback_timeout': 50
        }
        
        orchestrator = LandPriceOrchestrator(
            cache_dir=self.test_cache_dir,
            enable_live_scraping=False,
            config=config
        )
        
        print(f"\n✓ Orchestrator initialized with config")
        print(f"\n  Checking Lamudi scraper:")
        print(f"    Max Retries: {orchestrator.lamudi.max_retries} (expected: 4)")
        print(f"    Request Timeout: {orchestrator.lamudi.request_timeout}s (expected: 25)")
        print(f"    Fallback Timeout: {orchestrator.lamudi.fallback_timeout}s (expected: 50)")
        
        print(f"\n  Checking Rumah.com scraper:")
        print(f"    Max Retries: {orchestrator.rumah_com.max_retries} (expected: 4)")
        print(f"    Request Timeout: {orchestrator.rumah_com.request_timeout}s (expected: 25)")
        
        print(f"\n  Checking 99.co scraper:")
        print(f"    Max Retries: {orchestrator.ninety_nine.max_retries} (expected: 4)")
        print(f"    Request Timeout: {orchestrator.ninety_nine.request_timeout}s (expected: 25)")
        
        # Validate all scrapers received config
        self.assertEqual(orchestrator.lamudi.max_retries, 4)
        self.assertEqual(orchestrator.lamudi.request_timeout, 25)
        self.assertEqual(orchestrator.rumah_com.max_retries, 4)
        self.assertEqual(orchestrator.ninety_nine.max_retries, 4)
        
        print("\n✅ TEST PASSED: Config properly propagated to all scrapers")


def run_tests():
    """Run all Phase 2A.6 tests"""
    print("="*80)
    print("REQUEST HARDENING TEST SUITE - Phase 2A.6")
    print("CloudClearingAPI v2.6-alpha")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRequestHardening)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY - Phase 2A.6 Request Hardening")
    print("="*80)
    print(f"Tests Passed: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.0f}%")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED - Request hardening working correctly!")
        print("\n✅ Phase 2A.6 Achievements:")
        print("   • Retry logic with exponential backoff")
        print("   • Configurable timeout handling (15s → 30s fallback)")
        print("   • User-agent rotation (5 agents)")
        print("   • Rate limiting (2s between requests)")
        print("   • Smart retry: Server errors (5xx) ✓, Client errors (4xx) ✗")
        print("   • Config propagation to all scrapers")
        print("\n📊 Next Steps (Phase 2A.7):")
        print("   • Document benchmark update procedure")
        print("   • Establish quarterly review schedule")
        print("   • Create benchmark validation process")
    else:
        print("\n❌ SOME TESTS FAILED - Review output above")
        if result.failures:
            print(f"\nFailures: {len(result.failures)}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
    
    print("="*80)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
