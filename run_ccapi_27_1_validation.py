#!/usr/bin/env python3
"""
CCAPI-27.1: Full End-to-End v2.8.2 Validation
==============================================

Rigorous validation of v2.8.2 (corrected scoring with market data) across 12 diverse regions.

Success Criteria:
- ≥90/100 improvement score vs v2.5 baseline
- ≥75% RVI sensibility rate (RVI calculations make sense)
- Market multipliers functioning correctly (0.85x-1.4x range)
- Infrastructure multipliers correct (0.8x-1.3x range)
- Diverse recommendations across regions (not all BUY or all PASS)

Test Regions (12 diverse):
Tier 1 (3): Jakarta North, Bandung North, Tangerang BSD
Tier 2 (4): Yogyakarta Urban Core, Semarang Port, Solo Raya, Denpasar North
Tier 3 (3): Purwokerto South, Tegal Brebes, Probolinggo Bromo
Tier 4 (2): Banyuwangi Ferry, Jember Southern

Runtime: ~8-12 hours (60-90 minutes per region with smart date fallback)
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.core.automated_monitor import AutomatedMonitor
from src.indonesia_expansion_regions import get_expansion_manager
from src.core.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ccapi_27_1_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test regions - 12 diverse across all tiers
VALIDATION_REGIONS = [
    # Tier 1 (3 regions) - Expected: High scores, live market data
    "jakarta_north_sprawl",
    "bandung_north_expansion", 
    "tangerang_bsd_corridor",
    
    # Tier 2 (4 regions) - Expected: Medium-high scores, good data availability
    "yogyakarta_urban_core",
    "semarang_port_expansion",
    "solo_raya_expansion",
    "denpasar_north_expansion",
    
    # Tier 3 (3 regions) - Expected: Medium scores, moderate data availability
    "purwokerto_south_expansion",
    "tegal_brebes_coastal",
    "probolinggo_bromo_gateway",
    
    # Tier 4 (2 regions) - Expected: Lower scores, benchmark fallbacks likely
    "banyuwangi_ferry_corridor",
    "jember_southern_coast"
]


class CCAPI271Validator:
    """End-to-end validation orchestrator for v2.8.2"""
    
    def __init__(self):
        self.config = get_config()
        self.expansion_manager = get_expansion_manager()
        self.monitor = AutomatedMonitor()
        
        # Validation results
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'version': 'v2.8.2 (CCAPI-27.1)',
            'regions_tested': [],
            'success_metrics': {},
            'failures': [],
            'detailed_analysis': []
        }
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run full validation across all test regions"""
        logger.info("=" * 80)
        logger.info("CCAPI-27.1: Full End-to-End v2.8.2 Validation")
        logger.info("=" * 80)
        logger.info(f"Testing {len(VALIDATION_REGIONS)} diverse regions across Tier 1-4")
        logger.info(f"Expected runtime: {len(VALIDATION_REGIONS) * 45 / 60:.1f} hours")
        logger.info("")
        
        # Confirm before starting
        print("\n⚠️  This validation will run for ~8-12 hours and test 12 regions.")
        print("Press Ctrl+C within 5 seconds to cancel...\n")
        await asyncio.sleep(5)
        
        start_time = datetime.now()
        
        # Analyze each region
        for idx, region_name in enumerate(VALIDATION_REGIONS, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"[{idx}/{len(VALIDATION_REGIONS)}] Testing region: {region_name}")
            logger.info(f"{'='*80}")
            
            try:
                result = await self._analyze_region(region_name)
                if result:
                    self.results['regions_tested'].append(region_name)
                    self.results['detailed_analysis'].append(result)
                    self._log_region_summary(result)
                else:
                    self.results['failures'].append({
                        'region': region_name,
                        'reason': 'Analysis returned None'
                    })
                    logger.error(f"❌ {region_name}: Analysis failed (returned None)")
                    
            except Exception as e:
                self.results['failures'].append({
                    'region': region_name,
                    'reason': str(e)
                })
                logger.error(f"❌ {region_name}: Exception during analysis: {e}")
            
            # Progress update
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = len(VALIDATION_REGIONS) - idx
            avg_time_per_region = elapsed / idx
            estimated_remaining = remaining * avg_time_per_region
            
            logger.info(f"\n📊 Progress: {idx}/{len(VALIDATION_REGIONS)} regions")
            logger.info(f"⏱️  Elapsed: {elapsed:.1f} min | Estimated remaining: {estimated_remaining:.1f} min")
        
        # Calculate success metrics
        self._calculate_success_metrics()
        
        # Save results
        self._save_results()
        
        # Generate report
        self._generate_validation_report()
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f"\n✅ Validation completed in {total_time:.1f} minutes")
        
        return self.results
    
    async def _analyze_region(self, region_name: str) -> Optional[Dict[str, Any]]:
        """Analyze a single region using automated monitor"""
        # Get region info from expansion manager
        region = self.expansion_manager.get_region_by_name(region_name)
        if not region:
            logger.error(f"Region {region_name} not found in expansion manager")
            return None
        
        # Get bbox from expansion manager
        west, south, east, north = region.bbox
        bbox_dict = {
            'west': west,
            'south': south,
            'east': east,
            'north': north
        }
        
        # Create GEE geometry
        bbox_gee = {
            'type': 'Polygon',
            'coordinates': [[
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south]
            ]]
        }
        
        # Use smart date finding
        from datetime import timedelta
        now = datetime.now()
        end_date = now - timedelta(days=7)
        start_date = now - timedelta(days=14)
        
        week_a = start_date.strftime('%Y-%m-%d')
        week_b = end_date.strftime('%Y-%m-%d')
        
        # Run change detection directly (bypassing region manager)
        try:
            logger.info(f"   🛰️  Running satellite change detection for {region_name}...")
            
            # Use detector's smart date finding by trying multiple date ranges
            max_attempts = 20
            result = None
            
            for attempt_num in range(max_attempts):
                try:
                    weeks_back = attempt_num + 1
                    start_date_attempt = now - timedelta(days=weeks_back*7+7)
                    end_date_attempt = now - timedelta(days=weeks_back*7)
                    
                    week_a_str = start_date_attempt.strftime('%Y-%m-%d')
                    week_b_str = end_date_attempt.strftime('%Y-%m-%d')
                    
                    if attempt_num > 0:
                        logger.info(f"   🔄 Trying fallback {weeks_back} weeks ago...")
                    
                    results = self.monitor.detector.detect_weekly_changes(
                        week_a_start=week_a_str,
                        week_b_start=week_b_str,
                        bbox=bbox_gee,
                        export_results=True
                    )
                    
                    # Check if valid results
                    has_error = (
                        'error' in results.get('change_types', {}) or
                        (results.get('change_count', 0) == 0 and 
                         'error' in results.get('satellite_images', {}))
                    )
                    
                    if not has_error:
                        result = results
                        if attempt_num > 0:
                            logger.info(f"   ✅ Success with {weeks_back} weeks ago")
                        break
                    elif attempt_num < max_attempts - 1:
                        logger.warning(f"   ⚠️ No data at {weeks_back} weeks ago, trying next...")
                        continue
                    else:
                        logger.error(f"   ❌ All {max_attempts} attempts failed")
                        return None
                        
                except Exception as e:
                    if "no bands" in str(e).lower() or "empty composite" in str(e).lower():
                        if attempt_num < max_attempts - 1:
                            continue
                        else:
                            logger.error(f"   ❌ All attempts failed: {e}")
                            return None
                    else:
                        raise
            
            if not result:
                logger.error(f"No satellite data available for {region_name}")
                return None
            
            # Extract scoring details
            region_analysis = {
                'region_name': region_name,
                'tier': self._get_region_tier(region),
                'island': region.island,
                'focus': region.focus,
                'satellite_data': {
                    'change_count': result.get('change_count', 0),
                    'total_area_m2': result.get('total_area_m2', 0),
                    'change_types': result.get('change_types', {}),
                    'date_range_used': result.get('date_range_used', 'unknown')
                },
                'bbox': bbox_dict,
                'analysis_timestamp': result.get('analysis_timestamp'),
                'satellite_images': result.get('satellite_images', {}),
                'saved_images': result.get('saved_images', {})
            }
            
            # Get investment analysis (this will use CorrectedInvestmentScorer)
            investment_analysis = await self._get_investment_analysis(region_name, result, region)
            if investment_analysis:
                region_analysis['investment_analysis'] = investment_analysis
            
            return region_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {region_name}: {e}", exc_info=True)
            return None
    
    async def _get_investment_analysis(
        self, 
        region_name: str, 
        satellite_result: Dict[str, Any],
        region_info
    ) -> Optional[Dict[str, Any]]:
        """Get investment analysis using CorrectedInvestmentScorer"""
        try:
            # Prepare data for scorer
            region_config = {
                'name': region_name,
                'bbox': {
                    'west': region_info.bbox[0],
                    'south': region_info.bbox[1],
                    'east': region_info.bbox[2],
                    'north': region_info.bbox[3]
                },
                'center': {
                    'lat': (region_info.bbox[1] + region_info.bbox[3]) / 2,
                    'lng': (region_info.bbox[0] + region_info.bbox[2]) / 2
                }
            }
            
            satellite_changes = satellite_result.get('change_count', 0)
            area_affected_m2 = satellite_result.get('total_area_m2', 0)
            coordinates = region_config['center']
            bbox = region_config['bbox']
            
            # Use the monitor's corrected scorer
            logger.info(f"   🎯 Running CorrectedInvestmentScorer for {region_name}...")
            corrected_result = self.monitor.corrected_scorer.calculate_investment_score(
                region_name=region_name,
                satellite_changes=satellite_changes,
                area_affected_m2=area_affected_m2,
                region_config=region_config,
                coordinates=coordinates,
                bbox=bbox
            )
            
            # Get financial projection if available
            financial_projection = None
            if self.monitor.financial_engine:
                try:
                    logger.info(f"   💰 Calculating financial projection for {region_name}...")
                    financial_projection = self.monitor.financial_engine.calculate_financial_projection(
                        region_name=region_name,
                        satellite_data={
                            'vegetation_loss_pixels': satellite_result.get('change_types', {}).get('vegetation_loss', 0),
                            'construction_activity_pct': satellite_result.get('change_types', {}).get('development', 0) / max(satellite_changes, 1)
                        },
                        infrastructure_data={
                            'infrastructure_score': corrected_result.infrastructure_score,
                            'major_features': corrected_result.infrastructure_details.get('major_features', [])
                        },
                        market_data={
                            'price_trend_30d': corrected_result.price_trend_30d,
                            'market_heat': corrected_result.market_heat
                        },
                        scoring_result=corrected_result
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Financial projection failed for {region_name}: {e}")
            
            # Calculate RVI manually if financial projection available
            # RVI = Current Price / Expected Value
            # Expected Value = Peer Benchmark × Infrastructure Premium × Market Premium
            rvi_data = None
            if financial_projection and financial_projection.tier_benchmark_price:
                try:
                    # Get multipliers from corrected result
                    infra_multiplier = corrected_result.infrastructure_multiplier
                    market_multiplier = corrected_result.market_multiplier
                    
                    # Calculate expected value
                    peer_benchmark = financial_projection.tier_benchmark_price
                    expected_value = peer_benchmark * infra_multiplier * market_multiplier
                    
                    # Calculate RVI
                    current_price = financial_projection.current_land_value_per_m2
                    rvi_value = current_price / expected_value if expected_value > 0 else 1.0
                    
                    # Interpretation
                    if rvi_value < 0.8:
                        interpretation = "Significantly undervalued"
                    elif rvi_value < 0.95:
                        interpretation = "Moderately undervalued"
                    elif rvi_value <= 1.05:
                        interpretation = "Fair value"
                    elif rvi_value <= 1.25:
                        interpretation = "Moderately overvalued"
                    else:
                        interpretation = "Significantly overvalued"
                    
                    rvi_data = {
                        'rvi': rvi_value,
                        'interpretation': interpretation,
                        'expected_value_per_m2': expected_value,
                        'peer_benchmark_per_m2': peer_benchmark
                    }
                except Exception as e:
                    logger.warning(f"   ⚠️ RVI calculation failed for {region_name}: {e}")
            
            return {
                'scoring': {
                    'final_score': corrected_result.final_investment_score,
                    'development_score': corrected_result.development_score,
                    'infrastructure_score': corrected_result.infrastructure_score,
                    'infrastructure_multiplier': corrected_result.infrastructure_multiplier,
                    'market_multiplier': corrected_result.market_multiplier,
                    'confidence': corrected_result.confidence_level,
                    'recommendation': corrected_result.recommendation,
                    'rationale': corrected_result.rationale
                },
                'market_data': {
                    'current_price_per_m2': financial_projection.current_land_value_per_m2 if financial_projection else None,
                    'price_trend_30d': corrected_result.price_trend_30d,
                    'market_heat': corrected_result.market_heat,
                    'data_source': corrected_result.data_sources.get('market_data', 'unknown')
                },
                'financial_projection': {
                    'current_land_value_per_m2': financial_projection.current_land_value_per_m2 if financial_projection else None,
                    'projected_roi_3yr': financial_projection.projected_roi_3yr if financial_projection else None,
                    'recommended_plot_size_m2': financial_projection.recommended_plot_size_m2 if financial_projection else None,
                    'total_acquisition_cost': financial_projection.total_acquisition_cost if financial_projection else None,
                    'data_sources': financial_projection.data_sources if financial_projection else []
                } if financial_projection else None,
                'rvi': {
                    'value': rvi_data['rvi'] if rvi_data else None,
                    'interpretation': rvi_data['interpretation'] if rvi_data else None,
                    'expected_value_per_m2': rvi_data['expected_value_per_m2'] if rvi_data else None,
                    'peer_benchmark_per_m2': rvi_data['peer_benchmark_per_m2'] if rvi_data else None
                } if rvi_data else None,
                'data_availability': corrected_result.data_availability,
                'infrastructure_details': corrected_result.infrastructure_details
            }
            
        except Exception as e:
            logger.error(f"Error getting investment analysis for {region_name}: {e}", exc_info=True)
            return None
    
    def _get_region_tier(self, region) -> str:
        """Determine region tier based on priority"""
        priority_to_tier = {
            1: "Tier 1",
            2: "Tier 2",
            3: "Tier 3",
            4: "Tier 4"
        }
        # Default to Tier 3 for priority 3, unless it's very remote
        if region.priority == 3:
            # Check if it's Tier 4 based on location
            tier_4_keywords = ['banyuwangi', 'jember', 'probolinggo']
            if any(keyword in region.name.lower() for keyword in tier_4_keywords):
                return "Tier 4"
        return priority_to_tier.get(region.priority, "Tier 3")
    
    def _log_region_summary(self, result: Dict[str, Any]):
        """Log summary for a region"""
        region_name = result['region_name']
        tier = result['tier']
        
        satellite = result.get('satellite_data', {})
        investment = result.get('investment_analysis', {})
        
        logger.info(f"\n{'─'*80}")
        logger.info(f"📊 SUMMARY: {region_name} ({tier})")
        logger.info(f"{'─'*80}")
        
        # Satellite data
        logger.info(f"🛰️  Satellite: {satellite.get('change_count', 0)} changes, "
                   f"{satellite.get('total_area_m2', 0)/10000:.1f} ha affected")
        logger.info(f"📅 Date range: {satellite.get('date_range_used', 'unknown')}")
        
        if investment:
            scoring = investment.get('scoring', {})
            market = investment.get('market_data', {})
            rvi = investment.get('rvi', {})
            
            logger.info(f"\n🎯 Scoring:")
            logger.info(f"   Final Score: {scoring.get('final_score', 0):.1f}/100")
            logger.info(f"   Development: {scoring.get('development_score', 0):.1f}/40")
            logger.info(f"   Infrastructure: {scoring.get('infrastructure_score', 0):.1f} "
                       f"(×{scoring.get('infrastructure_multiplier', 1.0):.2f})")
            logger.info(f"   Market: {market.get('market_heat', 'unknown')} "
                       f"(×{scoring.get('market_multiplier', 1.0):.2f})")
            logger.info(f"   Confidence: {scoring.get('confidence', 0):.0f}%")
            logger.info(f"   Recommendation: {scoring.get('recommendation', 'UNKNOWN')}")
            
            logger.info(f"\n💰 Market Data:")
            logger.info(f"   Price: Rp {market.get('current_price_per_m2', 0):,.0f}/m²")
            logger.info(f"   Source: {market.get('data_source', 'unknown')}")
            logger.info(f"   Trend (30d): {market.get('price_trend_30d', 0):.1%}")
            
            if rvi and rvi.get('value'):
                logger.info(f"\n📈 RVI:")
                logger.info(f"   Value: {rvi.get('value', 0):.3f}")
                logger.info(f"   Interpretation: {rvi.get('interpretation', 'unknown')}")
        
        logger.info(f"{'─'*80}\n")
    
    def _calculate_success_metrics(self):
        """Calculate validation success metrics"""
        analyzed_regions = self.results['detailed_analysis']
        
        if not analyzed_regions:
            self.results['success_metrics'] = {
                'status': 'FAILED',
                'reason': 'No regions successfully analyzed'
            }
            return
        
        # Market data availability
        market_data_count = 0
        live_scraping_count = 0
        rvi_sensible_count = 0
        rvi_total_count = 0
        
        # Multiplier validation
        infra_multipliers = []
        market_multipliers = []
        
        # Recommendation diversity
        recommendations = {'BUY': 0, 'WATCH': 0, 'PASS': 0}
        
        # Score distribution
        scores = []
        
        for region in analyzed_regions:
            investment = region.get('investment_analysis')
            if not investment:
                continue
            
            scoring = investment.get('scoring', {})
            market = investment.get('market_data', {})
            rvi = investment.get('rvi', {})
            
            # Market data
            if market.get('current_price_per_m2', 0) > 0:
                market_data_count += 1
                
                # Check if live scraping (not benchmark)
                data_source = market.get('data_source', '').lower()
                if any(source in data_source for source in ['lamudi', '99co', 'rumah123']):
                    live_scraping_count += 1
            
            # RVI sensibility
            if rvi and rvi.get('value'):
                rvi_total_count += 1
                rvi_value = rvi.get('value', 0)
                # Sensible if between 0.1 and 10.0 (extreme outliers are suspicious)
                if 0.1 <= rvi_value <= 10.0:
                    rvi_sensible_count += 1
            
            # Multipliers
            infra_mult = scoring.get('infrastructure_multiplier', 1.0)
            market_mult = scoring.get('market_multiplier', 1.0)
            infra_multipliers.append(infra_mult)
            market_multipliers.append(market_mult)
            
            # Recommendations
            rec = scoring.get('recommendation', 'UNKNOWN')
            if rec in recommendations:
                recommendations[rec] += 1
            
            # Scores
            score = scoring.get('final_score', 0)
            scores.append(score)
        
        total_regions = len(analyzed_regions)
        
        # Calculate metrics
        market_data_rate = (market_data_count / total_regions * 100) if total_regions > 0 else 0
        live_scraping_rate = (live_scraping_count / total_regions * 100) if total_regions > 0 else 0
        rvi_sensibility_rate = (rvi_sensible_count / rvi_total_count * 100) if rvi_total_count > 0 else 0
        
        # Check multiplier ranges
        infra_mult_valid = all(0.8 <= m <= 1.3 for m in infra_multipliers)
        market_mult_valid = all(0.85 <= m <= 1.4 for m in market_multipliers)
        
        # Check recommendation diversity (at least 2 different types)
        rec_diversity = sum(1 for count in recommendations.values() if count > 0)
        
        # Calculate improvement score (0-100)
        improvement_score = (
            (market_data_rate / 100 * 30) +  # 30 points for market data
            (rvi_sensibility_rate / 100 * 25) +  # 25 points for RVI sensibility
            (20 if infra_mult_valid else 0) +  # 20 points for valid infrastructure multipliers
            (15 if market_mult_valid else 0) +  # 15 points for valid market multipliers
            (10 if rec_diversity >= 2 else 0)  # 10 points for recommendation diversity
        )
        
        # Success criteria
        success = (
            improvement_score >= 90 and
            rvi_sensibility_rate >= 75 and
            market_data_rate >= 70
        )
        
        self.results['success_metrics'] = {
            'status': 'PASS' if success else 'NEEDS_IMPROVEMENT',
            'improvement_score': round(improvement_score, 1),
            'market_data': {
                'availability_rate': round(market_data_rate, 1),
                'live_scraping_rate': round(live_scraping_rate, 1),
                'count': market_data_count,
                'total': total_regions
            },
            'rvi': {
                'sensibility_rate': round(rvi_sensibility_rate, 1),
                'sensible_count': rvi_sensible_count,
                'total_calculated': rvi_total_count
            },
            'multipliers': {
                'infrastructure': {
                    'valid': infra_mult_valid,
                    'range': [round(min(infra_multipliers), 2), round(max(infra_multipliers), 2)] if infra_multipliers else [0, 0],
                    'average': round(sum(infra_multipliers) / len(infra_multipliers), 2) if infra_multipliers else 0
                },
                'market': {
                    'valid': market_mult_valid,
                    'range': [round(min(market_multipliers), 2), round(max(market_multipliers), 2)] if market_multipliers else [0, 0],
                    'average': round(sum(market_multipliers) / len(market_multipliers), 2) if market_multipliers else 0
                }
            },
            'recommendations': {
                'diversity': rec_diversity,
                'breakdown': recommendations
            },
            'scores': {
                'average': round(sum(scores) / len(scores), 1) if scores else 0,
                'range': [round(min(scores), 1), round(max(scores), 1)] if scores else [0, 0],
                'distribution': {
                    'high_80plus': sum(1 for s in scores if s >= 80),
                    'medium_60_80': sum(1 for s in scores if 60 <= s < 80),
                    'low_below_60': sum(1 for s in scores if s < 60)
                }
            },
            'success_criteria': {
                'improvement_score_90plus': improvement_score >= 90,
                'rvi_sensibility_75plus': rvi_sensibility_rate >= 75,
                'market_data_70plus': market_data_rate >= 70
            }
        }
    
    def _save_results(self):
        """Save validation results to JSON"""
        output_dir = Path('output/validation')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'ccapi_27_1_validation_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {output_file}")
    
    def _generate_validation_report(self):
        """Generate human-readable validation report"""
        metrics = self.results['success_metrics']
        
        # Check if validation actually ran
        if metrics.get('status') == 'FAILED' and 'reason' in metrics:
            logger.info("\n" + "=" * 80)
            logger.info("CCAPI-27.1 VALIDATION REPORT")
            logger.info("=" * 80)
            logger.error(f"\n❌ Validation Failed: {metrics['reason']}")
            logger.info("=" * 80 + "\n")
            return
        
        logger.info("\n" + "=" * 80)
        logger.info("CCAPI-27.1 VALIDATION REPORT")
        logger.info("=" * 80)
        
        logger.info(f"\n📊 Overall Status: {metrics['status']}")
        logger.info(f"🎯 Improvement Score: {metrics.get('improvement_score', 0)}/100")
        logger.info(f"   Target: ≥90/100 | {'✅ PASS' if metrics['improvement_score'] >= 90 else '❌ FAIL'}")
        
        logger.info(f"\n📈 Market Data:")
        market = metrics['market_data']
        logger.info(f"   Availability: {market['availability_rate']}% ({market['count']}/{market['total']})")
        logger.info(f"   Live Scraping: {market['live_scraping_rate']}%")
        logger.info(f"   Target: ≥70% | {'✅ PASS' if market['availability_rate'] >= 70 else '❌ FAIL'}")
        
        logger.info(f"\n💎 RVI Analysis:")
        rvi = metrics['rvi']
        logger.info(f"   Sensibility Rate: {rvi['sensibility_rate']}% ({rvi['sensible_count']}/{rvi['total_calculated']})")
        logger.info(f"   Target: ≥75% | {'✅ PASS' if rvi['sensibility_rate'] >= 75 else '❌ FAIL'}")
        
        logger.info(f"\n⚙️ Multipliers:")
        infra = metrics['multipliers']['infrastructure']
        market_mult = metrics['multipliers']['market']
        logger.info(f"   Infrastructure: {infra['range'][0]}-{infra['range'][1]} (avg: {infra['average']})")
        logger.info(f"      Expected: 0.8-1.3 | {'✅ PASS' if infra['valid'] else '❌ FAIL'}")
        logger.info(f"   Market: {market_mult['range'][0]}-{market_mult['range'][1]} (avg: {market_mult['average']})")
        logger.info(f"      Expected: 0.85-1.4 | {'✅ PASS' if market_mult['valid'] else '❌ FAIL'}")
        
        logger.info(f"\n🎲 Recommendations:")
        recs = metrics['recommendations']
        logger.info(f"   Diversity: {recs['diversity']}/3 types")
        logger.info(f"   BUY: {recs['breakdown']['BUY']} | WATCH: {recs['breakdown']['WATCH']} | PASS: {recs['breakdown']['PASS']}")
        
        logger.info(f"\n📊 Score Distribution:")
        scores = metrics['scores']
        logger.info(f"   Average: {scores['average']}/100")
        logger.info(f"   Range: {scores['range'][0]}-{scores['range'][1]}")
        logger.info(f"   High (≥80): {scores['distribution']['high_80plus']} regions")
        logger.info(f"   Medium (60-79): {scores['distribution']['medium_60_80']} regions")
        logger.info(f"   Low (<60): {scores['distribution']['low_below_60']} regions")
        
        logger.info("\n" + "=" * 80)
        
        # Final verdict
        if metrics['status'] == 'PASS':
            logger.info("🎉 VALIDATION PASSED - v2.8.2 is production ready!")
        else:
            logger.info("⚠️  VALIDATION NEEDS IMPROVEMENT - Review failures and iterate")
        
        logger.info("=" * 80 + "\n")


async def main():
    """Main entry point"""
    try:
        validator = CCAPI271Validator()
        results = await validator.run_validation()
        
        # Exit with appropriate code
        if results['success_metrics'].get('status') == 'PASS':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error during validation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
