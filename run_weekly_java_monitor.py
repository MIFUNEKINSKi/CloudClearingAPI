#!/usr/bin/env python3
"""
Weekly Java-Wide Monitor
Monitors all 29 regions across Java island for development changes

This expands from 10 Yogyakarta regions to comprehensive Java coverage:
- 14 Priority 1 regions (infrastructure, major urban, industrial)
- 10 Priority 2 regions (secondary cities, ports, tourism)
- 5 Priority 3 regions (tertiary markets, coastal development)

Expected Runtime: ~60-90 minutes for all 29 regions
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup comprehensive logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/java_weekly_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run weekly monitoring for ALL Java regions"""
    
    print("\n" + "="*100)
    print("🇮🇩 JAVA-WIDE WEEKLY MONITORING")
    print("="*100)
    print()
    
    # Import expansion manager
    from src.indonesia_expansion_regions import get_expansion_manager
    expansion_manager = get_expansion_manager()
    
    # Get ALL Java regions
    java_regions = expansion_manager.get_java_regions()
    
    # Group by priority for reporting
    priority_1 = [r for r in java_regions if r.priority == 1]
    priority_2 = [r for r in java_regions if r.priority == 2]
    priority_3 = [r for r in java_regions if r.priority == 3]
    
    print(f"📊 **MONITORING SCOPE**: {len(java_regions)} Java Regions")
    print()
    print(f"   • Priority 1 (High Investment): {len(priority_1)} regions")
    print(f"   • Priority 2 (Medium Investment): {len(priority_2)} regions")
    print(f"   • Priority 3 (Emerging Markets): {len(priority_3)} regions")
    print()
    
    print("**Coverage Map:**")
    print("   • Jakarta Metro Area: 4 regions")
    print("   • Bandung Metro: 2 regions")
    print("   • Semarang-Yogyakarta-Solo Triangle: 6 regions")
    print("   • Surabaya Metro: 4 regions")
    print("   • Banten Industrial Corridor: 3 regions")
    print("   • Regional Hubs: 10 regions")
    print()
    
    # Estimate processing time
    avg_time_per_region = 3  # minutes (with fallback attempts)
    estimated_minutes = len(java_regions) * avg_time_per_region
    estimated_hours = estimated_minutes / 60
    
    print(f"⏱️  **ESTIMATED TIME**: {estimated_minutes} minutes (~{estimated_hours:.1f} hours)")
    print(f"📅 **START TIME**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("=" * 100)
    print()
    
    # Confirm before proceeding
    print("⚠️  This is a comprehensive monitoring run that will:")
    print("   1. Analyze satellite imagery for 29 regions across Java")
    print("   2. Calculate investment scores with resilient API handling")
    print("   3. Generate PDF report with all findings")
    print("   4. Save satellite images for top opportunities")
    print()
    
    response = input("Continue with Java-wide monitoring? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n❌ Monitoring cancelled by user")
        return
    
    print("\n🚀 Starting Java-wide monitoring...")
    print("=" * 100)
    print()
    
    # Import and configure the automated monitor
    from src.core.automated_monitor import AutomatedMonitor
    from src.core.config import get_config
    
    # Initialize monitor
    logger.info("Initializing Automated Monitor for Java-wide coverage...")
    monitor = AutomatedMonitor()
    
    # REPLACE yogyakarta_regions with ALL Java regions
    monitor.yogyakarta_regions = [region.name for region in java_regions]
    logger.info(f"✅ Configured with {len(monitor.yogyakarta_regions)} Java regions")
    
    # Update region manager to handle expansion regions
    original_get_bbox = monitor.region_manager.get_region_bbox
    
    def enhanced_get_bbox(name: str):
        """Enhanced bbox getter that checks expansion regions first"""
        # Try expansion manager first
        bbox = expansion_manager.get_region_bbox_dict(name)
        if bbox:
            return bbox
        # Fall back to original regions
        return original_get_bbox(name)
    
    # Monkey-patch the region manager
    monitor.region_manager.get_region_bbox = enhanced_get_bbox
    logger.info("✅ Enhanced region manager with Indonesia expansion support")
    
    # Run the monitoring
    start_time = datetime.now()
    
    try:
        print(f"\n📡 Processing {len(java_regions)} regions...")
        print("   (Progress updates will appear as each region completes)")
        print()
        
        results = await monitor.run_weekly_monitoring()
        
        # ✅ CCAPI-27.2: Track benchmark drift after monitoring completes
        print()
        print("📊 Tracking benchmark drift...")
        try:
            from src.core.benchmark_drift_monitor import BenchmarkDriftMonitor
            
            drift_monitor = BenchmarkDriftMonitor(
                history_dir="./data/benchmark_drift",
                retention_days=180,  # 6 months
                enable_alerts=True
            )
            
            # Track drift using investment analysis data (includes financial projections)
            investment_analysis = results.get('investment_analysis', {}).get('yogyakarta_analysis', {})
            all_recommendations = (
                investment_analysis.get('buy_recommendations', []) +
                investment_analysis.get('watch_list', []) +
                investment_analysis.get('pass_list', [])
            )
            drift_summary = drift_monitor.track_drift(all_recommendations)
            
            # Add drift summary to results
            results['drift_monitoring'] = drift_summary
            
            # Log drift alerts
            drift_alerts = drift_summary.get('alerts', {})
            if drift_alerts.get('total', 0) > 0:
                print(f"   ⚠️  Drift Alerts: {drift_alerts['critical']} CRITICAL, {drift_alerts['warning']} WARNING")
                
                # Show critical alerts
                for alert in drift_alerts.get('details', []):
                    if alert['alert_level'] == 'CRITICAL':
                        print(f"      🔴 {alert['region_name']}: {alert['current_drift_pct']:+.1f}% drift "
                              f"({alert['consecutive_weeks']} weeks)")
            else:
                print("   ✅ No drift alerts - benchmarks are healthy")
                
        except Exception as drift_error:
            logger.warning(f"Drift monitoring failed (non-critical): {drift_error}")
            results['drift_monitoring'] = {'status': 'failed', 'error': str(drift_error)}
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        print()
        print("=" * 100)
        print("✅ JAVA-WIDE MONITORING COMPLETED!")
        print("=" * 100)
        print()
        
        # Comprehensive results summary
        regions_analyzed = results.get('regions_analyzed', [])
        total_changes = results.get('total_changes', 0)
        total_area = results.get('total_area_m2', 0) / 10000  # Convert to hectares
        alerts = results.get('alerts', [])
        
        print("📊 **SATELLITE ANALYSIS RESULTS:**")
        print(f"   • Regions Successfully Analyzed: {len(regions_analyzed)}/{len(java_regions)}")
        print(f"   • Success Rate: {len(regions_analyzed)/len(java_regions)*100:.1f}%")
        print(f"   • Total Changes Detected: {total_changes:,}")
        print(f"   • Total Area Changed: {total_area:,.1f} hectares")
        print(f"   • Critical Alerts: {len([a for a in alerts if a.get('level') == 'CRITICAL'])}")
        print(f"   • Major Alerts: {len([a for a in alerts if a.get('level') == 'MAJOR'])}")
        print()
        
        # Performance metrics
        print(f"⚡ **PERFORMANCE:**")
        print(f"   • Total Processing Time: {duration:.1f} minutes ({duration/60:.2f} hours)")
        print(f"   • Average Time per Region: {duration/len(java_regions):.1f} minutes")
        print(f"   • Regions per Hour: {len(regions_analyzed)/(duration/60):.1f}")
        print()
        
        # Drift monitoring results (CCAPI-27.2)
        drift_data = results.get('drift_monitoring', {})
        if drift_data.get('status') == 'complete':
            drift_stats = drift_data.get('overall_stats', {})
            drift_alerts = drift_data.get('alerts', {})
            
            print("📈 **BENCHMARK DRIFT MONITORING (v2.9.0):**")
            print(f"   • Regions Tracked: {drift_data.get('regions_tracked', 0)}")
            print(f"   • Average Drift: {drift_stats.get('avg_drift_pct', 0):+.1f}%")
            print(f"   • Regions >10% Drift: {drift_stats.get('regions_above_10pct', 0)}")
            print(f"   • Regions >20% Drift: {drift_stats.get('regions_above_20pct', 0)}")
            print(f"   • Active Alerts: {drift_alerts.get('total', 0)} "
                  f"({drift_alerts.get('critical', 0)} CRITICAL, {drift_alerts.get('warning', 0)} WARNING)")
            
            if drift_alerts.get('total', 0) > 0:
                print()
                print("   ⚠️  **DRIFT ALERTS REQUIRING ATTENTION:**")
                for alert_detail in drift_alerts.get('details', [])[:5]:  # Show top 5
                    region = alert_detail['region_name']
                    drift = alert_detail['current_drift_pct']
                    weeks = alert_detail['consecutive_weeks']
                    level = alert_detail['alert_level']
                    icon = "🔴" if level == "CRITICAL" else "🟡"
                    print(f"      {icon} {region}: {drift:+.1f}% drift ({weeks} consecutive weeks)")
            
            print()
        
        # Investment analysis
        investment = results.get('investment_analysis', {})
        yogyakarta_analysis = investment.get('yogyakarta_analysis', {})  # Name is legacy but works for all regions
        buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
        watch_list = yogyakarta_analysis.get('watch_list', [])
        
        print("💰 **INVESTMENT INTELLIGENCE:**")
        print(f"   • Strong Buy Recommendations: {len(buy_recs)}")
        print(f"   • Watch List Opportunities: {len(watch_list)}")
        print()
        
        if buy_recs:
            print("   🏆 **TOP 10 INVESTMENT OPPORTUNITIES:**")
            for i, opp in enumerate(buy_recs[:10], 1):
                region_name = opp.get('region', 'Unknown')
                score = opp.get('investment_score', 0)
                confidence = opp.get('confidence_level', 0)
                changes = opp.get('satellite_changes', 0)
                
                # Get region details
                region_obj = next((r for r in java_regions if r.name == region_name), None)
                province = region_obj.province if region_obj else 'Java'
                
                print(f"      {i:2d}. {region_name:40s} ({province})")
                print(f"          Score: {score:.1f}/100 | Confidence: {confidence:.0%} | Changes: {changes:,}")
                
                # Show data availability if present
                data_sources = opp.get('data_sources', {})
                if isinstance(data_sources, dict) and 'missing_data_note' in data_sources:
                    note = data_sources['missing_data_note']
                    if 'unavailable' in note.lower():
                        print(f"          ⚠️ {note}")
        
        print()
        print("=" * 100)
        print("📁 **OUTPUT FILES:**")
        print(f"   • Monitoring Data: output/monitoring/weekly_monitoring_*.json")
        print(f"   • PDF Report: output/reports/executive_summary_*.pdf")
        print(f"   • Satellite Images: output/satellite_images/weekly/")
        print(f"   • Drift History: data/benchmark_drift/*_drift_history.json")
        print(f"   • Detailed Logs: logs/java_weekly_*.log")
        print()
        
        print("=" * 100)
        print("🎯 **NEXT STEPS:**")
        print("   1. ✅ Review the PDF executive summary for investment insights")
        print("   2. ✅ Analyze satellite imagery for top opportunities")
        print("   3. ✅ Compare results across different Java regions")
        print("   4. ✅ Track confidence levels - follow up on low-confidence scores")
        print("   5. ✅ If successful, consider expanding to Sumatra/Bali")
        print("=" * 100)
        print()
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Monitoring interrupted by user")
        logger.warning("User interrupted monitoring")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Monitoring failed: {e}", exc_info=True)
        print()
        print("=" * 100)
        print("❌ MONITORING FAILED!")
        print("=" * 100)
        print(f"Error: {str(e)}")
        print()
        print("Check logs/java_weekly_*.log for detailed error information")
        raise

if __name__ == "__main__":
    import asyncio
    
    print()
    print("🚀 CloudClearing - Java-Wide Weekly Monitoring")
    print("   Comprehensive satellite analysis across Java island")
    print("   29 regions from Jakarta to Banyuwangi")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
