"""
Land Price Scraper Orchestrator
CloudClearingAPI - October 19, 2025
Phase 2A.6: Enhanced with configurable retry logic and timeout handling

Coordinates multiple scrapers with priority logic:
1. Live scraping (Lamudi, Rumah.com, 99.co)
2. Cached results (if < 24-48h old)
3. Fallback to static regional benchmarks
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base_scraper import ScrapeResult
from .lamudi_scraper import LamudiScraper
from .rumah_scraper import RumahComScraper
from .ninety_nine_scraper import NinetyNineScraper  # Phase 2A.5: Third-tier fallback

logger = logging.getLogger(__name__)


class LandPriceOrchestrator:
    """
    Orchestrates land price data collection from multiple sources with fallback logic
    
    Priority (Phase 2A.5 - Multi-Source Fallback):
    1. Live scraping (try Lamudi first, then Rumah.com, then 99.co)
    2. Cached results (if valid and not expired)
    3. Static regional benchmarks (last resort)
    """
    
    def __init__(self, 
                 cache_dir: Optional[Path] = None,
                 cache_expiry_hours: int = 24,
                 enable_live_scraping: bool = True,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator with scrapers
        
        Args:
            cache_dir: Directory for caching scraped data
            cache_expiry_hours: Hours before cache expires
            enable_live_scraping: If False, skip live scraping and use cache/fallback only
            config: Optional config dict for retry logic and timeouts (Phase 2A.6)
        """
        self.enable_live_scraping = enable_live_scraping
        
        # Initialize scrapers (Phase 2A.5: Added 99.co as third source)
        # Phase 2A.6: Pass config to scrapers for retry/timeout settings
        self.lamudi = LamudiScraper(
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            config=config
        )
        self.rumah_com = RumahComScraper(
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            config=config
        )
        self.ninety_nine = NinetyNineScraper(
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            config=config
        )
        
        # Static regional benchmarks (fallback)
        self.regional_benchmarks = {
            'jakarta': {
                'current_avg': 8_500_000,
                'historical_appreciation': 0.15,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark'
            },
            'bali': {
                'current_avg': 12_000_000,
                'historical_appreciation': 0.20,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark'
            },
            'yogyakarta': {
                'current_avg': 4_500_000,
                'historical_appreciation': 0.12,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark'
            },
            'surabaya': {
                'current_avg': 6_500_000,
                'historical_appreciation': 0.14,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark'
            },
            'bandung': {
                'current_avg': 5_000_000,
                'historical_appreciation': 0.13,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark'
            },
            'semarang': {
                'current_avg': 3_500_000,
                'historical_appreciation': 0.11,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark'
            }
        }
        
        logger.info(f"Initialized LandPriceOrchestrator (live_scraping={'enabled' if enable_live_scraping else 'disabled'})")
    
    def get_land_price(self, region_name: str, max_listings: int = 20) -> Dict[str, Any]:
        """
        Get land price data with cascading fallback logic
        
        Priority (Phase 2A.5 - Multi-Source Fallback):
        1. Try live scraping from Lamudi
        2. If Lamudi fails, try Rumah.com
        3. If Rumah.com fails, try 99.co
        4. If all fail, check cache from any source
        5. If cache empty/expired, use static benchmark
        
        Args:
            region_name: Region to get prices for (e.g., "Sleman Yogyakarta")
            max_listings: Maximum listings to scrape
            
        Returns:
            Dict with price data and metadata (includes 'data_source' field)
        """
        logger.info(f"Orchestrating land price data for: {region_name}")
        
        # Phase 1: Live Scraping (if enabled) - Try all 3 sources sequentially
        if self.enable_live_scraping:
            logger.info("Phase 1: Attempting live scraping (3-source cascading fallback)...")
            
            # Try Lamudi first (primary source)
            lamudi_result = self._try_live_scrape(self.lamudi, region_name, max_listings)
            
            if lamudi_result['success']:
                logger.info(f"✓ Live scraping successful (Lamudi): {lamudi_result['listing_count']} listings")
                return lamudi_result
            
            logger.warning(f"✗ Lamudi scraping failed: {lamudi_result.get('error')}")
            
            # Try Rumah.com as second source
            rumah_result = self._try_live_scrape(self.rumah_com, region_name, max_listings)
            
            if rumah_result['success']:
                logger.info(f"✓ Live scraping successful (Rumah.com): {rumah_result['listing_count']} listings")
                return rumah_result
            
            logger.warning(f"✗ Rumah.com scraping failed: {rumah_result.get('error')}")
            
            # Phase 2A.5: Try 99.co as third source (NEW)
            ninety_nine_result = self._try_live_scrape(self.ninety_nine, region_name, max_listings)
            
            if ninety_nine_result['success']:
                logger.info(f"✓ Live scraping successful (99.co): {ninety_nine_result['listing_count']} listings")
                return ninety_nine_result
            
            logger.warning(f"✗ 99.co scraping failed: {ninety_nine_result.get('error')}")
            logger.warning("✗ All 3 live scraping sources failed")
        else:
            logger.info("Live scraping disabled, skipping Phase 1")
        
        # Phase 2: Check Cache (even if expired, it's better than nothing)
        logger.info("Phase 2: Checking cache from all sources...")
        cache_result = self._check_cache(region_name)
        
        if cache_result:
            logger.info(f"✓ Using cached data (source: {cache_result['data_source']}, age: {cache_result.get('cache_age_hours', 0):.1f}h)")
            return cache_result
        
        logger.warning("✗ No valid cache found from any source")
        
        # Phase 3: Fallback to Static Benchmark
        logger.info("Phase 3: Using static regional benchmark (last resort)")
        benchmark_result = self._get_benchmark_fallback(region_name)
        
        logger.info(f"✓ Using static benchmark: {benchmark_result['average_price_per_m2']:,.0f} IDR/m²")
        
        return benchmark_result
    
    def _try_live_scrape(self, scraper, region_name: str, max_listings: int) -> Dict[str, Any]:
        """
        Attempt live scraping with a scraper
        
        Args:
            scraper: Scraper instance (LamudiScraper or RumahComScraper)
            region_name: Region to scrape
            max_listings: Max listings
            
        Returns:
            Dict with results or error
        """
        try:
            result = scraper.get_price_data(region_name, max_listings)
            
            if result.success and result.listing_count > 0:
                return self._convert_scrape_result_to_dict(result, region_name)  # Pass region_name for trend calc
            else:
                return {
                    'success': False,
                    'error': result.error_message or 'No listings found',
                    'data_source': scraper.get_source_name()
                }
        
        except Exception as e:
            logger.error(f"Exception during {scraper.get_source_name()} scraping: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data_source': scraper.get_source_name()
            }
    
    def _check_cache(self, region_name: str) -> Optional[Dict[str, Any]]:
        """
        Check cache from all scrapers (even if expired)
        
        Phase 2A.5: Now checks all 3 sources (Lamudi, Rumah.com, 99.co)
        
        Args:
            region_name: Region to check
            
        Returns:
            Dict with cached data or None
        """
        # Try Lamudi cache first
        lamudi_cache = self.lamudi._load_from_cache(region_name)
        if lamudi_cache and lamudi_cache.success:
            result = self._convert_scrape_result_to_dict(lamudi_cache, region_name)  # Pass region_name
            result['cache_age_hours'] = self.lamudi._get_cache_age(lamudi_cache)
            result['data_source'] = 'lamudi_cached'
            return result
        
        # Try Rumah.com cache
        rumah_cache = self.rumah_com._load_from_cache(region_name)
        if rumah_cache and rumah_cache.success:
            result = self._convert_scrape_result_to_dict(rumah_cache, region_name)  # Pass region_name
            result['cache_age_hours'] = self.rumah_com._get_cache_age(rumah_cache)
            result['data_source'] = 'rumah_com_cached'
            return result
        
        # Phase 2A.5: Try 99.co cache (NEW)
        ninety_nine_cache = self.ninety_nine._load_from_cache(region_name)
        if ninety_nine_cache and ninety_nine_cache.success:
            result = self._convert_scrape_result_to_dict(ninety_nine_cache, region_name)  # Pass region_name
            result['cache_age_hours'] = self.ninety_nine._get_cache_age(ninety_nine_cache)
            result['data_source'] = '99.co_cached'
            return result
        
        return None
    
    def _get_benchmark_fallback(self, region_name: str) -> Dict[str, Any]:
        """
        Get static regional benchmark as last resort fallback
        
        Args:
            region_name: Region name
            
        Returns:
            Dict with benchmark data including trend estimates
        """
        benchmark = self._find_nearest_benchmark(region_name)
        
        # Use historical appreciation to estimate trend
        annual_appreciation = benchmark.get('historical_appreciation', 5.0)
        monthly_trend = annual_appreciation / 12.0
        market_heat = self._classify_market_heat(annual_appreciation)
        
        return {
            'success': True,
            'average_price_per_m2': benchmark['current_avg'],
            'median_price_per_m2': benchmark['current_avg'],
            'listing_count': 0,
            'data_source': 'static_benchmark',
            'benchmark_region': self._get_benchmark_region_name(region_name),
            'data_confidence': 0.5,  # Lower confidence for static data
            'historical_appreciation': annual_appreciation,
            'market_liquidity': benchmark['market_liquidity'],
            'price_trend_30d': monthly_trend,  # NEW: Estimate from historical data
            'market_heat': market_heat  # NEW: Classify from appreciation rate
        }
    
    def _find_nearest_benchmark(self, region_name: str) -> Dict[str, Any]:
        """Find nearest regional benchmark for a region"""
        region_lower = region_name.lower()
        
        # Direct matches
        for benchmark_name, data in self.regional_benchmarks.items():
            if benchmark_name in region_lower:
                return data
        
        # Province-level matches
        if 'jakarta' in region_lower or 'tangerang' in region_lower or 'bekasi' in region_lower:
            return self.regional_benchmarks['jakarta']
        elif 'yogya' in region_lower or 'sleman' in region_lower or 'bantul' in region_lower:
            return self.regional_benchmarks['yogyakarta']
        elif 'surabaya' in region_lower or 'sidoarjo' in region_lower:
            return self.regional_benchmarks['surabaya']
        elif 'bandung' in region_lower:
            return self.regional_benchmarks['bandung']
        elif 'semarang' in region_lower or 'solo' in region_lower:
            return self.regional_benchmarks['semarang']
        
        # Default to Yogyakarta (mid-tier market)
        return self.regional_benchmarks['yogyakarta']
    
    def _get_benchmark_region_name(self, region_name: str) -> str:
        """Get the name of the benchmark region used"""
        region_lower = region_name.lower()
        
        for benchmark_name in self.regional_benchmarks.keys():
            if benchmark_name in region_lower:
                return benchmark_name.capitalize()
        
        # Province-level
        if 'jakarta' in region_lower or 'tangerang' in region_lower or 'bekasi' in region_lower:
            return 'Jakarta'
        elif 'yogya' in region_lower or 'sleman' in region_lower or 'bantul' in region_lower:
            return 'Yogyakarta'
        elif 'surabaya' in region_lower or 'sidoarjo' in region_lower:
            return 'Surabaya'
        elif 'bandung' in region_lower:
            return 'Bandung'
        elif 'semarang' in region_lower or 'solo' in region_lower:
            return 'Semarang'
        
        return 'Yogyakarta'  # Default
    
    def _calculate_price_trend(self, region_name: str, current_price: float) -> tuple:
        """
        Calculate 30-day price trend by comparing current price with cached historical data
        
        Strategy:
        1. Try to find cache from 25-35 days ago (ideal window)
        2. If not found, use benchmark historical_appreciation rate
        3. Calculate trend percentage and classify market heat
        
        Args:
            region_name: Region name
            current_price: Current average price per m²
            
        Returns:
            (price_trend_pct: float, market_heat: str)
        """
        try:
            # Try to load historical cache (from any scraper)
            # Look for cache that's approximately 30 days old
            from datetime import datetime, timedelta
            import os
            
            target_age_days = 30
            tolerance_days = 5  # Accept cache 25-35 days old
            
            # Check all scraper caches for historical data
            for scraper in [self.lamudi, self.rumah_com, self.ninety_nine]:
                cache_file = scraper.cache_dir / f"{region_name.lower().replace(' ', '_')}.json"
                
                if cache_file.exists():
                    try:
                        # Check file age
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                        age_days = (datetime.now() - file_mtime).days
                        
                        # If cache is in the ideal window (25-35 days)
                        if target_age_days - tolerance_days <= age_days <= target_age_days + tolerance_days:
                            cached_result = scraper._load_from_cache(region_name)
                            if cached_result and cached_result.success and cached_result.average_price_per_m2 > 0:
                                historical_price = cached_result.average_price_per_m2
                                
                                # Calculate percentage change
                                trend_pct = ((current_price - historical_price) / historical_price) * 100
                                
                                # Classify market heat based on annualized trend
                                # 30-day trend → annualized: * (365/30) = * 12.17
                                annualized_trend = trend_pct * 12.17
                                market_heat = self._classify_market_heat(annualized_trend)
                                
                                logger.info(f"   📊 Price Trend ({age_days}d): {trend_pct:+.1f}% (annualized: {annualized_trend:+.1f}%)")
                                
                                return trend_pct, market_heat
                    except Exception as e:
                        logger.debug(f"   Error reading cache from {scraper.get_source_name()}: {e}")
                        continue
            
            # No suitable historical cache found - use benchmark appreciation rate
            benchmark = self._find_nearest_benchmark(region_name)
            annual_appreciation = benchmark.get('historical_appreciation', 5.0)  # Default 5%/yr
            
            # Convert annual rate to 30-day rate
            monthly_rate = annual_appreciation / 12.0
            trend_pct = monthly_rate  # Approximate 30-day trend
            
            market_heat = self._classify_market_heat(annual_appreciation)
            
            logger.info(f"   📊 Price Trend (benchmark): {trend_pct:+.1f}%/mo (annual: {annual_appreciation:+.1f}%/yr)")
            
            return trend_pct, market_heat
            
        except Exception as e:
            logger.warning(f"   ⚠️ Price trend calculation failed: {e}")
            return 0.0, 'neutral'
    
    def _classify_market_heat(self, annualized_trend_pct: float) -> str:
        """
        Classify market heat based on annualized price trend
        
        Args:
            annualized_trend_pct: Annualized price trend percentage
            
        Returns:
            Market heat classification string
        """
        if annualized_trend_pct >= 15:
            return 'booming'
        elif annualized_trend_pct >= 8:
            return 'strong'
        elif annualized_trend_pct >= 2:
            return 'warming'
        elif annualized_trend_pct >= 0:
            return 'stable'
        elif annualized_trend_pct >= -5:
            return 'cooling'
        else:
            return 'declining'
    
    def _convert_scrape_result_to_dict(self, result: ScrapeResult, region_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert ScrapeResult to dict for consistency
        
        Args:
            result: ScrapeResult from scraper
            region_name: Optional region name for trend calculation
            
        Returns:
            Dict with price data including trend calculations
        """
        # Calculate price trend if we have historical cache data
        price_trend_30d = 0.0
        market_heat = 'neutral'
        
        if region_name:
            price_trend_30d, market_heat = self._calculate_price_trend(
                region_name, 
                result.average_price_per_m2
            )
        
        return {
            'success': result.success,
            'average_price_per_m2': result.average_price_per_m2,
            'median_price_per_m2': result.median_price_per_m2,
            'listing_count': result.listing_count,
            'data_source': result.source,
            'scraped_at': result.scraped_at.isoformat(),
            'data_confidence': 0.85,  # High confidence for live data
            'price_trend_30d': price_trend_30d,  # NEW: 30-day price trend percentage
            'market_heat': market_heat,  # NEW: Market heat classification
            'listings': [
                {
                    'price_per_m2': listing.price_per_m2,
                    'total_price': listing.total_price,
                    'size_m2': listing.size_m2,
                    'location': listing.location,
                    'url': listing.source_url
                }
                for listing in result.listings
            ]
        }
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get status of orchestrator and its components
        
        Phase 2A.5: Now includes 99.co scraper status
        
        Returns:
            Dict with status information
        """
        return {
            'live_scraping_enabled': self.enable_live_scraping,
            'scrapers': [
                {
                    'name': 'Lamudi',
                    'source_id': self.lamudi.get_source_name(),
                    'cache_dir': str(self.lamudi.cache_dir),
                    'cache_expiry_hours': self.lamudi.cache_expiry_hours,
                    'priority': 1
                },
                {
                    'name': 'Rumah.com',
                    'source_id': self.rumah_com.get_source_name(),
                    'cache_dir': str(self.rumah_com.cache_dir),
                    'cache_expiry_hours': self.rumah_com.cache_expiry_hours,
                    'priority': 2
                },
                {
                    'name': '99.co',
                    'source_id': self.ninety_nine.get_source_name(),
                    'cache_dir': str(self.ninety_nine.cache_dir),
                    'cache_expiry_hours': self.ninety_nine.cache_expiry_hours,
                    'priority': 3
                }
            ],
            'benchmark_regions': list(self.regional_benchmarks.keys()),
            'total_sources': 3  # Phase 2A.5: Now 3 live sources
        }


# Standalone test
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    orchestrator = LandPriceOrchestrator(
        cache_expiry_hours=24,
        enable_live_scraping=True
    )
    
    # Test region
    test_region = "Sleman Yogyakarta"
    
    print(f"\n{'='*70}")
    print(f"TESTING LAND PRICE ORCHESTRATOR")
    print(f"{'='*70}")
    print(f"Region: {test_region}\n")
    
    # Get status
    status = orchestrator.get_orchestrator_status()
    print(f"Orchestrator Status:")
    print(f"  Live Scraping: {'Enabled' if status['live_scraping_enabled'] else 'Disabled'}")
    print(f"  Scrapers: {', '.join([s['name'] for s in status['scrapers']])}")
    print(f"  Benchmark Regions: {', '.join(status['benchmark_regions'])}\n")
    
    # Get price data
    print(f"Fetching land price data...\n")
    result = orchestrator.get_land_price(test_region, max_listings=10)
    
    print(f"\n{'='*70}")
    print(f"RESULT")
    print(f"{'='*70}")
    print(f"Success: {result['success']}")
    print(f"Data Source: {result['data_source']}")
    print(f"Average Price: Rp {result['average_price_per_m2']:,.0f}/m²")
    print(f"Median Price: Rp {result['median_price_per_m2']:,.0f}/m²")
    print(f"Listing Count: {result['listing_count']}")
    print(f"Data Confidence: {result.get('data_confidence', 0):.0%}")
    
    if 'cache_age_hours' in result:
        print(f"Cache Age: {result['cache_age_hours']:.1f} hours")
    
    if 'benchmark_region' in result:
        print(f"Benchmark Region: {result['benchmark_region']}")
    
    if result.get('listings'):
        print(f"\nSample Listings (top 3):")
        for i, listing in enumerate(result['listings'][:3], 1):
            print(f"\n  {i}. {listing['location']}")
            print(f"     Price: Rp {listing['price_per_m2']:,.0f}/m²")
            print(f"     Size: {listing['size_m2']:,.0f} m²")
