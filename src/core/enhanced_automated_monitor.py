"""
Enhanced Automated Weekly Monitoring System
CloudClearingAPI Phase 3: Strategic Corridor Investment Intelligence

This enhanced version integrates the national strategic corridors with 
automated weekly monitoring and investment analysis.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
import numpy as np

import ee

from .change_detector import ChangeDetector
from .config import get_config
from .speculative_scorer import SpeculativeScorer

# Import our enhanced strategic systems
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from national_corridors import get_national_manager, StrategicCorridor
    STRATEGIC_CORRIDORS_AVAILABLE = True
except ImportError:
    STRATEGIC_CORRIDORS_AVAILABLE = False
    logger.warning("Strategic corridors module not available - using legacy regions")

# Legacy region fallback
try:
    from ..regions import RegionManager
except ImportError:
    from regions import RegionManager

logger = logging.getLogger(__name__)

class EnhancedAutomatedMonitor:
    """
    Enhanced automated monitoring system with strategic corridor integration
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the enhanced automated monitor"""
        self.config = get_config()
        self.detector = ChangeDetector()
        self.speculative_scorer = SpeculativeScorer()
        
        # Initialize strategic corridor management
        if STRATEGIC_CORRIDORS_AVAILABLE:
            self.national_manager = get_national_manager()
            self.monitoring_mode = 'strategic_corridors'
            logger.info("🇮🇩 Strategic corridor monitoring activated")
        else:
            self.region_manager = RegionManager()
            self.monitoring_mode = 'legacy_regions'
            logger.info("📍 Legacy region monitoring activated")
        
        self.alert_config = {
            'critical_change_threshold': 50,  # Changes per week
            'development_ratio_threshold': 0.4,  # 40% development changes
            'vegetation_loss_threshold': 0.3,  # 30% vegetation loss
            'infrastructure_change_threshold': 5,  # Infrastructure changes
            'investment_score_threshold': 75.0  # Investment opportunity threshold
        }
        
        # Enhanced monitoring regions based on mode
        if self.monitoring_mode == 'strategic_corridors':
            self.monitoring_regions = self._get_strategic_corridor_regions()
        else:
            self.monitoring_regions = self._get_legacy_regions()
    
    def _get_strategic_corridor_regions(self) -> List[str]:
        """Get strategic corridor names for monitoring"""
        if not STRATEGIC_CORRIDORS_AVAILABLE:
            return []
        
        corridors = self.national_manager.corridors
        tier1_corridors = [c.name for c in corridors if c.investment_tier == 'tier1']
        tier2_corridors = [c.name for c in corridors if c.investment_tier == 'tier2']
        
        logger.info(f"📊 Strategic monitoring: {len(tier1_corridors)} Tier 1 + {len(tier2_corridors)} Tier 2 corridors")
        
        # Return Tier 1 first (higher priority), then Tier 2
        return tier1_corridors + tier2_corridors
    
    def _get_legacy_regions(self) -> List[str]:
        """Get legacy region names for monitoring"""
        return [
            'yogyakarta_urban', 'yogyakarta_periurban', 'sleman_north',
            'bantul_south', 'kulonprogo_west', 'gunungkidul_east',
            'magelang_corridor', 'solo_expansion', 'semarang_industrial',
            'surakarta_suburbs'
        ]
    
    async def run_weekly_monitoring(self) -> Dict[str, Any]:
        """Run comprehensive weekly monitoring with strategic analysis"""
        logger.info(f"🚀 Starting enhanced weekly monitoring ({self.monitoring_mode})")
        
        # Calculate date ranges for analysis
        end_date = datetime.now()
        week_b_start = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
        week_a_start = (end_date - timedelta(days=14)).strftime('%Y-%m-%d')
        
        monitoring_results = {
            'analysis_date': end_date.isoformat(),
            'monitoring_mode': self.monitoring_mode,
            'week_a_period': f"{week_a_start} to {week_b_start}",
            'week_b_period': f"{week_b_start} to {end_date.strftime('%Y-%m-%d')}",
            'regions_analyzed': [],
            'strategic_analysis': {},
            'total_changes': 0,
            'total_area_m2': 0,
            'alerts': [],
            'errors': []
        }
        
        # Analyze each monitoring region/corridor
        for region_name in self.monitoring_regions:
            try:
                logger.info(f"🔍 Analyzing: {region_name}")
                result = await self._analyze_region_or_corridor(
                    region_name, 
                    week_a_start, 
                    week_b_start
                )
                
                if result:
                    monitoring_results['regions_analyzed'].append(result)
                    monitoring_results['total_changes'] += result['change_count']
                    monitoring_results['total_area_m2'] += result['total_area_m2']
                    
                    # Check for alerts
                    alerts = self._check_enhanced_alerts(region_name, result)
                    monitoring_results['alerts'].extend(alerts)
                    
            except Exception as e:
                error_msg = f"Failed to analyze {region_name}: {str(e)}"
                logger.error(error_msg)
                monitoring_results['errors'].append(error_msg)
        
        # Generate enhanced investment analysis
        monitoring_results['strategic_analysis'] = self._generate_strategic_investment_analysis(monitoring_results)
        
        # Generate executive summary
        monitoring_results['executive_summary'] = self._generate_executive_summary(monitoring_results)
        
        # Save results
        await self._save_enhanced_monitoring_results(monitoring_results)
        
        # Send alerts if necessary
        if monitoring_results['alerts']:
            await self._send_enhanced_alerts(monitoring_results)
        
        logger.info(f"✅ Enhanced weekly monitoring completed: {monitoring_results['total_changes']} changes across {len(monitoring_results['regions_analyzed'])} regions")
        return monitoring_results
    
    async def _analyze_region_or_corridor(self, region_name: str, week_a: str, week_b: str) -> Optional[Dict[str, Any]]:
        """Analyze a region or strategic corridor for changes"""
        try:
            # Get boundaries based on monitoring mode
            if self.monitoring_mode == 'strategic_corridors':
                corridor = next((c for c in self.national_manager.corridors if c.name == region_name), None)
                if not corridor:
                    logger.warning(f"Strategic corridor not found: {region_name}")
                    return None
                
                west, south, east, north = corridor.bbox
                region_bbox = {'west': west, 'south': south, 'east': east, 'north': north}
                
                # Add strategic corridor metadata
                corridor_metadata = {
                    'investment_tier': corridor.investment_tier,
                    'focus': corridor.focus,
                    'island': corridor.island,
                    'risk_level': corridor.risk_level,
                    'infrastructure_catalysts': corridor.infrastructure_catalysts or [],
                    'expected_roi_years': corridor.expected_roi_years,
                    'market_maturity': corridor.market_maturity
                }
            else:
                region_bbox = self.region_manager.get_region_bbox(region_name)
                if not region_bbox:
                    logger.warning(f"No bbox found for region: {region_name}")
                    return None
                corridor_metadata = {}
            
            # Run satellite change detection
            changes = await self.detector.analyze_region_changes(
                bbox=region_bbox,
                period_a=week_a,
                period_b=week_b
            )
            
            if not changes:
                return None
            
            # Calculate area
            bbox_area_m2 = self._calculate_bbox_area(region_bbox)
            
            # Enhance with strategic scoring if available
            investment_score = 0
            if self.monitoring_mode == 'strategic_corridors':
                investment_score = self._calculate_strategic_investment_score(
                    corridor, changes, corridor_metadata
                )
            
            return {
                'region_name': region_name,
                'bbox': region_bbox,
                'change_count': len(changes.get('changes', [])),
                'total_area_m2': bbox_area_m2,
                'change_types': changes.get('change_types', {}),
                'changes': changes.get('changes', []),
                'investment_score': investment_score,
                'strategic_metadata': corridor_metadata,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {region_name}: {e}")
            return None
    
    def _calculate_strategic_investment_score(self, corridor: StrategicCorridor, 
                                           changes: Dict[str, Any], 
                                           metadata: Dict[str, Any]) -> float:
        """Calculate enhanced investment score for strategic corridors"""
        try:
            # Base corridor score
            base_score = corridor.base_investment_score() if hasattr(corridor, 'base_investment_score') else 50
            
            # Change activity bonus
            change_count = len(changes.get('changes', []))
            change_bonus = min(20, change_count * 0.5)  # Up to 20 points for activity
            
            # Development change bonus
            change_types = changes.get('change_types', {})
            development_changes = change_types.get('development', 0) + change_types.get('infrastructure', 0)
            development_bonus = min(15, development_changes * 2)  # Up to 15 points for development
            
            # Infrastructure catalyst bonus
            catalyst_bonus = len(corridor.infrastructure_catalysts or []) * 2  # 2 points per catalyst
            
            # Risk adjustment
            risk_multipliers = {
                'low': 1.0, 'medium': 0.95, 'medium-high': 0.9, 
                'high': 0.85, 'high-reward': 1.1
            }
            risk_mult = risk_multipliers.get(corridor.risk_level, 1.0)
            
            total_score = (base_score + change_bonus + development_bonus + catalyst_bonus) * risk_mult
            return min(100, max(0, total_score))
            
        except Exception as e:
            logger.warning(f"Could not calculate investment score: {e}")
            return 50  # Default score
    
    def _check_enhanced_alerts(self, region_name: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate enhanced alerts including investment opportunities"""
        alerts = []
        change_count = result['change_count']
        change_types = result.get('change_types', {})
        investment_score = result.get('investment_score', 0)
        metadata = result.get('strategic_metadata', {})
        
        # Critical change volume alert
        if change_count > self.alert_config['critical_change_threshold']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'high_activity',
                'region': region_name,
                'message': f"🚨 High change activity: {change_count} changes detected in {region_name}",
                'investment_relevance': 'High activity may indicate development pressure',
                'details': {
                    'change_count': change_count,
                    'investment_score': investment_score,
                    'tier': metadata.get('investment_tier', 'unknown')
                }
            })
        
        # Development hotspot alert
        if change_types and change_count > 0:
            development_ratio = (change_types.get('development', 0) + change_types.get('infrastructure', 0)) / change_count
            if development_ratio > self.alert_config['development_ratio_threshold']:
                alerts.append({
                    'level': 'MAJOR',
                    'type': 'development_hotspot',
                    'region': region_name,
                    'message': f"🏗️ Development hotspot: {development_ratio*100:.1f}% development activity in {region_name}",
                    'investment_relevance': 'Strong development signals suggest land value appreciation',
                    'details': {
                        'development_ratio': development_ratio,
                        'development_count': change_types.get('development', 0),
                        'infrastructure_count': change_types.get('infrastructure', 0),
                        'investment_score': investment_score
                    }
                })
        
        # Infrastructure development alert
        infra_changes = change_types.get('infrastructure', 0)
        if infra_changes > self.alert_config['infrastructure_change_threshold']:
            alerts.append({
                'level': 'MAJOR',
                'type': 'infrastructure_development',
                'region': region_name,
                'message': f"🛤️ Infrastructure development: {infra_changes} infrastructure changes in {region_name}",
                'investment_relevance': 'Infrastructure development drives land value appreciation',
                'details': {
                    'infrastructure_changes': infra_changes,
                    'catalysts': metadata.get('infrastructure_catalysts', []),
                    'investment_score': investment_score
                }
            })
        
        # High investment score alert
        if investment_score > self.alert_config['investment_score_threshold']:
            alerts.append({
                'level': 'INVESTMENT',
                'type': 'high_investment_score',
                'region': region_name,
                'message': f"💰 Investment opportunity: {region_name} scored {investment_score:.1f}/100",
                'investment_relevance': 'High investment score indicates strong opportunity',
                'details': {
                    'investment_score': investment_score,
                    'tier': metadata.get('investment_tier', 'unknown'),
                    'risk_level': metadata.get('risk_level', 'unknown'),
                    'roi_timeline': metadata.get('expected_roi_years', 'unknown')
                }
            })
        
        return alerts
    
    def _generate_strategic_investment_analysis(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced strategic investment analysis"""
        regions_analyzed = results['regions_analyzed']
        
        if not regions_analyzed:
            return {'status': 'no_data', 'message': 'No regions to analyze for investment'}
        
        # Sort regions by investment score
        scored_regions = [r for r in regions_analyzed if r.get('investment_score', 0) > 0]
        scored_regions.sort(key=lambda x: x.get('investment_score', 0), reverse=True)
        
        # Generate investment categories
        strong_buy = [r for r in scored_regions if r.get('investment_score', 0) > 80]
        buy = [r for r in scored_regions if 70 <= r.get('investment_score', 0) <= 80]
        accumulate = [r for r in scored_regions if 60 <= r.get('investment_score', 0) < 70]
        watch = [r for r in scored_regions if 50 <= r.get('investment_score', 0) < 60]
        
        # Calculate weekly change velocity
        weekly_activity = {}
        for region in regions_analyzed:
            weekly_activity[region['region_name']] = {
                'change_count': region['change_count'],
                'investment_score': region.get('investment_score', 0),
                'development_changes': region.get('change_types', {}).get('development', 0),
                'infrastructure_changes': region.get('change_types', {}).get('infrastructure', 0)
            }
        
        # Generate strategic insights
        strategic_insights = []
        
        if strong_buy:
            top_opportunity = strong_buy[0]
            strategic_insights.append(
                f"🎯 TOP OPPORTUNITY: {top_opportunity['region_name']} "
                f"(Score: {top_opportunity.get('investment_score', 0):.1f}/100) - "
                f"{top_opportunity['change_count']} changes detected this week"
            )
        
        if len([r for r in regions_analyzed if r.get('change_types', {}).get('infrastructure', 0) > 0]) > 0:
            infra_regions = [r['region_name'] for r in regions_analyzed 
                           if r.get('change_types', {}).get('infrastructure', 0) > 0]
            strategic_insights.append(
                f"🏗️ INFRASTRUCTURE ACTIVITY: Active development in {', '.join(infra_regions[:3])}"
            )
        
        # Market intelligence summary
        tier1_activity = len([r for r in regions_analyzed 
                            if r.get('strategic_metadata', {}).get('investment_tier') == 'tier1'])
        
        if tier1_activity > 0:
            strategic_insights.append(
                f"🚀 TIER 1 ACTIVITY: {tier1_activity} high-priority corridors showing change activity"
            )
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'monitoring_mode': self.monitoring_mode,
            'total_scored_regions': len(scored_regions),
            'investment_categories': {
                'strong_buy': len(strong_buy),
                'buy': len(buy), 
                'accumulate': len(accumulate),
                'watch': len(watch)
            },
            'strong_buy_opportunities': [
                {
                    'name': r['region_name'],
                    'score': r.get('investment_score', 0),
                    'changes': r['change_count'],
                    'tier': r.get('strategic_metadata', {}).get('investment_tier', 'unknown'),
                    'focus': r.get('strategic_metadata', {}).get('focus', 'unknown')
                }
                for r in strong_buy
            ],
            'buy_opportunities': [
                {
                    'name': r['region_name'],
                    'score': r.get('investment_score', 0),
                    'changes': r['change_count']
                }
                for r in buy
            ],
            'weekly_activity_summary': weekly_activity,
            'strategic_insights': strategic_insights,
            'average_investment_score': np.mean([r.get('investment_score', 0) for r in scored_regions]) if scored_regions else 0
        }
    
    def _generate_executive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for weekly report"""
        strategic_analysis = results.get('strategic_analysis', {})
        regions_count = len(results['regions_analyzed'])
        total_changes = results['total_changes']
        total_alerts = len(results['alerts'])
        
        # Key metrics
        strong_buy_count = strategic_analysis.get('investment_categories', {}).get('strong_buy', 0)
        avg_score = strategic_analysis.get('average_investment_score', 0)
        
        # Generate executive insights
        executive_insights = []
        
        if strong_buy_count > 0:
            executive_insights.append(f"🎯 {strong_buy_count} high-conviction investment opportunities identified")
        
        if total_changes > 100:
            executive_insights.append(f"📈 High market activity: {total_changes} total changes detected")
        elif total_changes > 50:
            executive_insights.append(f"📊 Moderate market activity: {total_changes} total changes detected")
        else:
            executive_insights.append(f"📉 Low market activity: {total_changes} total changes detected")
        
        if total_alerts > 0:
            critical_alerts = len([a for a in results['alerts'] if a['level'] == 'CRITICAL'])
            investment_alerts = len([a for a in results['alerts'] if a['level'] == 'INVESTMENT'])
            
            if critical_alerts > 0:
                executive_insights.append(f"🚨 {critical_alerts} critical development alerts require immediate attention")
            if investment_alerts > 0:
                executive_insights.append(f"💰 {investment_alerts} investment opportunities flagged for consideration")
        
        # Market status
        if avg_score > 75:
            market_status = "🟢 STRONG - Multiple high-conviction opportunities"
        elif avg_score > 60:
            market_status = "🟡 MODERATE - Selective opportunities available"
        else:
            market_status = "🔴 WEAK - Limited opportunities, focus on monitoring"
        
        return {
            'analysis_date': results['analysis_date'],
            'monitoring_mode': results['monitoring_mode'],
            'regions_monitored': regions_count,
            'total_changes': total_changes,
            'total_alerts': total_alerts,
            'market_status': market_status,
            'average_investment_score': avg_score,
            'high_conviction_opportunities': strong_buy_count,
            'executive_insights': executive_insights,
            'top_opportunity': strategic_analysis.get('strong_buy_opportunities', [{}])[0] if strategic_analysis.get('strong_buy_opportunities') else None,
            'strategic_insights': strategic_analysis.get('strategic_insights', [])
        }
    
    async def _save_enhanced_monitoring_results(self, results: Dict[str, Any]):
        """Save enhanced monitoring results with strategic analysis"""
        output_dir = Path('./output/monitoring/strategic')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save comprehensive results
        filename = output_dir / f"strategic_monitoring_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save executive summary separately
        exec_summary_file = output_dir / f"executive_summary_{timestamp}.json"
        with open(exec_summary_file, 'w') as f:
            json.dump(results['executive_summary'], f, indent=2, default=str)
        
        logger.info(f"📁 Enhanced monitoring results saved to: {filename}")
        logger.info(f"📋 Executive summary saved to: {exec_summary_file}")
    
    async def _send_enhanced_alerts(self, results: Dict[str, Any]):
        """Send enhanced alerts with investment intelligence"""
        alerts = results['alerts']
        executive_summary = results['executive_summary']
        
        # Group alerts by type
        critical_alerts = [a for a in alerts if a['level'] == 'CRITICAL']
        investment_alerts = [a for a in alerts if a['level'] == 'INVESTMENT']
        major_alerts = [a for a in alerts if a['level'] == 'MAJOR']
        
        # Generate alert summary
        alert_summary = [
            f"🇮🇩 INDONESIA STRATEGIC CORRIDOR MONITORING ALERT",
            f"Analysis Date: {executive_summary['analysis_date'][:10]}",
            f"Market Status: {executive_summary['market_status']}",
            ""
        ]
        
        if critical_alerts:
            alert_summary.append("🚨 CRITICAL ALERTS:")
            for alert in critical_alerts[:3]:  # Top 3
                alert_summary.append(f"  • {alert['message']}")
            alert_summary.append("")
        
        if investment_alerts:
            alert_summary.append("💰 INVESTMENT OPPORTUNITIES:")
            for alert in investment_alerts[:3]:  # Top 3
                alert_summary.append(f"  • {alert['message']}")
            alert_summary.append("")
        
        if executive_summary['strategic_insights']:
            alert_summary.append("🎯 STRATEGIC INSIGHTS:")
            for insight in executive_summary['strategic_insights'][:3]:
                alert_summary.append(f"  • {insight}")
        
        alert_message = "\n".join(alert_summary)
        
        # Log the alert (in production, this would send to Slack/email/etc.)
        logger.info("📧 STRATEGIC ALERT GENERATED:")
        logger.info(alert_message)
        
        # TODO: Implement actual alert sending (Slack, email, webhook)
        return alert_message
    
    def _calculate_bbox_area(self, bbox: Dict[str, float]) -> float:
        """Calculate approximate area of bounding box in square meters"""
        west, south, east, north = bbox['west'], bbox['south'], bbox['east'], bbox['north']
        
        # Convert to approximate area (rough calculation)
        width_km = (east - west) * 111.32 * np.cos(np.radians((south + north) / 2))
        height_km = (north - south) * 110.54
        area_km2 = abs(width_km * height_km)
        area_m2 = area_km2 * 1_000_000  # Convert to square meters
        
        return area_m2

# Global instance for easy access
_enhanced_monitor = None

def get_enhanced_monitor() -> EnhancedAutomatedMonitor:
    """Get the global enhanced monitor instance"""
    global _enhanced_monitor
    if _enhanced_monitor is None:
        _enhanced_monitor = EnhancedAutomatedMonitor()
    return _enhanced_monitor

async def run_strategic_weekly_monitoring():
    """Run the strategic weekly monitoring system"""
    monitor = get_enhanced_monitor()
    return await monitor.run_weekly_monitoring()

if __name__ == "__main__":
    # Run the monitoring system
    async def main():
        results = await run_strategic_weekly_monitoring()
        
        print("🇮🇩 STRATEGIC WEEKLY MONITORING COMPLETE")
        print("="*50)
        print(f"Market Status: {results['executive_summary']['market_status']}")
        print(f"Total Changes: {results['executive_summary']['total_changes']}")
        print(f"High-Conviction Opportunities: {results['executive_summary']['high_conviction_opportunities']}")
        
        if results['executive_summary']['strategic_insights']:
            print("\n🎯 KEY INSIGHTS:")
            for insight in results['executive_summary']['strategic_insights']:
                print(f"  • {insight}")
    
    asyncio.run(main())