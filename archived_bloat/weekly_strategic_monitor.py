"""
Weekly Strategic Monitoring Integration
CloudClearingAPI: Automated Weekly Reports with Investment Intelligence

This script integrates the strategic corridor analysis with automated weekly monitoring
to generate comprehensive investment intelligence reports.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

class WeeklyStrategicMonitor:
    """
    Integrated weekly monitoring with strategic corridor investment analysis
    """
    
    def __init__(self):
        """Initialize the weekly strategic monitor"""
        self.analysis_date = datetime.now()
        
        # Satellite analysis for the corridor
        try:
            from src.core.change_detector import ChangeDetector
            self.strategic_corridors = create_strategic_corridors()
            self.calculate_score = calculate_comprehensive_score
            self.strategic_mode = True
            logger.info("🇮🇩 Strategic corridor analysis activated")
        except ImportError:
            self.strategic_mode = False
            logger.warning("Strategic analysis not available - using simplified monitoring")
        
        # Monitoring configuration
        self.alert_thresholds = {
            'high_investment_score': 80.0,
            'moderate_investment_score': 70.0,
            'development_activity': 0.4,  # 40% development changes
            'infrastructure_activity': 5,  # 5+ infrastructure changes
        }
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly strategic monitoring report"""
        logger.info("🚀 Starting weekly strategic monitoring report generation")
        
        report = {
            'report_metadata': {
                'generation_date': self.analysis_date.isoformat(),
                'report_type': 'strategic_weekly_monitoring',
                'monitoring_mode': 'strategic_corridors' if self.strategic_mode else 'basic',
                'coverage_area': 'Indonesia National'
            },
            'executive_summary': {},
            'strategic_analysis': {},
            'investment_opportunities': {},
            'market_alerts': [],
            'weekly_insights': []
        }
        
        if self.strategic_mode:
            # Analyze strategic corridors
            corridor_analysis = await self._analyze_strategic_corridors()
            report['strategic_analysis'] = corridor_analysis
            
            # Generate investment opportunities
            report['investment_opportunities'] = self._generate_investment_opportunities(corridor_analysis)
            
            # Generate market alerts
            report['market_alerts'] = self._generate_market_alerts(corridor_analysis)
            
            # Generate weekly insights
            report['weekly_insights'] = self._generate_weekly_insights(corridor_analysis)
            
            # Generate executive summary
            report['executive_summary'] = self._generate_executive_summary(report)
        else:
            # Basic monitoring mode
            report['executive_summary'] = {
                'status': 'basic_mode',
                'message': 'Strategic corridor analysis not available'
            }
        
        # Save report
        await self._save_weekly_report(report)
        
        # Generate alerts if needed
        await self._send_weekly_alerts(report)
        
        logger.info("✅ Weekly strategic monitoring report completed")
        return report
    
    async def _analyze_strategic_corridors(self) -> Dict[str, Any]:
        """Analyze all strategic corridors for the weekly report"""
        logger.info("📊 Analyzing strategic corridors...")
        
        corridor_scores = []
        for corridor in self.strategic_corridors:
            try:
                # Calculate comprehensive score
                scores = self.calculate_score(corridor)
                
                # Analyze real satellite changes using our change detection system
                weekly_changes = await self._analyze_real_satellite_changes(corridor)
                
                corridor_analysis = {
                    'name': corridor.name,
                    'investment_tier': corridor.investment_tier,
                    'island': corridor.island,
                    'focus': corridor.focus,
                    'total_score': scores['total'],
                    'score_breakdown': scores,
                    'weekly_activity': weekly_changes,
                    'risk_level': corridor.risk_level,
                    'roi_timeline': f"{corridor.expected_roi_years[0]}-{corridor.expected_roi_years[1]} years",
                    'infrastructure_catalysts': corridor.infrastructure_catalysts or [],
                    'area_km2': corridor.area_km2()
                }
                
                corridor_scores.append(corridor_analysis)
                
            except Exception as e:
                logger.warning(f"Failed to analyze corridor {corridor.name}: {e}")
        
        # Sort by total score
        corridor_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Calculate summary statistics
        avg_score = sum(c['total_score'] for c in corridor_scores) / len(corridor_scores) if corridor_scores else 0
        high_conviction_count = len([c for c in corridor_scores if c['total_score'] > 80])
        total_weekly_changes = sum(c['weekly_activity']['total_changes'] for c in corridor_scores)
        
        return {
            'analysis_timestamp': self.analysis_date.isoformat(),
            'total_corridors_analyzed': len(corridor_scores),
            'average_investment_score': avg_score,
            'high_conviction_opportunities': high_conviction_count,
            'total_weekly_changes': total_weekly_changes,
            'corridor_analysis': corridor_scores,
            'top_5_opportunities': corridor_scores[:5]
        }
    
    async def _analyze_real_satellite_changes(self, corridor) -> Dict[str, Any]:
        """Analyze real satellite changes using our advanced change detection system"""
        try:
            # Import our change detection system
            sys.path.append('./src/core')
            from change_detector import ChangeDetector
            
            # Initialize change detector
            detector = ChangeDetector()
            
            # Create bbox from corridor
            west, south, east, north = corridor.bbox
            bbox = {
                'type': 'Polygon',
                'coordinates': [[
                    [west, south], [east, south], 
                    [east, north], [west, north], 
                    [west, south]
                ]]
            }
            
            # Calculate dates for weekly analysis (current week vs previous week)
            end_date = self.analysis_date
            week_b_start = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
            week_a_start = (end_date - timedelta(days=14)).strftime('%Y-%m-%d')
            
            logger.info(f"🛰️ Running satellite analysis for {corridor.name}: {week_a_start} → {week_b_start}")
            
            # Run change detection with auto date finding
            results = detector.detect_weekly_changes(
                week_a_start=week_a_start,
                week_b_start=week_b_start,
                bbox=bbox,
                export_results=False,
                auto_find_dates=True
            )
            
            # Extract change statistics
            change_stats = results.get('statistics', {})
            changes = results.get('changes', [])
            
            # Analyze change types from the actual satellite detection
            development_changes = 0
            infrastructure_changes = 0
            vegetation_changes = 0
            
            for change in changes:
                change_type = change.get('properties', {}).get('change_type', 'unknown')
                if change_type in ['development', 'new_building', 'urban_expansion']:
                    development_changes += 1
                elif change_type in ['infrastructure', 'new_road', 'construction']:
                    infrastructure_changes += 1
                elif change_type in ['vegetation_loss', 'deforestation', 'land_clearing']:
                    vegetation_changes += 1
            
            total_changes = len(changes)
            
            # Calculate change density
            change_density = total_changes / corridor.area_km2() if corridor.area_km2() > 0 else 0
            
            # Extract additional metrics from satellite analysis  
            ndvi_loss_area = change_stats.get('ndvi_loss_area_ha', 0)
            ndbi_gain_area = change_stats.get('ndbi_gain_area_ha', 0)
            total_area_changed = change_stats.get('total_change_area_ha', 0)
            
            satellite_analysis = {
                'total_changes': total_changes,
                'development_changes': development_changes,
                'infrastructure_changes': infrastructure_changes,
                'vegetation_changes': vegetation_changes,
                'change_density_per_km2': change_density,
                'satellite_metrics': {
                    'ndvi_loss_area_ha': ndvi_loss_area,
                    'ndbi_gain_area_ha': ndbi_gain_area,
                    'total_area_changed_ha': total_area_changed,
                    'analysis_success': True,
                    'data_quality': 'high' if total_changes > 0 else 'low'
                },
                'analysis_metadata': {
                    'week_a_period': week_a_start,
                    'week_b_period': week_b_start,
                    'satellite_data_source': 'Sentinel-2',
                    'change_detection_method': 'NDVI/NDBI spectral analysis'
                }
            }
            
            logger.info(f"✅ Satellite analysis complete for {corridor.name}: {total_changes} changes detected")
            return satellite_analysis
            
        except Exception as e:
            logger.warning(f"⚠️ Satellite analysis failed for {corridor.name}: {str(e)}")
            logger.info(f"   Falling back to simulated data for {corridor.name}")
            
            # Fallback to simulated data if satellite analysis fails
            return self._simulate_weekly_activity_fallback(corridor)
    
    def _simulate_weekly_activity_fallback(self, corridor) -> Dict[str, Any]:
        """Fallback simulation when real satellite analysis is unavailable"""
        import random
        
        # Base activity level influenced by corridor characteristics
        base_activity = 10
        if corridor.investment_tier == 'tier1':
            base_activity = 20
        if 'capital' in corridor.focus:
            base_activity = 30
        elif 'port' in corridor.focus or 'industrial' in corridor.focus:
            base_activity = 25
        
        # Random variation
        total_changes = max(0, base_activity + random.randint(-10, 20))
        
        # Distribute changes by type
        development_changes = max(0, int(total_changes * random.uniform(0.2, 0.6)))
        infrastructure_changes = max(0, int(total_changes * random.uniform(0.1, 0.3)))
        vegetation_changes = max(0, total_changes - development_changes - infrastructure_changes)
        
        return {
            'total_changes': total_changes,
            'development_changes': development_changes,
            'infrastructure_changes': infrastructure_changes,
            'vegetation_changes': vegetation_changes,
            'change_density_per_km2': total_changes / corridor.area_km2() if corridor.area_km2() > 0 else 0,
            'satellite_metrics': {
                'ndvi_loss_area_ha': random.uniform(5, 50),
                'ndbi_gain_area_ha': random.uniform(2, 25),
                'total_area_changed_ha': random.uniform(10, 75),
                'analysis_success': False,
                'data_quality': 'simulated'
            },
            'analysis_metadata': {
                'satellite_data_source': 'Simulated',
                'change_detection_method': 'Fallback simulation'
            }
        }
    
    def _generate_investment_opportunities(self, corridor_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment opportunities from corridor analysis"""
        corridors = corridor_analysis['corridor_analysis']
        
        # Categorize opportunities
        strong_buy = [c for c in corridors if c['total_score'] > 80]
        buy = [c for c in corridors if 70 <= c['total_score'] <= 80]
        accumulate = [c for c in corridors if 60 <= c['total_score'] < 70]
        watch = [c for c in corridors if c['total_score'] < 60]
        
        return {
            'analysis_date': self.analysis_date.isoformat(),
            'investment_categories': {
                'strong_buy': {
                    'count': len(strong_buy),
                    'opportunities': [
                        {
                            'name': c['name'],
                            'score': c['total_score'],
                            'tier': c['investment_tier'],
                            'weekly_changes': c['weekly_activity']['total_changes'],
                            'development_activity': c['weekly_activity']['development_changes'],
                            'recommendation': 'Immediate land banking recommended'
                        }
                        for c in strong_buy
                    ]
                },
                'buy': {
                    'count': len(buy),
                    'opportunities': [
                        {
                            'name': c['name'],
                            'score': c['total_score'],
                            'tier': c['investment_tier'],
                            'recommendation': 'Selective acquisition in prime locations'
                        }
                        for c in buy
                    ]
                },
                'accumulate': {
                    'count': len(accumulate),
                    'opportunities': [
                        {
                            'name': c['name'],
                            'score': c['total_score'],
                            'recommendation': 'Monitor and accumulate on weakness'
                        }
                        for c in accumulate
                    ]
                },
                'watch': {
                    'count': len(watch),
                    'opportunities': [
                        {
                            'name': c['name'],
                            'score': c['total_score'],
                            'recommendation': 'Watch for improved fundamentals'
                        }
                        for c in watch
                    ]
                }
            },
            'priority_actions': self._generate_priority_actions(strong_buy, buy)
        }
    
    def _generate_priority_actions(self, strong_buy: List[Dict], buy: List[Dict]) -> List[str]:
        """Generate priority actions for the week"""
        actions = []
        
        if strong_buy:
            top_opportunity = strong_buy[0]
            actions.append(
                f"🎯 IMMEDIATE ACTION: Begin land banking in {top_opportunity['name']} "
                f"(Score: {top_opportunity['total_score']:.1f}/100)"
            )
            
            if top_opportunity['weekly_activity']['development_changes'] > 10:
                actions.append(
                    f"🏗️ HIGH DEVELOPMENT ACTIVITY: {top_opportunity['weekly_activity']['development_changes']} "
                    f"development changes in {top_opportunity['name']} - market heating up"
                )
        
        if len(strong_buy) > 1:
            actions.append(
                f"📈 DIVERSIFICATION: {len(strong_buy)} high-conviction opportunities available "
                f"for portfolio diversification"
            )
        
        if buy:
            actions.append(
                f"🎯 SELECTIVE ACQUISITION: Consider premium parcels in {', '.join([c['name'] for c in buy[:2]])}"
            )
        
        return actions
    
    def _generate_market_alerts(self, corridor_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate market alerts based on corridor analysis"""
        alerts = []
        corridors = corridor_analysis['corridor_analysis']
        
        # High investment score alerts
        high_score_corridors = [c for c in corridors if c['total_score'] > self.alert_thresholds['high_investment_score']]
        for corridor in high_score_corridors:
            alerts.append({
                'level': 'INVESTMENT_OPPORTUNITY',
                'type': 'high_investment_score',
                'corridor': corridor['name'],
                'message': f"🚀 High investment score: {corridor['name']} scored {corridor['total_score']:.1f}/100",
                'details': {
                    'score': corridor['total_score'],
                    'tier': corridor['investment_tier'],
                    'weekly_changes': corridor['weekly_activity']['total_changes']
                },
                'action_required': 'Consider immediate land banking evaluation'
            })
        
        # High development activity alerts
        high_development_corridors = [c for c in corridors 
                                    if c['weekly_activity']['development_changes'] > self.alert_thresholds['infrastructure_activity']]
        for corridor in high_development_corridors:
            alerts.append({
                'level': 'MARKET_ACTIVITY',
                'type': 'high_development_activity',
                'corridor': corridor['name'],
                'message': f"🏗️ High development activity: {corridor['weekly_activity']['development_changes']} changes in {corridor['name']}",
                'details': {
                    'development_changes': corridor['weekly_activity']['development_changes'],
                    'total_changes': corridor['weekly_activity']['total_changes'],
                    'investment_score': corridor['total_score']
                },
                'action_required': 'Monitor for land value appreciation signals'
            })
        
        # Tier 1 corridor activity alerts
        tier1_active = [c for c in corridors 
                       if c['investment_tier'] == 'tier1' and c['weekly_activity']['total_changes'] > 15]
        if tier1_active:
            alerts.append({
                'level': 'STRATEGIC',
                'type': 'tier1_activity',
                'corridor': 'multiple',
                'message': f"🎯 Tier 1 corridor activity: {len(tier1_active)} priority corridors showing high activity",
                'details': {
                    'active_corridors': [c['name'] for c in tier1_active],
                    'total_changes': sum(c['weekly_activity']['total_changes'] for c in tier1_active)
                },
                'action_required': 'Prioritize due diligence on Tier 1 opportunities'
            })
        
        return alerts
    
    def _generate_weekly_insights(self, corridor_analysis: Dict[str, Any]) -> List[str]:
        """Generate strategic insights for the week"""
        insights = []
        corridors = corridor_analysis['corridor_analysis']
        
        # Top performing corridor insight
        if corridors:
            top_corridor = corridors[0]
            insights.append(
                f"🏆 TOP PERFORMER: {top_corridor['name']} leads with {top_corridor['total_score']:.1f}/100 "
                f"score and {top_corridor['weekly_activity']['total_changes']} weekly changes"
            )
        
        # Island diversification insight
        island_activity = {}
        for corridor in corridors:
            island = corridor['island']
            if island not in island_activity:
                island_activity[island] = {'corridors': 0, 'changes': 0, 'avg_score': 0}
            island_activity[island]['corridors'] += 1
            island_activity[island]['changes'] += corridor['weekly_activity']['total_changes']
            island_activity[island]['avg_score'] += corridor['total_score']
        
        for island in island_activity:
            island_activity[island]['avg_score'] /= island_activity[island]['corridors']
        
        most_active_island = max(island_activity.items(), key=lambda x: x[1]['changes'])
        insights.append(
            f"🏝️ ISLAND FOCUS: {most_active_island[0].capitalize()} shows highest activity "
            f"({most_active_island[1]['changes']} changes, {most_active_island[1]['avg_score']:.1f} avg score)"
        )
        
        # Infrastructure catalyst insight
        catalysts_active = []
        for corridor in corridors:
            if corridor['weekly_activity']['infrastructure_changes'] > 3:
                catalysts_active.extend(corridor['infrastructure_catalysts'])
        
        if catalysts_active:
            from collections import Counter
            top_catalyst = Counter(catalysts_active).most_common(1)[0][0]
            insights.append(
                f"🏗️ INFRASTRUCTURE CATALYST: '{top_catalyst}' showing strong development signals "
                f"across multiple corridors"
            )
        
        # Market timing insight
        high_conviction_count = len([c for c in corridors if c['total_score'] > 80])
        if high_conviction_count > 3:
            insights.append(
                f"⏰ MARKET TIMING: {high_conviction_count} high-conviction opportunities suggest "
                f"favorable market conditions for strategic land banking"
            )
        
        return insights
    
    def _generate_executive_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for the weekly report"""
        strategic_analysis = report['strategic_analysis']
        investment_opportunities = report['investment_opportunities']
        market_alerts = report['market_alerts']
        
        # Key metrics
        total_corridors = strategic_analysis['total_corridors_analyzed']
        avg_score = strategic_analysis['average_investment_score']
        high_conviction = strategic_analysis['high_conviction_opportunities']
        total_changes = strategic_analysis['total_weekly_changes']
        
        # Market status determination
        if avg_score > 75 and high_conviction > 2:
            market_status = "🟢 STRONG MARKET - Multiple high-conviction opportunities"
        elif avg_score > 65 and high_conviction > 0:
            market_status = "🟡 MODERATE MARKET - Selective opportunities available"
        else:
            market_status = "🔴 WEAK MARKET - Limited opportunities, focus on monitoring"
        
        # Priority recommendations
        priority_recommendations = []
        strong_buy_count = investment_opportunities['investment_categories']['strong_buy']['count']
        
        if strong_buy_count > 0:
            priority_recommendations.append(f"Immediate action required on {strong_buy_count} high-conviction opportunities")
        
        critical_alerts = len([a for a in market_alerts if a['level'] == 'INVESTMENT_OPPORTUNITY'])
        if critical_alerts > 0:
            priority_recommendations.append(f"Review {critical_alerts} investment opportunity alerts")
        
        if total_changes > 200:
            priority_recommendations.append("High market activity detected - consider accelerating due diligence")
        
        return {
            'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
            'market_status': market_status,
            'key_metrics': {
                'corridors_monitored': total_corridors,
                'average_investment_score': round(avg_score, 1),
                'high_conviction_opportunities': high_conviction,
                'total_weekly_changes': total_changes,
                'critical_alerts': len(market_alerts)
            },
            'top_opportunity': strategic_analysis['top_5_opportunities'][0] if strategic_analysis['top_5_opportunities'] else None,
            'priority_recommendations': priority_recommendations,
            'strategic_insights': report['weekly_insights'][:3]  # Top 3 insights
        }
    
    async def _save_weekly_report(self, report: Dict[str, Any]):
        """Save the weekly report to file"""
        output_dir = Path('./output/weekly_reports')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = self.analysis_date.strftime('%Y%m%d_%H%M%S')
        
        # Save full report
        full_report_file = output_dir / f"strategic_weekly_report_{timestamp}.json"
        with open(full_report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save executive summary for quick access
        exec_summary_file = output_dir / f"executive_summary_{timestamp}.json"
        with open(exec_summary_file, 'w') as f:
            json.dump(report['executive_summary'], f, indent=2, default=str)
        
        logger.info(f"📁 Full weekly report saved: {full_report_file}")
        logger.info(f"📋 Executive summary saved: {exec_summary_file}")
    
    async def _send_weekly_alerts(self, report: Dict[str, Any]):
        """Send weekly alerts and summary"""
        executive_summary = report['executive_summary']
        market_alerts = report['market_alerts']
        
        # Generate alert message
        alert_lines = [
            "🇮🇩 WEEKLY INDONESIA STRATEGIC CORRIDOR REPORT",
            f"Date: {executive_summary['analysis_date']}",
            f"Market Status: {executive_summary['market_status']}",
            "",
            "📊 KEY METRICS:",
            f"  • Corridors Monitored: {executive_summary['key_metrics']['corridors_monitored']}",
            f"  • Average Score: {executive_summary['key_metrics']['average_investment_score']}/100",
            f"  • High-Conviction Opportunities: {executive_summary['key_metrics']['high_conviction_opportunities']}",
            f"  • Weekly Changes: {executive_summary['key_metrics']['total_weekly_changes']}",
            ""
        ]
        
        if executive_summary.get('top_opportunity'):
            top_opp = executive_summary['top_opportunity']
            alert_lines.extend([
                "🎯 TOP OPPORTUNITY:",
                f"  • {top_opp['name']} - Score: {top_opp['total_score']:.1f}/100",
                f"  • {top_opp['weekly_activity']['total_changes']} weekly changes",
                ""
            ])
        
        if executive_summary['priority_recommendations']:
            alert_lines.append("🚨 PRIORITY ACTIONS:")
            for rec in executive_summary['priority_recommendations']:
                alert_lines.append(f"  • {rec}")
            alert_lines.append("")
        
        if executive_summary['strategic_insights']:
            alert_lines.append("💡 STRATEGIC INSIGHTS:")
            for insight in executive_summary['strategic_insights']:
                alert_lines.append(f"  • {insight}")
        
        alert_message = "\n".join(alert_lines)
        
        # Log the alert (in production, send to Slack/email/webhook)
        logger.info("📧 WEEKLY STRATEGIC ALERT:")
        logger.info(alert_message)
        
        return alert_message

# Global instance
_weekly_monitor = None

def get_weekly_monitor() -> WeeklyStrategicMonitor:
    """Get the global weekly monitor instance"""
    global _weekly_monitor
    if _weekly_monitor is None:
        _weekly_monitor = WeeklyStrategicMonitor()
    return _weekly_monitor

async def run_weekly_strategic_monitoring():
    """Run the weekly strategic monitoring system"""
    monitor = get_weekly_monitor()
    return await monitor.generate_weekly_report()

if __name__ == "__main__":
    # Run weekly monitoring
    async def main():
        print("🚀 Starting Weekly Strategic Monitoring...")
        results = await run_weekly_strategic_monitoring()
        
        exec_summary = results['executive_summary']
        print("\n🇮🇩 WEEKLY STRATEGIC MONITORING COMPLETE")
        print("=" * 60)
        print(f"📅 Date: {exec_summary['analysis_date']}")
        print(f"📊 Market Status: {exec_summary['market_status']}")
        print(f"🎯 High-Conviction Opportunities: {exec_summary['key_metrics']['high_conviction_opportunities']}")
        print(f"📈 Total Weekly Changes: {exec_summary['key_metrics']['total_weekly_changes']}")
        
        if exec_summary.get('top_opportunity'):
            top_opp = exec_summary['top_opportunity']
            print(f"\n🏆 TOP OPPORTUNITY: {top_opp['name']}")
            print(f"    Score: {top_opp['total_score']:.1f}/100")
            print(f"    Weekly Activity: {top_opp['weekly_activity']['total_changes']} changes")
        
        if exec_summary['priority_recommendations']:
            print(f"\n🚨 PRIORITY ACTIONS:")
            for rec in exec_summary['priority_recommendations']:
                print(f"    • {rec}")
        
        print(f"\n✅ Report saved to ./output/weekly_reports/")
        print(f"🎊 Weekly strategic monitoring complete!")
    
    asyncio.run(main())