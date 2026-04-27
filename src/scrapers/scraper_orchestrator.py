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
        
        # Static regional benchmarks (fallback when scrapers fail).
        # historical_appreciation is in PERCENT (e.g. 15 = 15%/yr).
        # current_avg refreshed 2026-04-25 from live Lamudi medians (only
        # well-mapped regions, excluding outlier-clamped extracts). Untouched
        # benchmarks (yogyakarta, palembang, nusantara, denpasar) had too few
        # legitimate contributors or geographic mis-routing — flagged for a
        # follow-up pass once the region→benchmark mapping is more granular.
        self.regional_benchmarks = {
            'jakarta': {
                'current_avg': 8_564_000,  # was 8,500,000 — refreshed +0.8%
                'historical_appreciation': 15.0,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark',
            },
            'bali': {
                'current_avg': 7_494_000,  # was 12,000,000 — refreshed -37.5% (real Bali medians)
                'historical_appreciation': 20.0,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark',
            },
            'yogyakarta': {
                # NOT REFRESHED 2026-04-25: contributors include cross-province
                # regions (anyer_carita = Banten) that fall through default
                # routing. Refresh once region mapping has a 'banten' bucket.
                'current_avg': 4_500_000,
                'historical_appreciation': 12.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'surabaya': {
                'current_avg': 5_165_000,  # was 6,500,000 — refreshed -20.5%
                'historical_appreciation': 14.0,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark',
            },
            'bandung': {
                'current_avg': 5_845_000,  # was 5,000,000 — refreshed +16.9%
                'historical_appreciation': 13.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'semarang': {
                'current_avg': 4_411_000,  # was 3,500,000 — refreshed +26.0%
                'historical_appreciation': 11.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'medan': {
                'current_avg': 3_540_000,  # was 4,000,000 — refreshed -11.5%
                'historical_appreciation': 10.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'palembang': {
                # NOT REFRESHED: 0 contributors with live data this run
                'current_avg': 3_000_000,
                'historical_appreciation': 9.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'lampung': {
                'current_avg': 1_867_000,  # was 2,500,000 — refreshed -25.3%
                'historical_appreciation': 8.0,
                'market_liquidity': 'low',
                'data_source': 'static_benchmark',
            },
            'batam': {
                'current_avg': 5_175_000,  # was 5,500,000 — refreshed -5.9% (n=1)
                'historical_appreciation': 12.0,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark',
            },
            'makassar': {
                'current_avg': 5_815_000,  # was 4,200,000 — refreshed +38.4%
                'historical_appreciation': 11.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'balikpapan': {
                'current_avg': 3_705_000,  # was 3,800,000 — refreshed -2.5% (basically right)
                'historical_appreciation': 10.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'nusantara': {
                # NOT REFRESHED: only 1 contributor (nusantara_capital_core),
                # too low a sample to overwrite. Land prices in IKN are still
                # speculative and noisy.
                'current_avg': 2_000_000,
                'historical_appreciation': 25.0,
                'market_liquidity': 'low',
                'data_source': 'static_benchmark',
            },
            'lombok': {
                'current_avg': 2_815_000,  # was 5,000,000 — refreshed -43.7%
                'historical_appreciation': 15.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
            'denpasar': {
                # 2026-04-25: denpasar_* now routes here (was bali). Keep the
                # premium benchmark — Bali capital land trades ~2× rest of island.
                # Refresh on next run when denpasar_north_expansion contributes.
                'current_avg': 15_000_000,
                'historical_appreciation': 18.0,
                'market_liquidity': 'high',
                'data_source': 'static_benchmark',
            },
            'banten': {
                # Added 2026-04-25 to stop anyer/cilegon/serang/merak from
                # polluting the yogyakarta default bucket. Banten coastal +
                # industrial corridor — anchor at Cilegon/Merak port pricing.
                # Will refresh from real medians on the next full run.
                'current_avg': 4_000_000,
                'historical_appreciation': 11.0,
                'market_liquidity': 'moderate',
                'data_source': 'static_benchmark',
            },
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
        # Token-based matching: split on '_' so 'bali' won't substring-match
        # 'balikpapan' (which routed every Kalimantan region to the Bali
        # benchmark and silently inflated the apparent Bali land prices when
        # we tried to refresh benchmarks from real medians).
        tokens = set(region_lower.split('_'))

        # Province / island-level matches — checked FIRST (more specific than
        # the bare-substring fallback) so balikpapan_* lands in 'balikpapan'
        # not 'bali'. Order matters when keywords overlap: more-specific
        # benchmarks (denpasar, banten, jakarta) must come BEFORE the broader
        # ones (bali, surabaya).
        mapping = {
            # Banten = Indonesian province west of Jakarta (Anyer, Cilegon,
            # Serang, Merak, Tangerang). Previously polluted yogyakarta default.
            'banten': ['anyer', 'carita', 'cilegon', 'serang', 'merak'],
            # Jakarta keeps tangerang/bekasi/cikarang/bogor — those are part of
            # JABODETABEK metropolitan area, not Banten proper.
            'jakarta': ['jakarta', 'tangerang', 'bekasi', 'cikarang', 'bogor', 'karawang'],
            # Denpasar (Bali capital) priced ~2× the rest of Bali — keep
            # separate. Listed BEFORE bali so denpasar_* lands here.
            'denpasar': ['denpasar'],
            'yogyakarta': ['yogyakarta', 'yogya', 'sleman', 'bantul', 'kulon', 'magelang', 'purwokerto'],
            'surabaya': ['surabaya', 'sidoarjo', 'gresik', 'malang', 'probolinggo', 'jember', 'banyuwangi'],
            'bandung': ['bandung', 'cirebon', 'subang'],
            'semarang': ['semarang', 'solo', 'tegal', 'batang'],
            'bali': ['bali', 'canggu', 'seminyak', 'sanur', 'ubud', 'tabanan', 'nusa', 'bukit'],
            'medan': ['medan', 'kuala', 'belawan', 'toba'],
            'palembang': ['palembang', 'jakabaring', 'boom'],
            'lampung': ['lampung', 'bakauheni'],
            'batam': ['batam'],
            'makassar': ['makassar', 'manado', 'bitung'],
            'balikpapan': ['balikpapan', 'samarinda', 'banjarmasin', 'pontianak'],
            'nusantara': ['nusantara', 'ikn'],
            'lombok': ['lombok', 'mataram', 'mandalika', 'senggigi'],
        }

        for bench_key, keywords in mapping.items():
            if bench_key not in self.regional_benchmarks:
                continue
            for kw in keywords:
                if kw in tokens:
                    return self.regional_benchmarks[bench_key]

        # Broader island-level fallback
        if tokens & {'aceh', 'padang', 'pekanbaru'}:
            return self.regional_benchmarks['medan']
        if tokens & {'jayapura', 'ambon', 'papua', 'maluku'}:
            return self.regional_benchmarks['makassar']
        if tokens & {'labuan', 'kupang', 'flores'}:
            # NTT/Flores — small island tourism, closest analogue is Lombok
            return self.regional_benchmarks['lombok']

        # Default to Yogyakarta (mid-tier market)
        return self.regional_benchmarks['yogyakarta']
    
    def _get_benchmark_region_name(self, region_name: str) -> str:
        """Get the display name of the benchmark region used.

        Mirrors the lookup logic in _find_nearest_benchmark so the displayed
        name matches the benchmark actually applied (token-based, not substring).
        """
        # Reverse-map: find the benchmark dict and return its key
        target = self._find_nearest_benchmark(region_name)
        for key, value in self.regional_benchmarks.items():
            if value is target:
                return key.capitalize()
        return 'Yogyakarta'  # Should never hit; safety net
    
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
            # Try to calculate trend from price history archive (JSONL files)
            from datetime import datetime, timedelta
            import json as _json

            slug = region_name.lower().replace(' ', '_')
            for scraper in [self.lamudi, self.rumah_com, self.ninety_nine]:
                history_file = scraper.cache_dir / 'price_history' / f"{slug}.jsonl"
                if not history_file.exists():
                    # Also try with source prefix stripped
                    continue

                try:
                    records = []
                    with open(history_file, 'r') as f:
                        for line in f:
                            try:
                                records.append(_json.loads(line))
                            except _json.JSONDecodeError:
                                pass

                    if len(records) >= 2:
                        # Find a record ~30 days ago (accept 14-60 day window)
                        today = datetime.now().date()
                        best_rec = None
                        best_delta = 999

                        for rec in records:
                            try:
                                rec_date = datetime.strptime(rec['date'], '%Y-%m-%d').date()
                                age_days = (today - rec_date).days
                                # Prefer ~30 days, accept 14-60
                                if 14 <= age_days <= 60:
                                    delta = abs(age_days - 30)
                                    if delta < best_delta:
                                        best_delta = delta
                                        best_rec = rec
                            except (KeyError, ValueError):
                                pass

                        if best_rec and best_rec.get('avg_price_m2', 0) > 0:
                            historical_price = best_rec['avg_price_m2']
                            age_days = (today - datetime.strptime(best_rec['date'], '%Y-%m-%d').date()).days

                            trend_pct = ((current_price - historical_price) / historical_price) * 100
                            # Cap the annualization multiplier at 12.2x (= 365/30) so short
                            # histories don't over-extrapolate noise. Without this, a 14-day
                            # history with 1% trend produced annualized 26%/yr → "booming",
                            # and 5-day histories went 73× → wild "declining" classifications
                            # for any tiny price wiggle. Real-world land prices don't move
                            # fast enough for sub-30-day extrapolation to be meaningful.
                            annualization_factor = 365.0 / max(age_days, 30)
                            annualized_trend = trend_pct * annualization_factor
                            market_heat = self._classify_market_heat(annualized_trend)

                            logger.info(
                                f"   📊 Price Trend ({age_days}d history): {trend_pct:+.1f}% "
                                f"(annualized: {annualized_trend:+.1f}%, factor {annualization_factor:.1f}x)"
                            )
                            return trend_pct, market_heat

                except Exception as e:
                    logger.debug(f"   Error reading price history: {e}")
                    continue

            # No suitable historical data found - use benchmark appreciation rate
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
    
    # If extracted average exceeds the regional benchmark by this multiplier we
    # treat it as scraper noise (typical causes: commercial buildings priced as
    # land, "starting from" prices, unit confusion). Indonesian land tops out
    # around Rp 80-100M/m² in the most expensive Jakarta CBD plots — anything
    # 5× the regional benchmark is almost certainly garbage.
    _PRICE_OUTLIER_MULTIPLIER = 5.0

    def _sanity_check_price(
        self,
        region_name: Optional[str],
        average: float,
        median: float,
        listing_count: int,
        source: str,
    ) -> tuple[float, float, bool, str]:
        """Compare extracted prices against the regional benchmark.

        Returns (avg, med, was_clamped, reason). When the average is implausibly
        high we return the median (more outlier-resistant), or fall through to
        the benchmark if the median is also wild.
        """
        if not region_name:
            return average, median, False, ""
        benchmark = self._find_nearest_benchmark(region_name).get('current_avg', 0)
        if benchmark <= 0:
            return average, median, False, ""
        threshold = benchmark * self._PRICE_OUTLIER_MULTIPLIER
        if average <= threshold:
            return average, median, False, ""
        # Average is implausible. Try median first.
        if 0 < median <= threshold:
            reason = (
                f"avg Rp {average:,.0f}/m² is {average / benchmark:.1f}× benchmark "
                f"(Rp {benchmark:,.0f}/m²) for {region_name} — using median Rp {median:,.0f}/m² "
                f"({listing_count} listings, source={source})"
            )
            logger.warning(f"⚠️ Price outlier clamped: {reason}")
            return median, median, True, reason
        # Both average and median are wild — fall back to the benchmark.
        reason = (
            f"avg Rp {average:,.0f}/m² AND median Rp {median:,.0f}/m² both exceed "
            f"{self._PRICE_OUTLIER_MULTIPLIER}× benchmark Rp {benchmark:,.0f}/m² for "
            f"{region_name} — clamping to benchmark ({listing_count} listings, source={source})"
        )
        logger.error(f"🚨 Price outlier — using benchmark: {reason}")
        return float(benchmark), float(benchmark), True, reason

    def _convert_scrape_result_to_dict(self, result: ScrapeResult, region_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert ScrapeResult to dict for consistency

        Args:
            result: ScrapeResult from scraper
            region_name: Optional region name for trend calculation

        Returns:
            Dict with price data including trend calculations
        """
        # Sanity check: clamp implausibly high prices (e.g. Rp 165M/m² for
        # Bitung — almost certainly commercial buildings). A bogus high price
        # silently kills any BUY signal for that region.
        avg, med, clamped, clamp_reason = self._sanity_check_price(
            region_name=region_name,
            average=result.average_price_per_m2,
            median=result.median_price_per_m2,
            listing_count=result.listing_count,
            source=result.source,
        )

        # Calculate price trend if we have historical cache data
        price_trend_30d = 0.0
        market_heat = 'neutral'

        if region_name:
            price_trend_30d, market_heat = self._calculate_price_trend(
                region_name,
                avg,
            )

        # Confidence cascade:
        # - clamped (avg >5x benchmark): 0.55 (data extraction is suspect)
        # - low listing count (<10): 0.65 (median is unstable with N<10)
        # - normal: 0.85
        # Audit 2026-04-27: 17 of 65 regions show price-history listing_count
        # bouncing between 5 and 20 (Lamudi pagination instability). When the
        # current scrape returns <10 listings the price aggregation is
        # noticeably more volatile run-to-run. Surfacing the low-sample
        # signal lets downstream confidence cap kick in.
        if clamped:
            data_conf = 0.55
        elif result.listing_count < 10:
            data_conf = 0.65
        else:
            data_conf = 0.85

        result_dict = {
            'success': result.success,
            'average_price_per_m2': avg,
            'median_price_per_m2': med,
            'listing_count': result.listing_count,
            'data_source': result.source if not clamped else f'{result.source}_clamped',
            'scraped_at': result.scraped_at.isoformat(),
            'data_confidence': data_conf,
            'price_trend_30d': price_trend_30d,
            'market_heat': market_heat,
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
        if clamped:
            result_dict['price_clamp_reason'] = clamp_reason
        return result_dict
    
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
