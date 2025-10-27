"""
Automated Weekly Monitoring System for CloudClearingAPI

This module implements automated weekly satellite monitoring across multiple regions,
with alerting, historical tracking, and comprehensive reporting.
"""

import asyncio
import logging
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
        
        # Initialize database if available
        self.db_manager = None
        logger.warning("Database functionality disabled due to SQLAlchemy compatibility issues")
        
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
        # Dynamic fallback: progressively tries older weeks (up to 20 attempts)
        now = datetime.now()
        max_attempts = 20
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
        
        # Try each date range for this region until one works
        last_error = None
        for attempt_num, (start_date, end_date, description) in enumerate(date_attempts):
            try:
                week_a_str = start_date.strftime('%Y-%m-%d')
                week_b_str = end_date.strftime('%Y-%m-%d')
                
                if attempt_num > 0:
                    logger.info(f"   🔄 {region_name}: Trying fallback {description}: {week_a_str} to {week_b_str}")
                
                # Run change detection
                results = self.detector.detect_weekly_changes(
                    week_a_start=week_a_str,
                    week_b_start=week_b_str,
                    bbox=bbox,
                    export_results=True
                )
                
                # Check if we got valid results (not empty composites or errors)
                # Check for error in change_types dict or if change_count is 0 with error in satellite_images
                has_error = (
                    'error' in results.get('change_types', {}) or
                    (results.get('change_count', 0) == 0 and 
                     'error' in results.get('satellite_images', {}))
                )
                
                if has_error:
                    # Empty composite or computation error, try next fallback
                    if attempt_num < len(date_attempts) - 1:
                        logger.warning(f"   ⚠️ {region_name}: {description} unavailable, will try next fallback")
                        continue
                    else:
                        logger.error(f"   ❌ {region_name}: All {len(date_attempts)} date range attempts failed!")
                        return None
                
                # If we got here without error, we have good data!
                # Enhance results with region info and save satellite images
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
                    'date_range_used': description  # Track which fallback was used
                }
                
                if attempt_num > 0:
                    logger.info(f"   ✅ {region_name}: Successfully analyzed using {description}")
                
                return region_result
                
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                # Check if this is a satellite data availability issue
                if "no bands" in error_msg.lower() or "empty composite" in error_msg.lower():
                    # This date range didn't work, try the next one
                    if attempt_num < len(date_attempts) - 1:
                        logger.warning(f"   ⚠️ {region_name}: {description} unavailable, will try next fallback")
                        continue
                    else:
                        # All dynamic attempts failed
                        logger.error(f"   ❌ {region_name}: All {len(date_attempts)} date range attempts failed!")
                        return None
                else:
                    # Some other error, don't retry
                    logger.error(f"Region analysis failed for {region_name}: {e}")
                    return None
        
        # If we got here, all attempts failed
        logger.error(f"❌ {region_name}: Failed to analyze after {len(date_attempts)} attempts. Last error: {last_error}")
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
        
        # 🚀 NEW: Analyze Yogyakarta regions using 100% DYNAMIC real-time scoring
        if yogyakarta_regions:
            try:
                logger.info("🔄 Running DYNAMIC scoring analysis (no more static assumptions)...")
                dynamic_scored_regions = []
                
                for region_data in yogyakarta_regions:
                    try:
                        # Convert region data to format needed by dynamic scorer
                        region_name = region_data['region_name']
                        region_config = {
                            'name': region_name,
                            'bbox': region_data['bbox'],
                            'center': {
                                'lat': (region_data['bbox']['north'] + region_data['bbox']['south']) / 2,
                                'lng': (region_data['bbox']['east'] + region_data['bbox']['west']) / 2
                            }
                        }
                        
                        # ✅ CORRECTED SCORING: Satellite-centric with infrastructure/market multipliers
                        # Wrap with timeout to prevent hanging on external API calls (OSM, etc)
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError("Corrected scoring exceeded 45 second timeout")
                        
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(45)  # 45 second timeout for scoring
                        
                        try:
                            # Get satellite data from change detection
                            satellite_changes = region_data.get('change_count', 0)
                            area_affected_m2 = region_data.get('total_area', 0)
                            coordinates = region_config['center']
                            bbox = region_config['bbox']
                            
                            # Calculate CORRECTED score (satellite is PRIMARY!)
                            corrected_result = self.corrected_scorer.calculate_investment_score(
                                region_name=region_name,
                                satellite_changes=satellite_changes,
                                area_affected_m2=area_affected_m2,
                                region_config=region_config,
                                coordinates=coordinates,
                                bbox=bbox
                            )
                            signal.alarm(0)  # Cancel the alarm
                        except TimeoutError as te:
                            signal.alarm(0)  # Cancel the alarm
                            raise Exception(f"Corrected scoring timeout: {te}")
                        
                        # --- NEW: Calculate Financial Projection ---
                        financial_projection = None
                        if self.financial_engine:
                            try:
                                # Prepare data for financial engine
                                satellite_data = {
                                    'vegetation_loss_pixels': region_data.get('change_count', 0) // 2,  # Estimate
                                    'total_pixels': 10000,  # Estimate
                                    'construction_activity_pct': corrected_result.development_score * 0.2  # Estimate
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
                                
                                logger.info(f"   💰 Financial: Rp {financial_projection.current_land_value_per_m2:,.0f}/m² "
                                          f"→ Rp {financial_projection.estimated_future_value_per_m2:,.0f}/m² "
                                          f"(ROI: {financial_projection.projected_roi_3yr:.1%})")
                                
                            except Exception as e:
                                logger.warning(f"   ⚠️ Financial projection failed for {region_name}: {e}")
                                financial_projection = None
                        # -------------------------------------------
                        
                        # NEW (v2.6-alpha): Calculate RVI if financial projection available
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
                                    logger.info(f"   📊 RVI: {rvi_data['rvi']:.3f} ({rvi_data['interpretation']})")
                                    
                            except Exception as e:
                                logger.warning(f"   ⚠️ RVI calculation failed for {region_name}: {e}")
                        # -------------------------------------------
                        
                        # Convert to format compatible with reporting system
                        dynamic_score = {
                            'region_name': region_name,
                            'satellite_changes': corrected_result.satellite_changes,
                            'change_percentage': region_data.get('change_percentage', 0),
                            'development_score': corrected_result.development_score,  # NEW: Base score from satellite
                            'current_price_per_m2': financial_projection.current_land_value_per_m2 if financial_projection else 0,
                            'price_trend_30d': corrected_result.price_trend_30d,
                            'market_heat': corrected_result.market_heat,
                            'infrastructure_score': corrected_result.infrastructure_score,
                            'infrastructure_multiplier': corrected_result.infrastructure_multiplier,  # NEW
                            'infrastructure_details': corrected_result.infrastructure_details,  # ✅ FIX: Include detailed breakdown
                            'market_multiplier': corrected_result.market_multiplier,  # NEW
                            'speculative_score': corrected_result.development_score,  # Map to development score
                            'final_investment_score': corrected_result.final_investment_score,
                            'overall_confidence': corrected_result.confidence_level,
                            'recommendation': corrected_result.recommendation,  # NEW
                            'rationale': corrected_result.rationale,  # NEW
                            'data_sources': {
                                **corrected_result.data_sources,  # Original string values (e.g., 'osm_live', 'live')
                                'availability': corrected_result.data_availability  # Add boolean availability for PDF generator
                            },
                            'analysis_type': 'corrected_satellite_centric',  # Mark as corrected!
                            'financial_projection': financial_projection,  # NEW: Financial metrics
                            'rvi_data': rvi_data  # NEW (v2.6-alpha): Relative Value Index
                        }
                        
                        dynamic_scored_regions.append(dynamic_score)
                        
                        # Log scoring results with satellite changes
                        logger.info(
                            f"✅ {region_name}: Score {corrected_result.final_investment_score:.1f}/100 "
                            f"({corrected_result.confidence_level:.0%} confidence) - "
                            f"{corrected_result.satellite_changes:,} changes detected - "
                            f"{corrected_result.recommendation}"
                        )
                        
                        # Log data availability
                        available = [k for k, v in corrected_result.data_availability.items() if v]
                        if len(available) < 3:
                            missing = [k for k, v in corrected_result.data_availability.items() if not v]
                            logger.info(f"   ⚠️ Missing data: {', '.join(missing)}")
                        
                    except Exception as e:
                        logger.error(f"❌ Scoring failed completely for {region_data['region_name']}: {e}")
                        logger.error(f"   This should not happen as dynamic scorer handles missing data gracefully")
                        # Don't add to scored regions if completely failed
                
                if dynamic_scored_regions:
                    # Generate investment report using dynamic scores
                    yogyakarta_report = self._generate_dynamic_investment_report(dynamic_scored_regions)
                    investment_report['yogyakarta_analysis'] = yogyakarta_report
                    
                    dynamic_count = sum(1 for r in dynamic_scored_regions if r.get('analysis_type') == 'dynamic_real_time')
                    total_opportunities = len(yogyakarta_report.get('buy_recommendations', []))
                    
                    logger.info(f"🎯 DYNAMIC MARKET Analysis: {dynamic_count}/{len(dynamic_scored_regions)} regions analyzed with real-time data")
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
        
        # Save to database if available
        if self.db_manager:
            try:
                # await self.db_manager.save_monitoring_results(results)  # Disabled
                logger.info("💾 Database functionality disabled")
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

    def _generate_dynamic_investment_report(self, dynamic_scored_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate investment report from dynamic scoring results.
        Regions are sorted by investment score (highest first).
        """
        buy_recommendations = []
        watch_list = []
        pass_list = []  # ✅ NEW: Track PASS regions (<25) so ALL scores appear in PDF
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
                'confidence_level': confidence,
                'current_price_per_m2': region_score.get('current_price_per_m2', 0),
                'price_trend_30d': price_trend,
                'market_heat': region_score.get('market_heat', 'unknown'),
                'infrastructure_score': region_score.get('infrastructure_score', 0),
                'infrastructure_details': region_score.get('infrastructure_details', {}),  # NEW: Detailed breakdown
                'satellite_changes': region_score.get('satellite_changes', 0),
                'data_sources': region_score.get('data_sources', {}),
                'analysis_type': region_score.get('analysis_type', 'dynamic'),
                'financial_projection': region_score.get('financial_projection')  # ✅ FIX: Include financial projection
            }
            
            # ✅ CORRECTED THRESHOLDS (based on proper 0-60 score range)
            # OLD: BUY ≥70, WATCH ≥50 (broken - everyone was a BUY!)
            # NEW: BUY ≥40, WATCH ≥25 (proper differentiation)
            if investment_score >= 40 and confidence >= 0.6:
                recommendation['recommendation'] = 'BUY'
                
                # Build concise rationale (truncated for PDF display)
                rationale_parts = []
                
                if price_trend > 5:
                    rationale_parts.append(f"Strong price momentum (+{price_trend:.1f}%)")
                elif price_trend < -3:
                    rationale_parts.append(f"Price correction ({price_trend:.1f}%)")
                else:
                    rationale_parts.append(f"Stable market ({price_trend:+.1f}%)")
                
                if region_score.get('satellite_changes', 0) > 10000:
                    rationale_parts.append(f"Very high development: {region_score.get('satellite_changes', 0):,} changes")
                elif region_score.get('satellite_changes', 0) > 5000:
                    rationale_parts.append(f"High development: {region_score.get('satellite_changes', 0):,} changes")
                elif region_score.get('satellite_changes', 0) > 1000:
                    rationale_parts.append(f"Moderate activity: {region_score.get('satellite_changes', 0):,} changes")
                
                # Combine with bullet separator for clean formatting
                recommendation['rationale'] = " • ".join(rationale_parts)
                
                buy_recommendations.append(recommendation)
            
            elif investment_score >= 25 and confidence >= 0.4:
                recommendation['recommendation'] = 'WATCH'
                recommendation['rationale'] = f"Moderate potential ({investment_score:.1f}/100) with monitoring advised. "
                
                if confidence < 0.6:
                    recommendation['rationale'] += f"Lower confidence ({confidence:.1%}) suggests careful evaluation. "
                
                watch_list.append(recommendation)
            
            else:
                # ✅ NEW: Capture PASS regions (<25) so ALL scores appear in PDF
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
        buy_recommendations.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        watch_list.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        pass_list.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        
        return {
            'buy_recommendations': buy_recommendations,
            'watch_list': watch_list,
            'pass_list': pass_list,  # ✅ NEW: Include PASS regions so PDF shows all scores
            'market_insights': market_insights,
            'summary': {
                'total_regions_analyzed': len(dynamic_scored_regions),
                'dynamic_analysis_count': len(dynamic_regions),
                'buy_recommendations_count': len(buy_recommendations),
                'watch_list_count': len(watch_list),
                'pass_list_count': len(pass_list),  # ✅ NEW: Track PASS count
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
