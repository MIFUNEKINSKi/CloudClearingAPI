"""
Automated Weekly Monitoring System for CloudClearingAPI

This module implements automated weekly satellite monitoring across multiple regions,
with alerting, historical tracking, and comprehensive reporting.
"""

import asyncio
import logging
import os
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from dataclasses import asdict, is_dataclass

import ee  # type: ignore[import]

from .change_detector import ChangeDetector
from .config import get_config
from .satellite_image_saver import SatelliteImageSaver
# from .database import DatabaseManager  # Disabled due to SQLAlchemy compatibility issues
from .speculative_scorer import SpeculativeScorer
from .corrected_scoring import CorrectedInvestmentScorer  # ✅ NEW: Proper satellite-centric scoring
from ..scrapers.scraper_orchestrator import LandPriceOrchestrator  # ✅ v2.8.2: For market data scraping

# Import financial metrics engine
try:
    from .financial_metrics import FinancialMetricsEngine
    FINANCIAL_ENGINE_AVAILABLE = True
except ImportError:
    FINANCIAL_ENGINE_AVAILABLE = False

# Import SAR (Sentinel-1 radar) change detector for cloud-penetrating analysis
try:
    from .sar_change_detector import SARChangeDetector
    SAR_AVAILABLE = True
except ImportError:
    SAR_AVAILABLE = False

# Import news catalyst + scraper for development news scoring
try:
    from .news_catalyst import NewsCatalyst
    from ..scrapers.news_scraper import NewsScraper
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

# Import momentum analyzer for historical rate-of-change scoring
try:
    from .momentum_analyzer import MomentumAnalyzer
    MOMENTUM_AVAILABLE = True
except ImportError:
    MOMENTUM_AVAILABLE = False

# Try to import RegionManager with fallback
try:
    from ..regions import RegionManager
except ImportError:
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    from regions import RegionManager

logger = logging.getLogger(__name__)

# Try to import strategic corridor analysis
try:
    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    from demo_strategic_analysis import create_strategic_corridors, calculate_comprehensive_score
    STRATEGIC_CORRIDORS_AVAILABLE = True
    create_strategic_corridors_func = create_strategic_corridors
    calculate_comprehensive_score_func = calculate_comprehensive_score
except ImportError:
    STRATEGIC_CORRIDORS_AVAILABLE = False
    create_strategic_corridors_func = None
    calculate_comprehensive_score_func = None
    logger.warning("Strategic corridor analysis not available - using regional analysis only")
    logger.warning("Strategic corridor analysis not available - using regional analysis only")

class AutomatedMonitor:
    """
    Automated monitoring system that runs weekly analysis across all regions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the automated monitor"""
        self.config = get_config()
        self.detector = ChangeDetector()
        self.region_manager = RegionManager()
        self.speculative_scorer = SpeculativeScorer()  # Legacy fallback
        # ✅ CORRECTED SCORER: Satellite-centric with infrastructure/market multipliers
        from .price_intelligence import PriceIntelligenceEngine
        from .infrastructure_analyzer import InfrastructureAnalyzer
        
        # v2.6-beta: Pass financial_engine for RVI-aware market multiplier
        # ✅ v2.8.2 FIX: Use LandPriceOrchestrator instead of PriceIntelligenceEngine
        # LandPriceOrchestrator has get_land_price() method used by corrected scorer
        price_orchestrator = LandPriceOrchestrator(
            cache_expiry_hours=24,
            enable_live_scraping=True,
            config=None  # Scrapers use default config if None
        )
        
        self.corrected_scorer = CorrectedInvestmentScorer(
            price_orchestrator,  # ✅ Fixed: was PriceIntelligenceEngine()
            InfrastructureAnalyzer(),
            financial_engine=None  # Will be set below if available
        )
        self.image_saver = SatelliteImageSaver()  # 📸 Image saving for PDF integration

        # Initialize SAR (Sentinel-1 radar) change detector
        self.sar_detector = None
        if SAR_AVAILABLE:
            try:
                self.sar_detector = SARChangeDetector()
                logger.info("✅ SAR Change Detector initialized (Sentinel-1 radar fusion enabled)")
            except Exception as e:
                logger.warning(f"⚠️ SAR Change Detector unavailable: {e}")

        # Initialize news catalyst + scraper
        self.news_scraper = None
        self.news_catalyst = None
        self._cached_news_articles = None  # Cache scraped articles across regions
        if NEWS_AVAILABLE:
            try:
                self.news_scraper = NewsScraper()
                self.news_catalyst = NewsCatalyst()
                logger.info("✅ News Catalyst + Scraper initialized")
            except Exception as e:
                logger.warning(f"⚠️ News modules unavailable: {e}")

        # Initialize momentum analyzer (historical rate-of-change)
        self.momentum_analyzer = None
        if MOMENTUM_AVAILABLE:
            try:
                self.momentum_analyzer = MomentumAnalyzer()
                logger.info("✅ Momentum Analyzer initialized (historical acceleration scoring)")
            except Exception as e:
                logger.warning(f"⚠️ Momentum Analyzer unavailable: {e}")

        # Initialize financial metrics engine (v2.7 CCAPI-27.0: with budget config)
        self.financial_engine = None
        if FINANCIAL_ENGINE_AVAILABLE:
            try:
                self.financial_engine = FinancialMetricsEngine(
                    enable_web_scraping=True,
                    cache_expiry_hours=24,
                    config=self.config  # ✅ v2.7 CCAPI-27.0: Pass config for budget-driven sizing
                )
                # v2.6-beta: Pass financial engine to scorer for RVI-aware multiplier
                self.corrected_scorer.financial_engine = self.financial_engine
                logger.info("✅ Financial Metrics Engine initialized with web scraping enabled")
                logger.info("✅ RVI-aware market multiplier enabled in corrected scorer")
                logger.info(f"✅ Budget-driven sizing: Target ~${self.financial_engine.target_budget_idr/15000:,.0f} USD")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Financial Metrics Engine: {e}")
        else:
            logger.warning("⚠️ Financial Metrics Engine not available - install dependencies: pip install beautifulsoup4 lxml")
        
        self.db_manager = None
        
        # Initialize strategic corridors if available
        self.strategic_corridors = []
        self.strategic_analysis_enabled = False
        if STRATEGIC_CORRIDORS_AVAILABLE and create_strategic_corridors_func:
            try:
                self.strategic_corridors = create_strategic_corridors_func()
                self.strategic_analysis_enabled = True
                logger.info(f"✅ Strategic corridor analysis enabled: {len(self.strategic_corridors)} corridors loaded")
            except Exception as e:
                logger.warning(f"Failed to load strategic corridors: {e}")
        
        # Database persistence is intentionally disabled — outputs are flat JSON
        # in output/ and history/. Logged at DEBUG so it doesn't crowd weekly logs.
        self.db_manager = None
        logger.debug("Database persistence disabled (intentional — outputs are JSON)")
        
        # Monitoring schedule - Original Yogyakarta regions
        self.yogyakarta_regions = [
            "yogyakarta_urban",
            "yogyakarta_periurban", 
            "sleman_north",
            "bantul_south",
            "kulonprogo_west",
            "gunungkidul_east",
            "magelang_corridor",
            "solo_expansion",
            "semarang_industrial",
            "surakarta_suburbs"
        ]
        
        # Strategic corridor regions (if available)
        self.strategic_corridor_regions = []
        if self.strategic_analysis_enabled:
            for corridor in self.strategic_corridors:
                self.strategic_corridor_regions.append({
                    'name': corridor.name.lower().replace(' ', '_').replace('-', '_'),
                    'corridor': corridor,
                    'analysis_type': 'strategic_corridor'
                })
        
        # Combined monitoring regions
        self.monitoring_regions = self.yogyakarta_regions.copy()
        if self.strategic_analysis_enabled:
            logger.info(f"MARKET Enhanced monitoring: {len(self.yogyakarta_regions)} Yogyakarta regions + {len(self.strategic_corridor_regions)} strategic corridors")
        
        # Alert thresholds
        self.alert_config = {
            'critical_change_count': 50,  # > 50 changes triggers critical alert
            'major_change_count': 20,     # > 20 changes triggers major alert
            'critical_area_m2': 100000,   # > 10 hectares triggers critical alert
            'major_area_m2': 50000,       # > 5 hectares triggers major alert
            'development_hotspot_threshold': 0.8,  # 80% development changes
            'vegetation_loss_threshold': 0.6       # 60% vegetation loss
        }
    
    def _get_optimal_date_range(self, attempt=0) -> tuple:
        """
        Get optimal date range for satellite analysis - tries recent data first, 
        progressively falls back through historical periods (up to 10 attempts)
        """
        now = datetime.now()
        
        # Dynamic candidate periods - goes progressively back in time
        # Each attempt is 1 week further back, with 10 attempt maximum
        max_attempts = 10
        
        if attempt >= max_attempts:
            logger.error(f"⚠️ Maximum fallback attempts ({max_attempts}) reached")
            # Return oldest attempt period
            weeks_back = max_attempts
            return (now - timedelta(days=weeks_back*7+7), now - timedelta(days=weeks_back*7))
        
        # Calculate date range based on attempt number
        # Attempt 0: 1 week ago, Attempt 1: 2 weeks ago, etc.
        weeks_back = attempt + 1
        start_date = now - timedelta(days=weeks_back*7+7)
        end_date = now - timedelta(days=weeks_back*7)
        
        # Generate dynamic period name
        if weeks_back == 1:
            period_name = "recent data (1 week ago)"
        else:
            period_name = f"{weeks_back} weeks ago"
        
        if attempt == 0:
            logger.info("🔍 Searching for optimal satellite data availability...")
            logger.info(f"📅 Trying {period_name}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"✅ Using {period_name} - will fallback if analysis fails")
        else:
            logger.warning(f"📅 Falling back to {period_name}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
        return end_date, start_date

    async def run_weekly_monitoring(self) -> Dict[str, Any]:
        """
        Run automated weekly monitoring across all regions.
        Each region independently searches for best available satellite data.
        
        Returns:
            Dict containing monitoring results and alerts
        """
        logger.info("🤖 Starting automated weekly monitoring")

        # Reset cached news articles for this run
        self._cached_news_articles = None

        # Calculate initial time periods (each region will handle its own fallback)
        end_date, start_date = self._get_optimal_date_range(0)
        
        logger.info(f"📅 Using satellite data period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        week_a_start = start_date.strftime('%Y-%m-%d')
        week_b_start = end_date.strftime('%Y-%m-%d')
        
        monitoring_results = {
            'timestamp': end_date.isoformat(),
            'period': f"{week_a_start} to {week_b_start}",
            'regions_analyzed': [],
            'total_changes': 0,
            'total_area_m2': 0,
            'alerts': [],
            'summary': {},
            'errors': []
        }
        
        # Track failures to trigger fallback
        failure_count = 0
        total_regions = len(self.yogyakarta_regions)
        
        # Analyze Yogyakarta regions (original functionality)
        for region_name in self.yogyakarta_regions:
            try:
                logger.info(f"🔍 Analyzing Yogyakarta region: {region_name}")
                result = await self._analyze_region(
                    region_name, 
                    week_a_start, 
                    week_b_start
                )
                
                if result:
                    result['analysis_type'] = 'yogyakarta_region'
                    monitoring_results['regions_analyzed'].append(result)
                    monitoring_results['total_changes'] += result['change_count']
                    monitoring_results['total_area_m2'] += result['total_area_m2']
                    
                    # Check for alerts
                    alerts = self._check_alerts(region_name, result)
                    monitoring_results['alerts'].extend(alerts)
                    
            except Exception as e:
                error_msg = str(e)
                failure_count += 1
                
                # Check if this is a satellite data error
                if "SATELLITE_DATA_ERROR" in error_msg:
                    logger.warning(f"🛰️ Satellite data unavailable for {region_name}")
                    monitoring_results['errors'].append(f"Satellite data unavailable for {region_name}")
                else:
                    logger.error(f"Failed to analyze Yogyakarta region {region_name}: {error_msg}")
                    monitoring_results['errors'].append(f"Failed to analyze Yogyakarta region {region_name}: {error_msg}")
        
        # Log success rate (each region now handles its own fallback)
        success_count = len(monitoring_results['regions_analyzed'])
        logger.info(f"� Successfully analyzed {success_count}/{total_regions} regions ({success_count/total_regions*100:.0f}% success rate)")
        
        # Analyze strategic corridors (enhanced functionality)
        if self.strategic_analysis_enabled:
            logger.info(f"INDONESIA Analyzing {len(self.strategic_corridor_regions)} strategic corridors")
            for corridor_info in self.strategic_corridor_regions:
                try:
                    corridor_name = corridor_info['name']
                    corridor = corridor_info['corridor']
                    logger.info(f"TARGET Analyzing strategic corridor: {corridor.name}")
                    
                    result = await self._analyze_strategic_corridor(
                        corridor,
                        week_a_start,
                        week_b_start
                    )
                    
                    if result:
                        result['analysis_type'] = 'strategic_corridor'
                        monitoring_results['regions_analyzed'].append(result)
                        monitoring_results['total_changes'] += result['change_count']
                        monitoring_results['total_area_m2'] += result['total_area_m2']
                        
                        # Check for strategic corridor alerts
                        alerts = self._check_strategic_alerts(corridor, result)
                        monitoring_results['alerts'].extend(alerts)
                        
                except Exception as e:
                    corridor_name = corridor_info.get('name', 'unknown')
                    error_msg = f"Failed to analyze strategic corridor {corridor_name}: {str(e)}"
                    logger.error(error_msg)
                    monitoring_results['errors'].append(error_msg)
        
        # Original regions for backward compatibility  
        for region_name in [r for r in self.monitoring_regions if r not in self.yogyakarta_regions]:
            try:
                logger.info(f"🔍 Analyzing region: {region_name}")
                result = await self._analyze_region(
                    region_name, 
                    week_a_start, 
                    week_b_start
                )
                
                if result:
                    result['analysis_type'] = 'legacy_region'
                    monitoring_results['regions_analyzed'].append(result)
                    monitoring_results['total_changes'] += result['change_count']
                    monitoring_results['total_area_m2'] += result['total_area_m2']
                    
                    # Check for alerts
                    alerts = self._check_alerts(region_name, result)
                    monitoring_results['alerts'].extend(alerts)
                    
            except Exception as e:
                error_msg = f"Failed to analyze {region_name}: {str(e)}"
                logger.error(error_msg)
                monitoring_results['errors'].append(error_msg)
        
        # Generate speculative investment scores
        monitoring_results['investment_analysis'] = self._generate_investment_analysis(monitoring_results)
        
        # Generate summary
        monitoring_results['summary'] = self._generate_summary(monitoring_results)
        
        # Save results
        await self._save_monitoring_results(monitoring_results)
        
        # Send alerts if necessary
        if monitoring_results['alerts']:
            await self._send_alerts(monitoring_results)
        
        logger.info(f"✅ Weekly monitoring completed: {monitoring_results['total_changes']} changes detected")
        return monitoring_results

    async def _analyze_region(self, region_name: str, week_a: str, week_b: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a specific region for changes with automatic per-region fallback.
        Each region independently searches through date ranges until it finds good data.
        """
        # Get region boundaries
        region_bbox = self.region_manager.get_region_bbox(region_name)
        if not region_bbox:
            logger.warning(f"No bbox found for region: {region_name}")
            return None
        
        # Create Earth Engine geometry
        bbox = {
            'type': 'Polygon',
            'coordinates': [[
                [region_bbox['west'], region_bbox['south']],
                [region_bbox['east'], region_bbox['south']],
                [region_bbox['east'], region_bbox['north']],
                [region_bbox['west'], region_bbox['north']],
                [region_bbox['west'], region_bbox['south']]
            ]]
        }
        
        # Define date ranges to try for this specific region (in order of preference)
        # Reduced from 20 to 5 attempts since SAR fallback handles cloud-covered periods
        # (Saves ~60s per region when optical is unavailable during rainy season)
        now = datetime.now()
        max_attempts = 5
        date_attempts = []

        for attempt_num in range(max_attempts):
            weeks_back = attempt_num + 1
            start_date = now - timedelta(days=weeks_back*7+7)
            end_date = now - timedelta(days=weeks_back*7)

            if weeks_back == 1:
                description = "recent (1 week ago)"
            else:
                description = f"{weeks_back} weeks ago"

            date_attempts.append((start_date, end_date, description))

        # Progressive cloud-cover thresholds. We try every date range at the strict
        # default (20%) first; only if all 5 dates are empty do we relax. This keeps
        # the happy path identical to before but rescues regions where heavy cloud
        # cover (rainy season) was forcing an SAR-only fallback.
        cloud_thresholds = [None, 40.0, 60.0]  # None = use config default (20%)

        last_error = None
        for cloud_pct in cloud_thresholds:
            cloud_label = f"cloud<{cloud_pct}%" if cloud_pct is not None else "cloud<strict"
            if cloud_pct is not None:
                logger.info(
                    f"   ☁️ {region_name}: All dates failed at strict cloud threshold — "
                    f"retrying with relaxed {cloud_label}"
                )

            for attempt_num, (start_date, end_date, description) in enumerate(date_attempts):
                try:
                    week_a_str = start_date.strftime('%Y-%m-%d')
                    week_b_str = end_date.strftime('%Y-%m-%d')

                    if attempt_num > 0:
                        logger.info(f"   🔄 {region_name}: Trying fallback {description}: {week_a_str} to {week_b_str} ({cloud_label})")

                    # Run change detection (cloud_pct overrides default when relaxed)
                    results = self.detector.detect_weekly_changes(
                        week_a_start=week_a_str,
                        week_b_start=week_b_str,
                        bbox=bbox,
                        export_results=True,
                        cloud_pct=cloud_pct,
                    )

                    # Check if we got valid results (not empty composites or errors)
                    # Check for error in change_types dict or if change_count is 0 with error in satellite_images
                    has_error = (
                        'error' in results.get('change_types', {}) or
                        (results.get('change_count', 0) == 0 and
                         'error' in results.get('satellite_images', {}))
                    )

                    if has_error:
                        # Empty composite or computation error, try next date in this cloud-tier
                        if attempt_num < len(date_attempts) - 1:
                            logger.warning(f"   ⚠️ {region_name}: {description} unavailable ({cloud_label}), will try next fallback")
                            continue
                        else:
                            # Done with this cloud tier — break out so the outer
                            # cloud_thresholds loop can try the next (more relaxed) one.
                            logger.warning(
                                f"   ⚠️ {region_name}: all {len(date_attempts)} dates failed at {cloud_label}; "
                                "advancing to next cloud-cover tier"
                            )
                            break

                    # SUCCESS PATH — we have good data. Enhance and return.
                    satellite_images = results.get('satellite_images', {})
                    saved_images = {}

                    # 📸 SAVE SATELLITE IMAGES for PDF integration
                    if satellite_images and 'error' not in satellite_images:
                        try:
                            saved_images = self.image_saver.save_satellite_images(
                                satellite_images, region_name, week_a_str, week_b_str
                            )
                            logger.info(f"📸 Saved {len([p for p in saved_images.values() if p])} satellite images for {region_name}")
                        except Exception as e:
                            logger.warning(f"Failed to save satellite images for {region_name}: {e}")

                    region_result = {
                        'region_name': region_name,
                        'bbox': region_bbox,
                        'change_count': results['change_count'],
                        'total_area_m2': results['total_area'],
                        'change_types': results['change_types'],
                        'week_a': results['week_a'],
                        'week_b': results['week_b'],
                        'analysis_timestamp': datetime.now().isoformat(),
                        'satellite_images': satellite_images,  # Original URLs
                        'saved_images': saved_images,  # Local file paths for PDF integration
                        'date_range_used': description,  # Track which fallback was used
                        'cloud_threshold_used': cloud_pct if cloud_pct is not None else self.detector.config.max_cloud_cover,
                    }

                    # SAR (Sentinel-1 radar) change detection — complements optical
                    if self.sar_detector:
                        try:
                            sar_result = self.sar_detector.detect_sar_changes(
                                bbox=region_bbox,
                                region_name=region_name,
                                period_a_start=start_date.strftime('%Y-%m-%d'),
                                period_a_end=end_date.strftime('%Y-%m-%d'),
                                period_b_start=end_date.strftime('%Y-%m-%d'),
                                period_b_end=datetime.now().strftime('%Y-%m-%d')
                            )
                            region_result['sar_result'] = sar_result
                            if sar_result.success:
                                logger.info(f"   🛰️ SAR: {sar_result.sar_change_pixels:,} radar changes detected for {region_name}")
                        except Exception as e:
                            logger.warning(f"   ⚠️ SAR detection failed for {region_name}: {e}")
                            region_result['sar_result'] = None

                    if attempt_num > 0 or cloud_pct is not None:
                        logger.info(f"   ✅ {region_name}: Successfully analyzed using {description} ({cloud_label})")

                    return region_result

                except Exception as e:
                    error_msg = str(e)
                    last_error = error_msg

                    # Empty-composite / no-bands errors mean this specific date+cloud
                    # combination failed; advance to the next date in this cloud tier.
                    # Other errors are real bugs — bail.
                    if "no bands" in error_msg.lower() or "empty composite" in error_msg.lower():
                        if attempt_num < len(date_attempts) - 1:
                            logger.warning(f"   ⚠️ {region_name}: {description} unavailable ({cloud_label}), will try next fallback")
                            continue
                        else:
                            # End of this cloud tier — break to let the outer loop relax the threshold
                            break
                    else:
                        logger.error(f"Region analysis failed for {region_name}: {e}")
                        return None

        # All cloud thresholds × all date ranges exhausted — fall back to SAR-only.
        logger.warning(
            f"   ⚠️ {region_name}: All {len(date_attempts)} optical date ranges failed across "
            f"cloud tiers {[t for t in cloud_thresholds]} — attempting SAR-only fallback"
        )
        sar_only_result = self._attempt_sar_only_fallback(region_name, region_bbox)
        if sar_only_result is not None:
            return sar_only_result
        logger.error(f"   ❌ {region_name}: All optical date+cloud combinations AND SAR fallback failed! Last error: {last_error}")
        return None

    def _attempt_sar_only_fallback(self, region_name: str, region_bbox: Dict) -> Optional[Dict]:
        """
        When all optical (Sentinel-2) date ranges fail, attempt SAR-only
        analysis using Sentinel-1 radar which penetrates cloud cover.

        SAR data is available year-round regardless of weather, so this
        should succeed even when optical is completely unavailable.

        Returns a region_result dict compatible with the optical path,
        or None if SAR also fails.
        """
        if not self.sar_detector:
            logger.warning(f"   ⚠️ {region_name}: SAR detector not available, cannot fallback")
            return None

        logger.info(f"   🛰️ {region_name}: Attempting SAR-only analysis (Sentinel-1 radar)...")

        # Try multiple date ranges for SAR too (though SAR is much more available)
        from datetime import timedelta
        now = datetime.now()
        sar_attempts = [
            (now - timedelta(days=14), now - timedelta(days=7), now),        # 1-2 weeks ago
            (now - timedelta(days=28), now - timedelta(days=14), now),       # 2-4 weeks ago
            (now - timedelta(days=60), now - timedelta(days=30), now),       # 1-2 months ago
        ]

        for period_a_start, period_a_end, period_b_end in sar_attempts:
            try:
                sar_result = self.sar_detector.detect_sar_changes(
                    bbox=region_bbox,
                    region_name=region_name,
                    period_a_start=period_a_start.strftime('%Y-%m-%d'),
                    period_a_end=period_a_end.strftime('%Y-%m-%d'),
                    period_b_start=period_a_end.strftime('%Y-%m-%d'),
                    period_b_end=period_b_end.strftime('%Y-%m-%d')
                )

                if sar_result and sar_result.success and sar_result.sar_change_pixels > 0:
                    sar_data_age_days = max(0, (datetime.now() - period_b_end).days)
                    # Confidence penalty: SAR-only loses optical signal entirely.
                    # Stale SAR (>14 days) loses more — investor should not act on it without verification.
                    if sar_data_age_days > 14:
                        sar_confidence_penalty = 0.40  # 60% confidence cap
                    elif sar_data_age_days > 7:
                        sar_confidence_penalty = 0.25  # 75% confidence cap
                    else:
                        sar_confidence_penalty = 0.15  # 85% confidence cap (SAR-only baseline)
                    logger.warning(
                        f"   ⚠️ {region_name}: SAR-only fallback succeeded "
                        f"({sar_result.sar_change_pixels:,} radar changes, data {sar_data_age_days}d old) — "
                        f"confidence reduced by {sar_confidence_penalty:.0%} (no optical verification)"
                    )

                    # Build a region_result that mimics optical output
                    # Use SAR change pixels as the primary change count
                    region_result = {
                        'region_name': region_name,
                        'bbox': region_bbox,
                        'change_count': sar_result.sar_change_pixels,
                        'total_area_m2': sar_result.sar_change_pixels * 100,  # ~100m² per pixel at 10m resolution
                        'change_types': {
                            'construction': sar_result.construction_pixels,
                            'clearing': sar_result.clearing_pixels,
                            'sar_total': sar_result.sar_change_pixels,
                        },
                        'week_a': period_a_start.strftime('%Y-%m-%d'),
                        'week_b': period_b_end.strftime('%Y-%m-%d'),
                        'analysis_timestamp': datetime.now().isoformat(),
                        'satellite_images': {},  # No optical imagery available
                        'saved_images': {},
                        'date_range_used': f'SAR-only fallback ({period_a_start.strftime("%Y-%m-%d")} to {period_b_end.strftime("%Y-%m-%d")})',
                        'sar_result': sar_result,
                        'data_source': 'sar_only',  # Flag that this is SAR-only
                        'data_age_days': sar_data_age_days,
                        'confidence_penalty': sar_confidence_penalty,
                    }
                    return region_result

                logger.info(f"   ⚠️ {region_name}: SAR attempt "
                           f"{period_a_start.strftime('%Y-%m-%d')}-{period_b_end.strftime('%Y-%m-%d')} "
                           f"returned no changes, trying next period")

            except Exception as e:
                logger.warning(f"   ⚠️ {region_name}: SAR attempt failed: {e}")
                continue

        logger.warning(f"   ❌ {region_name}: SAR-only fallback also failed after {len(sar_attempts)} attempts")
        return None

    async def _analyze_strategic_corridor(self, corridor, week_a: str, week_b: str) -> Optional[Dict[str, Any]]:
        """Analyze a strategic corridor for changes with enhanced intelligence"""
        try:
            # Create Earth Engine geometry from corridor bbox
            west, south, east, north = corridor.bbox
            bbox = {
                'type': 'Polygon',
                'coordinates': [[
                    [west, south], [east, south],
                    [east, north], [west, north],
                    [west, south]
                ]]
            }
            
            # Run change detection using existing detector (REAL satellite data)
            results = self.detector.detect_weekly_changes(
                week_a_start=week_a,
                week_b_start=week_b,
                bbox=bbox,
                export_results=True,
                auto_find_dates=True  # Use smart date finding
            )
            
            # Calculate strategic corridor metrics
            corridor_area_km2 = corridor.area_km2()
            change_density = results['change_count'] / corridor_area_km2 if corridor_area_km2 > 0 else 0
            
            # 📸 SAVE SATELLITE IMAGES for strategic corridors
            satellite_images = results.get('satellite_images', {})
            saved_images = {}
            if satellite_images and 'error' not in satellite_images:
                try:
                    saved_images = self.image_saver.save_satellite_images(
                        satellite_images, corridor.name, week_a, week_b
                    )
                    logger.info(f"📸 Saved {len([p for p in saved_images.values() if p])} satellite images for {corridor.name}")
                except Exception as e:
                    logger.warning(f"Failed to save satellite images for {corridor.name}: {e}")
            
            # Enhanced results with strategic corridor context
            corridor_result = {
                'region_name': corridor.name,
                'corridor_info': {
                    'island': corridor.island,
                    'focus': corridor.focus,
                    'investment_tier': corridor.investment_tier,
                    'risk_level': corridor.risk_level,
                    'area_km2': corridor_area_km2,
                    'market_maturity': corridor.market_maturity,
                    'expected_roi_years': corridor.expected_roi_years,
                    'infrastructure_catalysts': corridor.infrastructure_catalysts or []
                },
                'bbox': {'west': west, 'south': south, 'east': east, 'north': north},
                'change_count': results['change_count'],
                'total_area_m2': results['total_area'],
                'change_types': results['change_types'],
                'change_density_per_km2': change_density,
                'week_a': results['week_a'],
                'week_b': results['week_b'],
                'analysis_timestamp': datetime.now().isoformat(),
                'satellite_images': satellite_images,  # Original URLs
                'saved_images': saved_images,  # Local file paths for PDF integration
                
                # Strategic analysis components
                'strategic_score': self._calculate_strategic_score(corridor, results),
                'investment_signals': self._detect_investment_signals(corridor, results),
                'infrastructure_context': {
                    'active_catalysts': len(corridor.infrastructure_catalysts or []),
                    'catalyst_details': corridor.infrastructure_catalysts or []
                }
            }
            
            return corridor_result
            
        except Exception as e:
            logger.error(f"Strategic corridor analysis failed for {corridor.name}: {e}")
            return None
    
    def _calculate_strategic_score(self, corridor, satellite_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate strategic investment score for corridor with DYNAMIC intelligence"""
        try:
            # 🚀 NEW: Try dynamic scoring first
            try:
                corridor_name = getattr(corridor, 'name', str(corridor))
                
                # Create region config for dynamic scorer
                region_config = {
                    'name': corridor_name,
                    # Try to extract coordinates from corridor
                    'center': {
                        'lat': getattr(corridor, 'lat', -7.7956),
                        'lng': getattr(corridor, 'lng', 110.3695)
                    },
                    'bbox': getattr(corridor, 'bbox', {
                        'north': -7.7, 'south': -7.9, 'east': 110.5, 'west': 110.2
                    })
                }
                
                # ✅ CORRECTED SCORING: Satellite is now the PRIMARY signal!
                coordinates = region_config['center']
                bbox = region_config['bbox']
                satellite_changes = satellite_results.get('change_count', 0)
                area_affected_m2 = satellite_results.get('total_area', 0)
                
                corrected_result = self.corrected_scorer.calculate_investment_score(
                    region_name=corridor_name,
                    satellite_changes=satellite_changes,
                    area_affected_m2=area_affected_m2,
                    region_config=region_config,
                    coordinates=coordinates,
                    bbox=bbox
                )
                
                # Satellite component score for backward compatibility
                satellite_component = self._calculate_satellite_component_score(satellite_results)
                
                # Combined score: Use corrected score as base
                base_dynamic_score = corrected_result.final_investment_score
                
                if STRATEGIC_CORRIDORS_AVAILABLE and calculate_comprehensive_score_func:
                    strategic_scores = calculate_comprehensive_score_func(corridor)
                    enhanced_score = (
                        0.50 * base_dynamic_score +
                        0.25 * satellite_component +
                        0.25 * strategic_scores['total_score']
                    )
                    
                    return {
                        'dynamic_score': base_dynamic_score,
                        'dynamic_confidence': corrected_result.confidence_level,
                        'strategic_base_score': strategic_scores['total_score'],
                        'satellite_component_score': satellite_component,
                        'enhanced_total_score': enhanced_score,
                        'score_breakdown': {
                            'corrected_scoring': corrected_result.__dict__,
                            'strategic_analysis': strategic_scores
                        },
                        'satellite_metrics': {
                            'change_count': satellite_results['change_count'],
                            'total_area_m2': satellite_results['total_area'],
                            'change_types': satellite_results.get('change_types', {})
                        },
                        'analysis_type': 'enhanced_dynamic'
                    }
                else:
                    # Dynamic + satellite only
                    enhanced_score = (
                        0.75 * base_dynamic_score +
                        0.25 * satellite_component
                    )
                    
                    return {
                        'dynamic_score': base_dynamic_score,
                        'dynamic_confidence': corrected_result.confidence_level,
                        'satellite_component_score': satellite_component,
                        'enhanced_total_score': enhanced_score,
                        'score_breakdown': {
                            'corrected_scoring': corrected_result.__dict__
                        },
                        'satellite_metrics': {
                            'change_count': satellite_results['change_count'],
                            'total_area_m2': satellite_results['total_area'],
                            'change_types': satellite_results.get('change_types', {})
                        },
                        'analysis_type': 'dynamic_only'
                    }
                    
            except Exception as dynamic_error:
                logger.warning(f"Dynamic scoring failed for {corridor}, falling back to static: {dynamic_error}")
                
                # Fallback to static strategic scoring
                if STRATEGIC_CORRIDORS_AVAILABLE and calculate_comprehensive_score_func:
                    strategic_scores = calculate_comprehensive_score_func(corridor)
                    
                    # Enhance with real satellite data
                    satellite_component = self._calculate_satellite_component_score(satellite_results)
                    
                    # Weighted final score (satellite data gets 25% weight, strategic gets 75%)
                    enhanced_score = (
                        0.75 * strategic_scores['total_score'] +
                        0.25 * satellite_component
                    )
                    
                    return {
                        'strategic_base_score': strategic_scores['total_score'],
                        'satellite_component_score': satellite_component,
                        'enhanced_total_score': enhanced_score,
                        'score_breakdown': strategic_scores,
                        'satellite_metrics': {
                            'change_count': satellite_results['change_count'],
                            'total_area_m2': satellite_results['total_area'],
                            'change_types': satellite_results.get('change_types', {})
                        },
                        'analysis_type': 'static_fallback'
                    }
                else:
                    # Final fallback: satellite data only
                    satellite_score = self._calculate_satellite_component_score(satellite_results)
                    return {
                        'enhanced_total_score': satellite_score,
                        'satellite_component_score': satellite_score,
                        'note': 'Dynamic and strategic scoring not available - satellite data only',
                        'analysis_type': 'satellite_only'
                    }
                
        except Exception as e:
            logger.warning(f"All scoring methods failed for {corridor}: {e}")
            return {'enhanced_total_score': 50, 'error': str(e), 'analysis_type': 'error_fallback'}
    
    def _calculate_satellite_component_score(self, satellite_results: Dict[str, Any]) -> float:
        """Calculate satellite component score (0-100)"""
        change_count = satellite_results.get('change_count', 0)
        change_types = satellite_results.get('change_types', {})
        
        # Base score from change activity
        activity_score = min(50, change_count * 0.5)  # Max 50 points for activity
        
        # Development bonus (infrastructure + development changes)
        dev_changes = change_types.get('development', 0) + change_types.get('infrastructure', 0)
        development_bonus = min(30, dev_changes * 2)  # Max 30 points for development
        
        # Density bonus for concentrated activity
        if change_count > 20:
            density_bonus = 20
        elif change_count > 10:
            density_bonus = 10
        else:
            density_bonus = 0
        
        total_score = activity_score + development_bonus + density_bonus
        return min(100, max(0, total_score))
    
    def _detect_investment_signals(self, corridor, satellite_results: Dict[str, Any]) -> List[str]:
        """Detect investment signals from satellite and corridor data"""
        signals = []
        
        change_count = satellite_results.get('change_count', 0)
        change_types = satellite_results.get('change_types', {})
        
        # High satellite activity signal
        if change_count > 30:
            signals.append(f"High satellite activity: {change_count} changes detected")
        
        # Development concentration signal
        dev_changes = change_types.get('development', 0)
        if dev_changes > 15:
            signals.append(f"Strong development signal: {dev_changes} development changes")
        
        # Infrastructure development signal
        infra_changes = change_types.get('infrastructure', 0)
        if infra_changes > 5:
            signals.append(f"Infrastructure development: {infra_changes} infrastructure changes")
        
        # Catalyst timing signal
        active_catalysts = len(corridor.infrastructure_catalysts or [])
        if active_catalysts > 2:
            signals.append(f"Infrastructure catalyst convergence: {active_catalysts} active catalysts")
        
        # Investment tier signal
        if corridor.investment_tier == 'tier1' and change_count > 20:
            signals.append("Tier-1 corridor with high activity - prime acquisition opportunity")
        
        # Market maturity signal
        if corridor.market_maturity == 'emerging' and change_count > 15:
            signals.append("Emerging market with development momentum - early entry opportunity")
        
        return signals
    
    def _check_strategic_alerts(self, corridor, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for strategic corridor-specific alerts"""
        alerts = []
        
        change_count = results['change_count']
        strategic_score = results.get('strategic_score', {}).get('enhanced_total_score', 0)
        investment_signals = results.get('investment_signals', [])
        
        # High strategic score alert
        if strategic_score > 80:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'high_investment_opportunity',
                'region': corridor.name,
                'message': f"High investment opportunity: {corridor.name} scored {strategic_score:.1f}/100",
                'details': {
                    'strategic_score': strategic_score,
                    'change_count': change_count,
                    'investment_tier': corridor.investment_tier,
                    'investment_signals': investment_signals
                }
            })
        
        # Tier-1 corridor activity alert
        if corridor.investment_tier == 'tier1' and change_count > 25:
            alerts.append({
                'level': 'CRITICAL', 
                'type': 'tier1_activity',
                'region': corridor.name,
                'message': f"Tier-1 corridor high activity: {change_count} changes in {corridor.name}",
                'details': {
                    'change_count': change_count,
                    'investment_tier': corridor.investment_tier,
                    'focus': corridor.focus
                }
            })
        
        # Infrastructure catalyst timing alert
        active_catalysts = len(corridor.infrastructure_catalysts or [])
        if active_catalysts > 2 and change_count > 20:
            alerts.append({
                'level': 'MAJOR',
                'type': 'catalyst_convergence', 
                'region': corridor.name,
                'message': f"Infrastructure catalyst convergence: {active_catalysts} catalysts + {change_count} changes in {corridor.name}",
                'details': {
                    'active_catalysts': active_catalysts,
                    'catalyst_details': corridor.infrastructure_catalysts,
                    'change_count': change_count
                }
            })
        
        return alerts

    def _check_alerts(self, region_name: str, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if results trigger any alerts"""
        alerts = []
        
        change_count = results['change_count']
        total_area = results['total_area_m2']
        change_types = results.get('change_types', {})
        
        # Critical change count alert
        if change_count > self.alert_config['critical_change_count']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'high_change_count',
                'region': region_name,
                'message': f"Critical: {change_count} changes detected in {region_name}",
                'details': {
                    'change_count': change_count,
                    'threshold': self.alert_config['critical_change_count']
                }
            })
        elif change_count > self.alert_config['major_change_count']:
            alerts.append({
                'level': 'MAJOR',
                'type': 'high_change_count',
                'region': region_name,
                'message': f"Major: {change_count} changes detected in {region_name}",
                'details': {
                    'change_count': change_count,
                    'threshold': self.alert_config['major_change_count']
                }
            })
        
        # Critical area alert  
        if total_area > self.alert_config['critical_area_m2']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'large_area_change',
                'region': region_name,
                'message': f"Critical: {total_area/10000:.1f} hectares changed in {region_name}",
                'details': {
                    'area_m2': total_area,
                    'area_hectares': total_area/10000,
                    'threshold_hectares': self.alert_config['critical_area_m2']/10000
                }
            })
        elif total_area > self.alert_config['major_area_m2']:
            alerts.append({
                'level': 'MAJOR',
                'type': 'large_area_change',
                'region': region_name,
                'message': f"Major: {total_area/10000:.1f} hectares changed in {region_name}",
                'details': {
                    'area_m2': total_area,
                    'area_hectares': total_area/10000,
                    'threshold_hectares': self.alert_config['major_area_m2']/10000
                }
            })
        
        # Development hotspot alert
        if change_types and change_count > 0:
            development_ratio = change_types.get('development', 0) / change_count
            if development_ratio > self.alert_config['development_hotspot_threshold']:
                alerts.append({
                    'level': 'MAJOR',
                    'type': 'development_hotspot',
                    'region': region_name,
                    'message': f"Development hotspot: {development_ratio*100:.1f}% of changes are development in {region_name}",
                    'details': {
                        'development_ratio': development_ratio,
                        'development_count': change_types.get('development', 0),
                        'total_changes': change_count
                    }
                })
        
        # Vegetation loss alert
        if change_types and change_count > 0:
            veg_loss_ratio = change_types.get('vegetation_loss', 0) / change_count
            if veg_loss_ratio > self.alert_config['vegetation_loss_threshold']:
                alerts.append({
                    'level': 'MAJOR',
                    'type': 'vegetation_loss',
                    'region': region_name,
                    'message': f"High vegetation loss: {veg_loss_ratio*100:.1f}% of changes are vegetation loss in {region_name}",
                    'details': {
                        'vegetation_loss_ratio': veg_loss_ratio,
                        'vegetation_loss_count': change_types.get('vegetation_loss', 0),
                        'total_changes': change_count
                    }
                })
        
        return alerts

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monitoring summary statistics"""
        regions_analyzed = results['regions_analyzed']
        alerts = results['alerts']
        
        if not regions_analyzed:
            return {'status': 'no_data', 'message': 'No regions successfully analyzed'}
        
        # Calculate statistics
        region_count = len(regions_analyzed)
        total_changes = results['total_changes']
        total_area_hectares = results['total_area_m2'] / 10000
        
        # Alert statistics
        critical_alerts = len([a for a in alerts if a['level'] == 'CRITICAL'])
        major_alerts = len([a for a in alerts if a['level'] == 'MAJOR'])
        
        # Most active regions
        most_active = sorted(regions_analyzed, key=lambda x: x['change_count'], reverse=True)[:3]
        
        # Change type aggregation
        all_change_types = {}
        for region in regions_analyzed:
            for change_type, count in region.get('change_types', {}).items():
                all_change_types[change_type] = all_change_types.get(change_type, 0) + count
        
        summary = {
            'status': 'completed',
            'regions_monitored': region_count,
            'total_changes': total_changes,
            'total_area_hectares': round(total_area_hectares, 2),
            'alert_summary': {
                'critical': critical_alerts,
                'major': major_alerts,
                'total': len(alerts)
            },
            'most_active_regions': [
                {
                    'name': region['region_name'],
                    'changes': region['change_count'],
                    'area_hectares': round(region['total_area_m2'] / 10000, 2)
                }
                for region in most_active
            ],
            'change_types_total': all_change_types,
            'average_changes_per_region': round(total_changes / region_count, 1) if region_count > 0 else 0
        }
        
        return summary

    def _load_previous_region_state(self) -> Dict[str, Dict[str, Any]]:
        """Load per-region (recommendation tier, score) from the most recent prior run.

        Used by `_compute_tier_transitions` to surface regions that crossed
        a tier boundary this week — directly serves "see opportunities early":
        a region moving from PASS→WATCH or BUY→STRONG_BUY is a high-signal
        event that should jump to the top of the briefing.
        """
        import glob as glob_mod
        monitoring_dir = getattr(self, 'monitoring_dir', './output/monitoring')
        pattern = os.path.join(monitoring_dir, 'weekly_monitoring_*.json')
        files = sorted(glob_mod.glob(pattern), reverse=True)

        prev_state: Dict[str, Dict[str, Any]] = {}
        for filepath in files[:3]:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                yog = data.get('investment_analysis', {}).get('yogyakarta_analysis', {})
                regions = (yog.get('strong_buy_recommendations', []) +
                           yog.get('buy_recommendations', []) +
                           yog.get('watch_list', []) + yog.get('pass_list', []))
                for r in regions:
                    if not isinstance(r, dict):
                        continue
                    name = r.get('region_name') or r.get('region', '')
                    if not name:
                        continue
                    prev_state[name] = {
                        'recommendation': r.get('recommendation', 'PASS'),
                        'investment_score': r.get('investment_score', 0),
                        'snapshot_path': os.path.basename(filepath),
                    }
                if prev_state:
                    logger.info(f"   📊 Loaded previous tier state for {len(prev_state)} regions from {os.path.basename(filepath)}")
                    return prev_state
            except Exception as e:
                logger.debug(f"prev-state loader skipped {filepath}: {e}")
                continue
        logger.info("   📊 No previous tier state available (first run? or all priors empty)")
        return prev_state

    def _load_previous_news_counts(self) -> Dict[str, int]:
        """Load per-region news article counts from the most recent prior monitoring run.

        Bug fixed 2026-04-26: previously checked regions_analyzed first and
        bailed if non-empty. But regions_analyzed contains the SATELLITE
        analysis results which never have a news_catalyst field — that lives
        only on the post-scoring recommendation dicts (strong_buy / buy /
        watch / pass). Result: news_wow never populated even when articles
        were found. Fix: always use the recommendation lists.
        """
        import glob as glob_mod
        monitoring_dir = getattr(self, 'monitoring_dir', './output/monitoring')
        pattern = os.path.join(monitoring_dir, 'weekly_monitoring_*.json')
        files = sorted(glob_mod.glob(pattern), reverse=True)

        prev_counts = {}
        for filepath in files[:3]:  # try up to 3 most recent
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                yog = data.get('investment_analysis', {}).get('yogyakarta_analysis', {})
                regions = (yog.get('strong_buy_recommendations', []) +
                           yog.get('buy_recommendations', []) +
                           yog.get('watch_list', []) + yog.get('pass_list', []))
                for r in regions:
                    if not isinstance(r, dict):
                        continue
                    name = r.get('region_name') or r.get('region', '')
                    if not name:
                        continue
                    news = r.get('news_catalyst', {})
                    if isinstance(news, dict) and news.get('articles_found') is not None:
                        prev_counts[name] = news['articles_found']
                if prev_counts:
                    logger.info(f"   📊 Loaded previous news counts for {len(prev_counts)} regions from {os.path.basename(filepath)}")
                    return prev_counts
            except Exception as e:
                logger.debug(f"news-counts loader skipped {filepath}: {e}")
                continue
        logger.info("   📊 No previous news counts available (first run? or all priors empty)")
        return prev_counts

    def _score_single_region(
        self,
        region_data: Dict,
        prev_news_counts: Dict[str, int],
        cancel_event: Optional[threading.Event] = None,
    ) -> Optional[Dict]:
        """Score a single region. Thread-safe — no signal.alarm, uses only per-call state."""
        region_name = region_data['region_name']
        try:
            region_config = {
                'name': region_name,
                'bbox': region_data['bbox'],
                'center': {
                    'lat': (region_data['bbox']['north'] + region_data['bbox']['south']) / 2,
                    'lng': (region_data['bbox']['east'] + region_data['bbox']['west']) / 2
                }
            }
            
            optical_changes = region_data.get('change_count', 0)
            area_affected_m2 = region_data.get('total_area', 0)
            coordinates = region_config['center']
            bbox = region_config['bbox']
            
            # Fuse optical + SAR if available
            satellite_changes = optical_changes
            fusion_result = None
            sar_result = region_data.get('sar_result')
            if self.sar_detector and sar_result:
                try:
                    fusion_result = self.sar_detector.fuse_optical_and_sar(
                        optical_changes=optical_changes,
                        sar_result=sar_result
                    )
                    satellite_changes = fusion_result['fused_changes']
                    logger.info(f"   🔗 [{region_name}] Sensor fusion: {optical_changes:,} optical + {sar_result.sar_change_pixels:,} SAR → {satellite_changes:,} fused")
                except Exception as e:
                    logger.warning(f"   ⚠️ [{region_name}] SAR fusion failed: {e}")
            
            # News catalyst scoring (articles already pre-scraped)
            news_catalyst_result = None
            if self.news_scraper and self.news_catalyst and self._cached_news_articles:
                try:
                    matched_articles = self.news_scraper.match_articles_to_region(
                        self._cached_news_articles, region_name
                    )
                    news_catalyst_result = self.news_catalyst.calculate_catalyst(region_name, matched_articles)
                    if news_catalyst_result.articles_found > 0:
                        logger.info(f"   📰 [{region_name}] News catalyst: {news_catalyst_result.multiplier:.2f}x ({news_catalyst_result.articles_found} articles)")
                except Exception as e:
                    logger.warning(f"   ⚠️ [{region_name}] News catalyst failed: {e}")
            
            # News week-over-week rate of change
            news_wow = None
            if news_catalyst_result and prev_news_counts:
                current_count = news_catalyst_result.articles_found
                prev_count = prev_news_counts.get(region_name, 0)
                if prev_count > 0:
                    wow_ratio = current_count / prev_count
                    news_wow = {
                        'current_articles': current_count,
                        'previous_articles': prev_count,
                        'ratio': round(wow_ratio, 2),
                        'delta': current_count - prev_count,
                        'trend': 'surging' if wow_ratio >= 2.0 else 'increasing' if wow_ratio > 1.2 else 'stable' if wow_ratio >= 0.8 else 'declining'
                    }
                elif current_count > 0:
                    news_wow = {
                        'current_articles': current_count,
                        'previous_articles': 0,
                        'ratio': float(current_count),
                        'delta': current_count,
                        'trend': 'new_coverage'
                    }
                if news_wow:
                    logger.info(
                        f"   📰 [{region_name}] News WoW: "
                        f"{news_wow['previous_articles']}→{news_wow['current_articles']} "
                        f"(ratio={news_wow['ratio']:.2f}, trend={news_wow['trend']})"
                    )

            # Resolve satellite provenance: when fusion falls into sar_only
            # mode (optical_changes==0 but SAR has signal), the upstream
            # region_data['data_source'] is still 'optical' (optical detector
            # ran successfully, just found nothing). The SAR-only confidence
            # cap (0.84) keys off this string, so without overriding, regions
            # like Merak (Apr 27: optical=0, SAR=4.6M) skipped the cap and
            # finished at 0.99 confidence → score 61.7. Authoritative source
            # is fusion_result['source'] when present.
            if fusion_result and fusion_result['source'] == 'sar_only':
                effective_satellite_source = 'sar_only'
            else:
                effective_satellite_source = region_data.get('data_source', 'optical')

            # Calculate CORRECTED score (satellite is PRIMARY)
            corrected_result = self.corrected_scorer.calculate_investment_score(
                region_name=region_name,
                satellite_changes=satellite_changes,
                area_affected_m2=area_affected_m2,
                region_config=region_config,
                coordinates=coordinates,
                bbox=bbox,
                sar_confidence_boost=fusion_result['confidence_boost'] if fusion_result else 0.0,
                news_catalyst_multiplier=news_catalyst_result.multiplier if news_catalyst_result else 1.0,
                # Pass through satellite provenance so confidence calc can
                # penalize SAR-only and stale data (was always trusting 1.0).
                satellite_data_source=effective_satellite_source,
                satellite_data_age_days=region_data.get('data_age_days', 0),
                cancel_event=cancel_event,
            )
            
            # Financial Projection
            financial_projection = None
            if self.financial_engine:
                try:
                    satellite_data = {
                        'vegetation_loss_pixels': region_data.get('change_count', 0) // 2,
                        'total_pixels': 10000,
                        'construction_activity_pct': corrected_result.development_score * 0.2
                    }
                    infrastructure_data = {
                        'infrastructure_score': corrected_result.infrastructure_score,
                        'major_features': corrected_result.data_sources.get('infrastructure', []),
                        'data_confidence': corrected_result.confidence_level,
                        'data_source': 'osm_live' if corrected_result.data_availability.get('infrastructure', False) else 'fallback'
                    }
                    market_data = {
                        'price_trend_30d': corrected_result.price_trend_30d,
                        'market_heat': corrected_result.market_heat,
                        'data_confidence': corrected_result.confidence_level
                    }
                    financial_projection = self.financial_engine.calculate_financial_projection(
                        region_name=region_name,
                        satellite_data=satellite_data,
                        infrastructure_data=infrastructure_data,
                        market_data=market_data,
                        scoring_result=corrected_result
                    )
                    logger.info(f"   💰 [{region_name}] Financial: Rp {financial_projection.current_land_value_per_m2:,.0f}/m² "
                              f"→ Rp {financial_projection.estimated_future_value_per_m2:,.0f}/m² "
                              f"(ROI: {financial_projection.projected_roi_3yr:.1%})")
                except Exception as e:
                    logger.warning(f"   ⚠️ [{region_name}] Financial projection failed: {e}")
            
            # RVI calculation
            rvi_data = None
            if financial_projection and self.financial_engine:
                try:
                    satellite_data_for_rvi = {
                        'vegetation_loss_pixels': corrected_result.satellite_changes // 2,
                        'construction_activity_pct': corrected_result.development_score / 200.0
                    }
                    rvi_result = self.financial_engine.calculate_relative_value_index(
                        region_name=region_name,
                        actual_price_m2=financial_projection.current_land_value_per_m2,
                        infrastructure_score=corrected_result.infrastructure_score,
                        satellite_data=satellite_data_for_rvi
                    )
                    if rvi_result.get('rvi') is not None:
                        rvi_data = {
                            'rvi': rvi_result['rvi'],
                            'expected_price_m2': rvi_result['expected_price_m2'],
                            'interpretation': rvi_result['interpretation'],
                            'breakdown': rvi_result['breakdown']
                        }
                        logger.info(f"   📊 [{region_name}] RVI: {rvi_data['rvi']:.3f} ({rvi_data['interpretation']})")
                except Exception as e:
                    logger.warning(f"   ⚠️ [{region_name}] RVI calculation failed: {e}")
            
            # Momentum analysis
            momentum_data = None
            if self.momentum_analyzer:
                try:
                    momentum_data = self.momentum_analyzer.calculate_momentum(region_name)
                    if momentum_data and momentum_data.get('trend') not in ('insufficient_data', 'insufficient_baseline', 'new_region'):
                        momentum_mult = momentum_data['multiplier']
                        # Apply news WoW boost to momentum if news is surging
                        if news_wow and news_wow['trend'] in ('surging', 'increasing'):
                            news_momentum_boost = min(1.08, 1.0 + (news_wow['ratio'] - 1.0) * 0.05)
                            momentum_mult *= news_momentum_boost
                            logger.info(
                                f"   📰 [{region_name}] News WoW boost: {news_momentum_boost:.3f}x "
                                f"applied to momentum (trend={news_wow['trend']})"
                            )
                        corrected_result.final_investment_score = min(100,
                            corrected_result.final_investment_score * momentum_mult)
                        logger.info(f"   📈 [{region_name}] Momentum: {momentum_data['momentum_ratio']:.2f}x → "
                                  f"{momentum_mult:.2f}x multiplier ({momentum_data['trend']})")
                except Exception as e:
                    logger.warning(f"   ⚠️ [{region_name}] Momentum analysis failed: {e}")
            
            dynamic_score = {
                'region_name': region_name,
                'satellite_changes': corrected_result.satellite_changes,
                'change_percentage': region_data.get('change_percentage', 0),
                'development_score': corrected_result.development_score,
                'current_price_per_m2': financial_projection.current_land_value_per_m2 if financial_projection else 0,
                'price_trend_30d': corrected_result.price_trend_30d,
                'market_heat': corrected_result.market_heat,
                'infrastructure_score': corrected_result.infrastructure_score,
                'infrastructure_multiplier': corrected_result.infrastructure_multiplier,
                'infrastructure_details': corrected_result.infrastructure_details,
                'market_multiplier': corrected_result.market_multiplier,
                'speculative_score': corrected_result.development_score,
                'final_investment_score': corrected_result.final_investment_score,
                'overall_confidence': corrected_result.confidence_level,
                'recommendation': corrected_result.recommendation,
                'rationale': corrected_result.rationale,
                'data_sources': {
                    **corrected_result.data_sources,
                    'availability': corrected_result.data_availability,
                    # Satellite provenance for PDF/email confidence display.
                    # Use effective_satellite_source so sar_only fusion mode
                    # (optical_changes==0 with SAR signal) shows truthfully
                    # in PDF/email instead of mislabeled as 'optical'.
                    'satellite': effective_satellite_source,
                    'satellite_data_age_days': region_data.get('data_age_days', 0),
                    'satellite_confidence_penalty': region_data.get('confidence_penalty', 0),
                    'satellite_date_range': region_data.get('date_range_used', ''),
                },
                'analysis_type': 'dynamic_real_time',
                'financial_projection': financial_projection,
                'rvi_data': rvi_data,
                'sensitivity_flag': corrected_result.sensitivity_flag,
                'sensitivity_detail': corrected_result.sensitivity_detail,
                'score_headroom': corrected_result.score_headroom,
                'sar_data': {
                    'available': fusion_result is not None,
                    'source': fusion_result['source'] if fusion_result else 'optical_only',
                    'sar_changes': fusion_result['sar_changes'] if fusion_result else 0,
                    'sar_construction': fusion_result['sar_construction'] if fusion_result else 0,
                    'sar_clearing': fusion_result['sar_clearing'] if fusion_result else 0,
                    'confidence_boost': fusion_result['confidence_boost'] if fusion_result else 0,
                    'mean_vv_change_db': fusion_result['mean_vv_change_db'] if fusion_result else 0,
                    'mean_vh_change_db': fusion_result['mean_vh_change_db'] if fusion_result else 0,
                    'optical_changes': optical_changes,
                    'fused_changes': satellite_changes,
                    # SAR/optical disparity flag: when SAR > 20× optical, the
                    # signal is mostly SAR (which captures water dynamics, ship
                    # traffic, etc. — common false-positive source for ports
                    # and coastal regions). Surfaced so investor can verify
                    # with imagery before acting. Spot-check on Apr 26 run
                    # showed top 3 STRONG_BUYs all at >100× SAR/optical:
                    # Subang 398×, Merak 1318×, Banyuwangi 149×.
                    'sar_optical_ratio': (
                        round(fusion_result['sar_changes'] / max(1, optical_changes), 1)
                        if fusion_result else 0
                    ),
                    'sar_dominant_warning': (
                        bool(fusion_result and fusion_result['sar_changes'] > 20 * max(1, optical_changes))
                        if fusion_result else False
                    ),
                } if fusion_result else None,
                'news_catalyst': {
                    'multiplier': news_catalyst_result.multiplier,
                    'articles_found': news_catalyst_result.articles_found,
                    'positive_count': news_catalyst_result.positive_count,
                    'negative_count': news_catalyst_result.negative_count,
                    'top_keywords': news_catalyst_result.top_keywords,
                    'top_article_title': news_catalyst_result.top_article_title,
                    'summary': news_catalyst_result.summary,
                    'article_links': news_catalyst_result.article_links,
                } if news_catalyst_result else None,
                'news_wow': news_wow,
                'momentum': {
                    'multiplier': momentum_data['multiplier'],
                    'momentum_ratio': momentum_data['momentum_ratio'],
                    'trend': momentum_data['trend'],
                    'description': momentum_data['description'],
                    'recent_velocity': momentum_data['recent_velocity'],
                    'baseline_velocity': momentum_data['baseline_velocity'],
                    'data_points_recent': momentum_data.get('data_points_recent', 0),
                    'data_points_baseline': momentum_data.get('data_points_baseline', 0),
                } if momentum_data and momentum_data.get('trend') not in ('insufficient_data', 'insufficient_baseline', 'new_region') else None,
            }
            
            logger.info(
                f"✅ {region_name}: Score {corrected_result.final_investment_score:.1f}/100 "
                f"({corrected_result.confidence_level:.0%} confidence) - "
                f"{corrected_result.satellite_changes:,} changes - "
                f"{corrected_result.recommendation}"
            )
            
            available = [k for k, v in corrected_result.data_availability.items() if v]
            if len(available) < 3:
                missing = [k for k, v in corrected_result.data_availability.items() if not v]
                logger.info(f"   ⚠️ [{region_name}] Missing data: {', '.join(missing)}")
            
            return dynamic_score
            
        except Exception as e:
            logger.error(f"❌ Scoring failed for {region_name}: {e}")
            return None

    def _generate_investment_analysis(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive real estate investment analysis combining regional and strategic analysis"""
        regions_analyzed = results['regions_analyzed']
        
        if not regions_analyzed:
            return {'status': 'no_data', 'message': 'No regions to analyze for investment'}
        
        # Separate regional and strategic corridor analyses
        yogyakarta_regions = [r for r in regions_analyzed if r.get('analysis_type') == 'yogyakarta_region']
        strategic_corridors = [r for r in regions_analyzed if r.get('analysis_type') == 'strategic_corridor']
        other_regions = [r for r in regions_analyzed if r.get('analysis_type') not in ['yogyakarta_region', 'strategic_corridor']]
        
        investment_report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_components': {
                'yogyakarta_regions': len(yogyakarta_regions),
                'strategic_corridors': len(strategic_corridors),
                'other_regions': len(other_regions)
            },
            'yogyakarta_analysis': {},
            'strategic_corridor_analysis': {},
            'combined_recommendations': {},
            'executive_summary': {}
        }
        
        # 🚀 Parallel dynamic scoring with ThreadPoolExecutor
        if yogyakarta_regions:
            try:
                logger.info("🔄 Running DYNAMIC scoring analysis (parallel, no static assumptions)...")
                logger.info(
                    "   ⏳ Scoring phase timing is separate from satellite batch progress: "
                    "each region may call Overpass (roads → airports → railways) with global throttling; "
                    "a cold OSM cache often means tens of minutes to well over an hour for many regions."
                )

                # Pre-scrape news once before parallel scoring
                if self.news_scraper and self.news_catalyst and self._cached_news_articles is None:
                    try:
                        self._cached_news_articles = self.news_scraper.scrape_all_sources()
                        logger.info(f"   📰 Pre-scraped {len(self._cached_news_articles)} news articles for scoring")
                    except Exception as e:
                        logger.warning(f"   ⚠️ News pre-scrape failed: {e}")
                        self._cached_news_articles = []
                
                # Load previous run's news counts for week-over-week comparison
                prev_news_counts = self._load_previous_news_counts()
                
                from concurrent.futures import ThreadPoolExecutor, as_completed

                dynamic_scored_regions = []
                failed_regions: List[Dict[str, Any]] = []  # track failures for summary + retry
                # Default 2: Overpass is throttled globally, but fewer concurrent scorers
                # reduces memory pressure and scraper/API contention during full runs.
                _mw = int(os.environ.get("CC_SCORING_MAX_WORKERS", "2"))
                max_workers = max(1, min(_mw, len(yogyakarta_regions)))
                n_score = len(yogyakarta_regions)
                logger.info(f"   ⚡ Scoring {n_score} regions with {max_workers} parallel workers")
                _region_timeout = int(os.environ.get("CC_SCORE_REGION_TIMEOUT_SEC", "1200"))

                # Map region_name → cancel_event so outer timeout can signal in-flight Overpass
                cancel_events: Dict[str, threading.Event] = {}

                def _submit_region(executor, region_data, cancel_events_map):
                    rn = region_data['region_name']
                    evt = threading.Event()
                    cancel_events_map[rn] = evt
                    future = executor.submit(
                        self._score_single_region, region_data, prev_news_counts,
                        cancel_event=evt,
                    )
                    return future

                # --- initial pass ---
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_region = {}
                    region_data_by_name = {}
                    for region_data in yogyakarta_regions:
                        region_data_by_name[region_data['region_name']] = region_data
                        future = _submit_region(executor, region_data, cancel_events)
                        future_to_region[future] = region_data['region_name']

                    scoring_t0 = time.monotonic()
                    completed_score = 0
                    for future in as_completed(future_to_region):
                        region_name = future_to_region[future]
                        ok = False
                        try:
                            result = future.result(timeout=_region_timeout)
                            if result:
                                dynamic_scored_regions.append(result)
                                ok = True
                            else:
                                failed_regions.append({
                                    'region_name': region_name,
                                    'error': 'returned None (scoring produced no result)',
                                    'phase': 'initial',
                                })
                        except Exception as e:
                            # Signal cancellation so in-flight Overpass bails out quickly
                            evt = cancel_events.get(region_name)
                            if evt is not None:
                                evt.set()
                            failed_regions.append({
                                'region_name': region_name,
                                'error': str(e),
                                'error_type': type(e).__name__,
                                'traceback': traceback.format_exc(),
                                'phase': 'initial',
                            })
                            logger.error(
                                f"❌ Scoring failed for {region_name}: {type(e).__name__}: {e}"
                            )

                        completed_score += 1
                        elapsed_min = (time.monotonic() - scoring_t0) / 60.0
                        remaining = n_score - completed_score
                        if completed_score > 0 and remaining > 0:
                            eta_min = (elapsed_min / completed_score) * remaining
                            eta_part = f" | scoring ETA ~{eta_min:.1f} min ({remaining} left)"
                        elif remaining == 0:
                            eta_part = " | scoring phase complete"
                        else:
                            eta_part = ""
                        status = "ok" if ok else "FAILED"
                        logger.info(
                            f"   📈 Scoring [{completed_score}/{n_score}] {region_name} ({status}) — "
                            f"{elapsed_min:.1f} min in scoring phase{eta_part}"
                        )

                # --- retry pass (sequential, one attempt) for failed regions ---
                if failed_regions:
                    retryable = [f for f in failed_regions if f['phase'] == 'initial']
                    if retryable:
                        logger.info(
                            f"   🔄 Retrying {len(retryable)} failed region(s) sequentially..."
                        )
                        still_failed = []
                        for failure in retryable:
                            rn = failure['region_name']
                            rd = region_data_by_name.get(rn)
                            if rd is None:
                                still_failed.append(failure)
                                continue
                            try:
                                # Fresh cancel event, no outer timeout — run sequentially
                                result = self._score_single_region(rd, prev_news_counts)
                                if result:
                                    dynamic_scored_regions.append(result)
                                    logger.info(f"   ✅ Retry succeeded for {rn}")
                                else:
                                    failure['phase'] = 'retry'
                                    still_failed.append(failure)
                                    logger.warning(f"   ⚠️ Retry returned None for {rn}")
                            except Exception as e:
                                failure['error'] = str(e)
                                failure['error_type'] = type(e).__name__
                                failure['traceback'] = traceback.format_exc()
                                failure['phase'] = 'retry'
                                still_failed.append(failure)
                                logger.error(f"   ❌ Retry also failed for {rn}: {type(e).__name__}: {e}")
                        failed_regions = still_failed

                # --- error summary ---
                if failed_regions:
                    logger.warning(
                        f"   ⚠️ SCORING SUMMARY: {len(dynamic_scored_regions)}/{n_score} succeeded, "
                        f"{len(failed_regions)} failed after retry"
                    )
                    for f in failed_regions:
                        logger.warning(
                            f"      FAILED: {f['region_name']} — "
                            f"{f.get('error_type', 'Unknown')}: {f.get('error', '?')}"
                        )
                else:
                    logger.info(
                        f"   ✅ SCORING SUMMARY: all {n_score} regions scored successfully"
                    )

                if dynamic_scored_regions:
                    # Generate investment report using dynamic scores
                    yogyakarta_report = self._generate_dynamic_investment_report(
                        dynamic_scored_regions, failed_regions=failed_regions,
                    )
                    investment_report['yogyakarta_analysis'] = yogyakarta_report

                    dynamic_count = sum(1 for r in dynamic_scored_regions if r.get('analysis_type') == 'dynamic_real_time')
                    total_opportunities = len(yogyakarta_report.get('buy_recommendations', []))

                    logger.info(
                        f"🎯 DYNAMIC MARKET Analysis: {dynamic_count}/{n_score} regions analyzed "
                        f"with real-time data ({len(failed_regions)} failed)"
                    )
                    logger.info(f"💰 Investment opportunities identified: {total_opportunities}")
                    
            except Exception as e:
                logger.warning(f"Dynamic Yogyakarta investment analysis failed: {e}")
                investment_report['yogyakarta_analysis'] = {'status': 'failed', 'error': str(e)}
        
        # Analyze strategic corridors using enhanced scoring
        if strategic_corridors and self.strategic_analysis_enabled:
            try:
                strategic_analysis = self._generate_strategic_opportunities(strategic_corridors)
                investment_report['strategic_corridor_analysis'] = strategic_analysis
                logger.info(f"INDONESIA Strategic corridor analysis: {len(strategic_analysis.get('high_conviction_opportunities', []))} high-conviction opportunities")
            except Exception as e:
                logger.warning(f"Strategic corridor analysis failed: {e}")
                investment_report['strategic_corridor_analysis'] = {'status': 'failed', 'error': str(e)}
        
        # Generate combined recommendations
        investment_report['combined_recommendations'] = self._generate_combined_recommendations(investment_report)
        
        # Generate executive summary  
        investment_report['executive_summary'] = self._generate_investment_executive_summary(investment_report)
        
        total_opportunities = (
            len(investment_report.get('yogyakarta_analysis', {}).get('buy_recommendations', [])) +
            len(investment_report.get('strategic_corridor_analysis', {}).get('high_conviction_opportunities', []))
        )
        
        logger.info(f"INVESTMENT Complete investment analysis: {total_opportunities} total opportunities identified")
        
        return investment_report

    def _generate_strategic_opportunities(self, strategic_corridors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate strategic corridor investment opportunities"""
        high_conviction = []  # Score > 80
        selective_opportunities = []  # Score 70-80
        watch_list = []  # Score 60-70
        
        for corridor_data in strategic_corridors:
            corridor_name = corridor_data['region_name']
            strategic_score_data = corridor_data.get('strategic_score', {})
            enhanced_score = strategic_score_data.get('enhanced_total_score', 0)
            investment_signals = corridor_data.get('investment_signals', [])
            corridor_info = corridor_data.get('corridor_info', {})
            
            opportunity = {
                'corridor_name': corridor_name,
                'score': enhanced_score,
                'investment_tier': corridor_info.get('investment_tier', 'unknown'),
                'island': corridor_info.get('island', 'unknown'),
                'focus': corridor_info.get('focus', 'unknown'),
                'change_count': corridor_data.get('change_count', 0),
                'investment_signals': investment_signals,
                'satellite_activity': {
                    'change_count': corridor_data.get('change_count', 0),
                    'change_types': corridor_data.get('change_types', {}),
                    'total_area_m2': corridor_data.get('total_area_m2', 0),
                    'satellite_images': corridor_data.get('satellite_images', {})
                },                'infrastructure_context': corridor_data.get('infrastructure_context', {}),
                'risk_level': corridor_info.get('risk_level', 'unknown')
            }
            
            # Categorize by score
            if enhanced_score > 80:
                opportunity['recommendation'] = 'STRONG BUY - Immediate land banking'
                high_conviction.append(opportunity)
            elif enhanced_score > 70:
                opportunity['recommendation'] = 'BUY - Selective acquisition'
                selective_opportunities.append(opportunity)
            else:
                opportunity['recommendation'] = 'WATCH - Monitor for improvements'
                watch_list.append(opportunity)
        
        # Sort by score within each category
        high_conviction.sort(key=lambda x: x['score'], reverse=True)
        selective_opportunities.sort(key=lambda x: x['score'], reverse=True)
        watch_list.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'analysis_type': 'strategic_corridors',
            'total_corridors_analyzed': len(strategic_corridors),
            'high_conviction_opportunities': high_conviction,
            'selective_opportunities': selective_opportunities,
            'watch_list': watch_list,
            'top_opportunity': high_conviction[0] if high_conviction else (selective_opportunities[0] if selective_opportunities else None)
        }
    
    def _generate_combined_recommendations(self, investment_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate combined investment recommendations across all analysis types"""
        
        # Collect all opportunities
        all_opportunities = []
        
        # Yogyakarta opportunities
        yogyakarta_analysis = investment_report.get('yogyakarta_analysis', {})
        if yogyakarta_analysis.get('buy_recommendations'):
            for opp in yogyakarta_analysis['buy_recommendations']:
                # Get score from various possible fields
                score = opp.get('score', opp.get('investment_score', opp.get('dynamic_score', 0)))
                all_opportunities.append({
                    'region': opp['region'],
                    'score': score,
                    'type': 'yogyakarta_region',
                    'recommendation': 'BUY'
                })
        
        # Strategic corridor opportunities
        strategic_analysis = investment_report.get('strategic_corridor_analysis', {})
        if strategic_analysis.get('high_conviction_opportunities'):
            for opp in strategic_analysis['high_conviction_opportunities']:
                # Get score from various possible fields
                score = opp.get('score', opp.get('investment_score', opp.get('dynamic_score', 0)))
                all_opportunities.append({
                    'region': opp['corridor_name'],
                    'score': score,
                    'type': 'strategic_corridor',
                    'recommendation': 'STRONG BUY',
                    'investment_tier': opp.get('investment_tier'),
                    'island': opp.get('island'),
                    'change_count': opp.get('change_count', 0)
                })
        
        # Sort all opportunities by score
        all_opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'total_opportunities': len(all_opportunities),
            'top_5_opportunities': all_opportunities[:5],
            'high_conviction_total': len([o for o in all_opportunities if o['score'] > 80])
        }
    
    def _generate_investment_executive_summary(self, investment_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for investment analysis"""
        
        # Count opportunities across all analysis types
        yogyakarta_opps = len(investment_report.get('yogyakarta_analysis', {}).get('buy_recommendations', []))
        strategic_opps = len(investment_report.get('strategic_corridor_analysis', {}).get('high_conviction_opportunities', []))
        
        total_opps = yogyakarta_opps + strategic_opps
        
        # Get top opportunity
        combined_recs = investment_report.get('combined_recommendations', {})
        top_opportunities = combined_recs.get('top_5_opportunities', [])
        top_opportunity = top_opportunities[0] if top_opportunities else None
        
        # Market assessment
        if strategic_opps > 3 or total_opps > 5:
            market_status = "🟢 STRONG MARKET - Multiple high-conviction opportunities"
        elif strategic_opps > 1 or total_opps > 3:
            market_status = "🟡 MODERATE MARKET - Selective opportunities available"
        else:
            market_status = "🔴 WEAK MARKET - Limited opportunities detected"
        
        return {
            'market_status': market_status,
            'opportunity_breakdown': {
                'yogyakarta_opportunities': yogyakarta_opps,
                'strategic_corridor_opportunities': strategic_opps,
                'total_opportunities': total_opps
            },
            'top_opportunity': {
                'region': top_opportunity['region'] if top_opportunity else None,
                'score': top_opportunity['score'] if top_opportunity else None,
                'type': top_opportunity['type'] if top_opportunity else None
            } if top_opportunity else None,
            'analysis_confidence': 'HIGH' if self.strategic_analysis_enabled else 'MEDIUM'
        }

    async def _save_monitoring_results(self, results: Dict[str, Any]):
        """Save monitoring results to database and/or file"""
        # Save to file (always available)
        output_dir = Path('./output/monitoring')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_dir / f"weekly_monitoring_{timestamp}.json"
        
        # Custom JSON serializer for dataclasses
        def dataclass_serializer(obj):
            """Convert dataclasses to dicts for JSON serialization"""
            if is_dataclass(obj) and not isinstance(obj, type):
                return asdict(obj)
            return str(obj)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=dataclass_serializer)
        
        logger.info(f"📁 Monitoring results saved to: {filename}")
        
        # Generate PDF executive summary
        try:
            from .pdf_report_generator import generate_pdf_from_json
            pdf_path = generate_pdf_from_json(str(filename))
            logger.info(f"📄 Executive summary PDF generated: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to generate PDF report: {e}")
        
        # Generate HTML imagery viewer
        try:
            from .satellite_imagery_viewer import create_imagery_viewer
            html_path = create_imagery_viewer(str(filename))
            logger.info(f"🌐 HTML imagery viewer generated: {html_path}")
        except Exception as e:
            logger.warning(f"Failed to generate imagery viewer: {e}")
        
        # Generate cached imagery viewer (optional - requires more time)
        # Uncomment the following lines to enable automatic cached imagery generation
        # try:
        #     from .ee_image_downloader import create_cached_imagery_viewer
        #     cache_path = create_cached_imagery_viewer(str(filename))
        #     logger.info(f"🛰️ Cached imagery viewer generated: {cache_path}")
        # except Exception as e:
        #     logger.warning(f"Failed to generate cached imagery viewer: {e}")
        
        # Save to database if available (intentionally disabled — outputs are JSON)
        if self.db_manager:
            try:
                await self.db_manager.save_monitoring_results(results)
            except Exception as e:
                logger.warning(f"Failed to save to database: {e}")

    async def _send_alerts(self, results: Dict[str, Any]):
        """Send alerts via configured channels"""
        alerts = results['alerts']
        critical_alerts = [a for a in alerts if a['level'] == 'CRITICAL']
        major_alerts = [a for a in alerts if a['level'] == 'MAJOR']
        
        # Log alerts
        if critical_alerts:
            logger.critical(f"🚨 {len(critical_alerts)} CRITICAL alerts triggered!")
            for alert in critical_alerts:
                logger.critical(f"   - {alert['message']}")
        
        if major_alerts:
            logger.warning(f"⚠️  {len(major_alerts)} MAJOR alerts triggered!")
            for alert in major_alerts:
                logger.warning(f"   - {alert['message']}")
        
        # TODO: Implement email/SMS/Slack notifications
        # This is where you'd integrate with:
        # - Email services (SMTP, SendGrid, etc.)
        # - SMS services (Twilio, AWS SNS, etc.)  
        # - Slack/Discord webhooks
        # - Custom notification endpoints

    async def run_historical_analysis(self, months_back: int = 6) -> Dict[str, Any]:
        """
        Run historical trend analysis to identify long-term patterns
        
        Args:
            months_back: Number of months to analyze backwards
            
        Returns:
            Historical analysis results
        """
        logger.info(f"MARKET Starting historical analysis for {months_back} months")
        
        # This would analyze trends over time:
        # - Seasonal patterns in development
        # - Acceleration/deceleration of changes
        # - Regional comparison over time
        # - Prediction of future hotspots
        
        # For now, return placeholder
        return {
            'analysis_type': 'historical_trends',
            'period_months': months_back,
            'status': 'not_implemented',
            'message': 'Historical analysis will be implemented in future version'
        }

    def _generate_dynamic_investment_report(
        self,
        dynamic_scored_regions: List[Dict[str, Any]],
        failed_regions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate investment report from dynamic scoring results.
        Regions are sorted by investment score (highest first).
        """
        # Recommendation buckets — STRONG_BUY split out 2026-04-25 because the
        # old "BUY ≥40" gate was catching 67% of the universe (median = 46.8).
        # See corrected_scoring.py THRESHOLD_* constants.
        from .corrected_scoring import CorrectedInvestmentScorer as _Sc
        T_SB = _Sc.THRESHOLD_STRONG_BUY  # 58
        T_B = _Sc.THRESHOLD_BUY          # 50
        T_W = _Sc.THRESHOLD_WATCH        # 35
        C_SB = _Sc.CONF_GATE_STRONG_BUY  # 0.85
        C_B = _Sc.CONF_GATE_BUY          # 0.75
        C_W = _Sc.CONF_GATE_WATCH        # 0.50

        strong_buy_recommendations = []
        buy_recommendations = []
        watch_list = []
        pass_list = []
        market_insights = []
        
        # Sort regions by investment score (highest first)
        sorted_regions = sorted(
            dynamic_scored_regions, 
            key=lambda x: x.get('final_investment_score', 0), 
            reverse=True
        )
        
        for region_score in sorted_regions:
            region_name = region_score['region_name']
            investment_score = region_score.get('final_investment_score', 0)
            confidence = region_score.get('overall_confidence', 0)
            price_trend = region_score.get('price_trend_30d', 0)
            
            # Create recommendation based on dynamic scoring
            recommendation = {
                'region': region_name,
                'investment_score': investment_score,
                'confidence': confidence,  # Standardized key name
                'confidence_level': confidence,  # Backward compat
                'current_price_per_m2': region_score.get('current_price_per_m2', 0),
                'price_trend_30d': price_trend,
                'market_heat': region_score.get('market_heat', 'unknown'),
                'infrastructure_score': region_score.get('infrastructure_score', 0),
                'infrastructure_details': region_score.get('infrastructure_details', {}),
                'satellite_changes': region_score.get('satellite_changes', 0),
                'data_sources': region_score.get('data_sources', {}),
                'analysis_type': region_score.get('analysis_type', 'dynamic'),
                'financial_projection': region_score.get('financial_projection'),
                'sensitivity_flag': region_score.get('sensitivity_flag'),
                'sensitivity_detail': region_score.get('sensitivity_detail'),
                'score_headroom': region_score.get('score_headroom'),
                'sar_data': region_score.get('sar_data'),
                'news_catalyst': region_score.get('news_catalyst'),
                'news_wow': region_score.get('news_wow'),
                'momentum': region_score.get('momentum'),
                'rvi_data': region_score.get('rvi_data'),
            }
            
            # Tightened thresholds — see corrected_scoring.CorrectedInvestmentScorer
            # THRESHOLD_* constants. Median of the Apr 25 run was 46.8; old gate
            # of ≥40 caught 67% of regions and made BUY meaningless. New tiers:
            #   STRONG_BUY ≥58, conf ≥0.85  — top-decile, prioritize for DD
            #   BUY        ≥50, conf ≥0.75  — solid signal, verify before acting
            #   WATCH      ≥35, conf ≥0.50  — monitor for upgrade
            #   PASS       below either gate
            def _build_rationale():
                parts = []
                if price_trend > 5:
                    parts.append(f"Strong price momentum (+{price_trend:.1f}%)")
                elif price_trend < -3:
                    parts.append(f"Price correction ({price_trend:.1f}%)")
                else:
                    parts.append(f"Stable market ({price_trend:+.1f}%)")
                sc = region_score.get('satellite_changes', 0)
                if sc > 10000:
                    parts.append(f"Very high development: {sc:,} changes")
                elif sc > 5000:
                    parts.append(f"High development: {sc:,} changes")
                elif sc > 1000:
                    parts.append(f"Moderate activity: {sc:,} changes")
                return " • ".join(parts)

            if investment_score >= T_SB and confidence >= C_SB:
                recommendation['recommendation'] = 'STRONG_BUY'
                recommendation['rationale'] = "🔥 STRONG BUY • " + _build_rationale()
                strong_buy_recommendations.append(recommendation)

            elif investment_score >= T_B and confidence >= C_B:
                recommendation['recommendation'] = 'BUY'
                recommendation['rationale'] = _build_rationale()
                buy_recommendations.append(recommendation)

            elif investment_score >= T_W and confidence >= C_W:
                recommendation['recommendation'] = 'WATCH'
                recommendation['rationale'] = f"Moderate potential ({investment_score:.1f}/100) with monitoring advised. "
                if confidence < C_B:
                    recommendation['rationale'] += f"Lower confidence ({confidence:.1%}) suggests careful evaluation. "
                watch_list.append(recommendation)

            else:
                recommendation['recommendation'] = 'PASS'
                recommendation['rationale'] = f"Below investment threshold ({investment_score:.1f}/100). "
                if region_score.get('satellite_changes', 0) == 0:
                    recommendation['rationale'] += "No significant development detected. "
                else:
                    recommendation['rationale'] += f"Limited activity: {region_score.get('satellite_changes', 0):,} changes. "
                pass_list.append(recommendation)
            
            # Add market insights
            if price_trend != 0:
                insight = {
                    'region': region_name,
                    'insight_type': 'price_trend',
                    'description': f"Price trend: {price_trend:+.1f}% over 30 days",
                    'impact': 'positive' if price_trend > 0 else 'negative'
                }
                market_insights.append(insight)
        
        # Calculate summary statistics
        dynamic_regions = [r for r in sorted_regions if r.get('analysis_type') == 'dynamic_real_time']
        avg_confidence = sum(r.get('overall_confidence', 0) for r in sorted_regions) / len(sorted_regions) if sorted_regions else 0
        
        # Sort all recommendation lists by score (highest first)
        strong_buy_recommendations.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        buy_recommendations.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        watch_list.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        pass_list.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        
        _failed = failed_regions or []
        _failed_summary = [
            {'region': f['region_name'], 'error': f.get('error', '?'), 'phase': f.get('phase', '?')}
            for f in _failed
        ]

        return {
            'strong_buy_recommendations': strong_buy_recommendations,
            'buy_recommendations': buy_recommendations,
            'watch_list': watch_list,
            'pass_list': pass_list,
            'market_insights': market_insights,
            'failed_regions': _failed_summary,
            'summary': {
                'total_regions_attempted': len(dynamic_scored_regions) + len(_failed),
                'total_regions_analyzed': len(dynamic_scored_regions),
                'failed_region_count': len(_failed),
                'dynamic_analysis_count': len(dynamic_regions),
                'buy_recommendations_count': len(buy_recommendations),
                'watch_list_count': len(watch_list),
                'pass_list_count': len(pass_list),
                'average_confidence': avg_confidence,
                'analysis_methodology': 'dynamic_real_time_intelligence'
            }
        }

# Scheduler integration for automated runs
class MonitoringScheduler:
    """
    Scheduler for automated monitoring runs
    """
    
    def __init__(self, monitor: AutomatedMonitor):
        self.monitor = monitor
        self.is_running = False
    
    async def start_weekly_schedule(self):
        """Start the weekly monitoring schedule"""
        self.is_running = True
        logger.info("📅 Starting weekly monitoring schedule")
        
        while self.is_running:
            try:
                # Run monitoring
                results = await self.monitor.run_weekly_monitoring()
                
                # Wait for next week (7 days = 604800 seconds)
                # For testing, you might want to use shorter intervals
                await asyncio.sleep(604800)  # 7 days
                
            except Exception as e:
                logger.error(f"Scheduled monitoring failed: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    def stop_schedule(self):
        """Stop the monitoring schedule"""
        self.is_running = False
        logger.info("⏹️  Stopping weekly monitoring schedule")

# CLI interface for manual monitoring
async def run_monitoring_cli():
    """Command-line interface for running monitoring manually"""
    monitor = AutomatedMonitor()
    
    print("🤖 CloudClearing Automated Monitor")
    print("==================================")
    
    try:
        results = await monitor.run_weekly_monitoring()
        
        print(f"\n✅ Monitoring Complete!")
        print(f"MARKET Summary:")
        
        summary = results['summary']
        if summary.get('status') == 'no_data':
            print(f"   - Status: {summary['message']}")
            print(f"   - Regions attempted: {len(results.get('errors', []))}")
            print(f"   - All regions failed due to data access issues")
        else:
            print(f"   - Regions monitored: {summary.get('regions_monitored', 0)}")
            print(f"   - Total changes: {summary.get('total_changes', 0)}")
            print(f"   - Total area: {summary.get('total_area_hectares', 0)} hectares")
            print(f"   - Alerts: {summary.get('alert_summary', {}).get('total', 0)}")
        
        if results['alerts']:
            print("\n🚨 Alerts:")
            for alert in results['alerts']:
                print(f"   - {alert['level']}: {alert['message']}")        
        if results.get('errors'):
            print("\n⚠️  Issues encountered:")
            print("\nIssues encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        # Show investment analysis
        investment_analysis = results.get('investment_analysis', {})
        if investment_analysis.get('status') != 'no_data':
            print("\n💰 COMPREHENSIVE INVESTMENT ANALYSIS:")
            
            # Show executive summary first
            exec_summary = investment_analysis.get('executive_summary', {})
            if exec_summary:
                print(f"📊 Market Status: {exec_summary.get('market_status', 'Unknown')}")
                
                breakdown = exec_summary.get('opportunity_breakdown', {})
                print(f"🎯 Opportunities Found:")
                print(f"   • Yogyakarta Regions: {breakdown.get('yogyakarta_opportunities', 0)}")
                print(f"   • Strategic Corridors: {breakdown.get('strategic_corridor_opportunities', 0)}")
                print(f"   • Total Opportunities: {breakdown.get('total_opportunities', 0)}")
                
                top_opp = exec_summary.get('top_opportunity')
                if top_opp and top_opp.get('region'):
                    print(f"🏆 TOP OPPORTUNITY: {top_opp['region'].upper()} ({top_opp['score']:.1f}/100, {top_opp['type']})")
            
                        # Show Yogyakarta analysis
            yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
            if yogyakarta_analysis.get('buy_recommendations'):
                buy_recs = yogyakarta_analysis['buy_recommendations']
                print(f"🏠 RESIDENTIAL YOGYAKARTA OPPORTUNITIES ({len(buy_recs)}):")
                for rec in buy_recs:
                    print(f"   🎯 {rec['region'].upper()}: {rec['score']:.1f}/100 (confidence: {rec['confidence']:.1%})")
                    for reason in rec['reasoning'][:2]:  # Top 2 reasons
                        print(f"      - {reason}")
                    
                    # Show satellite images if available
                    if 'satellite_images' in rec and rec['satellite_images']:
                        img_data = rec['satellite_images']
                        if 'error' not in img_data:
                            print(f"      📡 SATELLITE IMAGERY:")
                            if 'week_a_true_color' in img_data:
                                print(f"         🌍 Before: {img_data['week_a_true_color']}")
                            if 'week_b_true_color' in img_data:
                                print(f"         🌍 After:  {img_data['week_b_true_color']}")
                            if 'ndvi_change' in img_data:
                                print(f"         🌱 NDVI Change: {img_data['ndvi_change']}")
            
            # Show strategic corridor analysis
            strategic_analysis = investment_analysis.get('strategic_corridor_analysis', {})
            if strategic_analysis.get('high_conviction_opportunities'):
                high_conv = strategic_analysis['high_conviction_opportunities']
                if high_conv:
                    print(f"\n🇮🇩 INDONESIAN STRATEGIC CORRIDORS ({len(high_conv)} high-conviction):")
                    for opp in high_conv:
                        tier = opp.get('investment_tier', 'unknown')
                        island = opp.get('island', 'unknown').title()
                        changes = opp.get('change_count', 0)
                        signals = len(opp.get('investment_signals', []))
                        print(f"   🎯 {opp['corridor_name'].upper()}: {opp['score']:.1f}/100")
                        print(f"      📍 {island} • {tier} • {changes} satellite changes • {signals} signals")
                        
                        # Show top investment signals
                        for signal in opp.get('investment_signals', [])[:2]:
                            print(f"      ✅ {signal}")
                        
                        # Show satellite images if available
                        satellite_activity = opp.get('satellite_activity', {})
                        if 'satellite_images' in satellite_activity:
                            img_data = satellite_activity['satellite_images']
                            if img_data and 'error' not in img_data:
                                print(f"      📡 SATELLITE IMAGERY:")
                                if 'week_a_true_color' in img_data:
                                    print(f"         🌍 Before: {img_data['week_a_true_color']}")
                                if 'week_b_true_color' in img_data:
                                    print(f"         🌍 After:  {img_data['week_b_true_color']}")
                                if 'ndvi_change' in img_data:
                                    print(f"         🌱 NDVI Change: {img_data['ndvi_change']}")
                
                # Show selective opportunities
                selective = strategic_analysis.get('selective_opportunities', [])
                if selective:
                    print(f"\n📈 SELECTIVE STRATEGIC OPPORTUNITIES ({len(selective)}):")
                    for opp in selective:
                        island = opp.get('island', 'unknown').title()
                        print(f"   📊 {opp['corridor_name']}: {opp['score']:.1f}/100 ({island})")
            
            # Show combined recommendations
            combined_recs = investment_analysis.get('combined_recommendations', {})
            if combined_recs.get('top_5_opportunities'):
                print(f"\n🏆 TOP 5 COMBINED OPPORTUNITIES:")
                for i, opp in enumerate(combined_recs['top_5_opportunities'][:5], 1):
                    region_type = "RESIDENTIAL" if opp['type'] == 'yogyakarta_region' else "INDONESIA"
                    print(f"   {i}. {region_type} {opp['region']}: {opp['score']:.1f}/100 ({opp['recommendation']})")
            
            print(f"\n📋 Analysis Confidence: {exec_summary.get('analysis_confidence', 'UNKNOWN')}")
    
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")


if __name__ == "__main__":
    # Run monitoring manually
    asyncio.run(run_monitoring_cli())
