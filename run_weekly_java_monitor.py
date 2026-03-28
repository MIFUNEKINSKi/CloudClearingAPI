#!/usr/bin/env python3
"""
Weekly Java-Wide Monitor - Async Parallel Processing
Monitors all 29 regions across Java island for development changes

Features:
- Async parallel processing (5 regions at a time to respect GEE rate limits)
- GEE + OSM caching for performance
- Progress tracking with real-time updates
- Graceful error handling per region

Expected Runtime: ~30-35 minutes for all 29 regions (with warm cache)
"""

import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

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


async def process_region_batch(
    monitor,
    regions: List[str],
    week_a_start: str,
    week_b_start: str,
    batch_num: int,
    total_batches: int
) -> List[Dict[str, Any]]:
    """
    Process a batch of regions in parallel.
    
    Args:
        monitor: AutomatedMonitor instance
        regions: List of region names to process
        week_a_start: Start date for week A
        week_b_start: Start date for week B
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
    
    Returns:
        List of analysis results (successful regions only)
    """
    print(f"\n📦 Batch {batch_num}/{total_batches}: Processing {len(regions)} regions in parallel...")
    
    # Create async tasks for each region
    tasks = []
    for region_name in regions:
        task = monitor._analyze_region(region_name, week_a_start, week_b_start)
        tasks.append(task)
    
    # Execute all tasks in parallel and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and handle errors
    successful_results = []
    for region_name, result in zip(regions, results):
        if isinstance(result, Exception):
            logger.error(f"   ❌ {region_name}: {str(result)}")
        elif result is None:
            logger.warning(f"   ⚠️  {region_name}: No data available")
        else:
            # Result is a dict - check if cached
            cache_status = "🔵 CACHED" if result.get('_cached') else "🟢 FRESH"  # type: ignore
            logger.info(f"   ✅ {region_name}: {result['change_count']:,} changes ({cache_status})")  # type: ignore
            result['analysis_type'] = 'yogyakarta_region'  # type: ignore
            successful_results.append(result)
    
    return successful_results


async def run_parallel_monitoring(
    monitor,
    regions: List[str],
    week_a_start: str,
    week_b_start: str,
    batch_size: int = 5
) -> List[Dict[str, Any]]:
    """
    Process all regions in parallel batches.
    
    Args:
        monitor: AutomatedMonitor instance
        regions: List of all region names
        week_a_start: Start date for week A
        week_b_start: Start date for week B
        batch_size: Number of regions to process in parallel (default 5 for GEE rate limits)
    
    Returns:
        List of all successful analysis results
    """
    all_results = []
    total_regions = len(regions)
    
    # Split regions into batches
    batches = [regions[i:i + batch_size] for i in range(0, total_regions, batch_size)]
    total_batches = len(batches)
    
    logger.info(f"🚀 Parallel processing: {total_regions} regions in {total_batches} batches of {batch_size}")
    
    # Process each batch
    batch_start_time = datetime.now()
    for batch_num, batch in enumerate(batches, 1):
        batch_results = await process_region_batch(
            monitor, batch, week_a_start, week_b_start, batch_num, total_batches
        )
        all_results.extend(batch_results)
        
        # Show progress
        completed = len(all_results)
        progress_pct = (completed / total_regions) * 100
        elapsed = (datetime.now() - batch_start_time).total_seconds() / 60
        
        # Estimate remaining time
        if completed > 0:
            avg_time_per_region = elapsed / completed
            remaining_regions = total_regions - completed
            eta_minutes = avg_time_per_region * remaining_regions
            
            print(f"\n📊 Progress: {completed}/{total_regions} regions ({progress_pct:.1f}%)")
            print(f"   ⏱️  Elapsed: {elapsed:.1f} min | ETA: {eta_minutes:.1f} min remaining")
        
        # Small delay between batches to be respectful to APIs
        if batch_num < total_batches:
            await asyncio.sleep(2)
    
    return all_results


async def main():
    """Run weekly monitoring for ALL Java regions with parallel processing"""
    
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
    
    # Estimate processing time with parallel processing
    # With 5 parallel regions per batch: ~6 batches for 29 regions
    # Each batch: ~3-4 minutes (with GEE cache, faster after first run)
    avg_time_per_batch = 3.5  # minutes
    num_batches = (len(java_regions) + 4) // 5  # Ceiling division
    estimated_minutes = num_batches * avg_time_per_batch
    estimated_hours = estimated_minutes / 60
    
    print(f"⏱️  **ESTIMATED TIME**: {estimated_minutes:.0f} minutes (~{estimated_hours:.1f} hours)")
    print(f"    With parallel processing: {len(java_regions)} regions in {num_batches} batches of 5")
    print(f"    (First run: ~30-35 min | Cached runs: ~15-20 min)")
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
    
    # Run the monitoring with parallel processing
    start_time = datetime.now()
    
    try:
        print(f"\n📡 Processing {len(java_regions)} regions in parallel batches...")
        print("   (Progress updates will appear as each batch completes)")
        print()
        
        # Calculate date ranges using monitor's method
        end_date, start_date = monitor._get_optimal_date_range(0)
        
        week_a_start = start_date.strftime('%Y-%m-%d')
        week_b_start = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Week A: {week_a_start}")
        logger.info(f"📅 Week B: {week_b_start}")
        
        # Run parallel batch processing
        results_list = await run_parallel_monitoring(
            monitor=monitor,
            regions=[region.name for region in java_regions],
            week_a_start=week_a_start,
            week_b_start=week_b_start,
            batch_size=5  # Process 5 regions at a time
        )
        
        # Aggregate results (same format as run_weekly_monitoring)
        total_changes = sum(r.get('change_count', 0) for r in results_list)
        total_area_m2 = sum(r.get('total_area_m2', 0) for r in results_list)
        
        # Collect alerts
        all_alerts = []
        for result in results_list:
            if result.get('alerts'):
                all_alerts.extend(result['alerts'])
        
        # Assemble monitoring results object for investment analysis
        monitoring_results = {
            'timestamp': end_date.isoformat(),
            'regions_analyzed': results_list,
            'total_changes': total_changes,
            'total_area_m2': total_area_m2,
            'alerts': all_alerts,
            'period': f"{week_a_start} to {week_b_start}"
        }
        
        # Generate summary statistics for PDF compatibility
        alert_summary = {
            'critical': len([a for a in all_alerts if a.get('severity') == 'CRITICAL']),
            'major': len([a for a in all_alerts if a.get('severity') == 'MAJOR']),
            'total': len(all_alerts)
        }
        
        # Get top 3 most active regions
        sorted_regions = sorted(results_list, key=lambda x: x.get('change_count', 0), reverse=True)
        most_active = [
            {
                'name': r['region_name'],
                'changes': r.get('change_count', 0),
                'area_hectares': r.get('total_area_m2', 0) / 10000
            }
            for r in sorted_regions[:3]
        ]
        
        monitoring_results['summary'] = {
            'status': 'completed',
            'regions_monitored': len(results_list),
            'total_changes': total_changes,
            'total_area_hectares': total_area_m2 / 10000,
            'average_changes_per_region': total_changes / len(results_list) if results_list else 0,
            'alert_summary': alert_summary,
            'most_active_regions': most_active
        }
        
        # Generate investment analysis
        print()
        print("💰 Generating investment analysis...")
        investment_analysis = monitor._generate_investment_analysis(monitoring_results)
        
        # Add investment analysis to final results
        results = monitoring_results
        results['investment_analysis'] = investment_analysis
        
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
            
            # Track drift using region analysis data (includes financial projections)
            drift_summary = drift_monitor.track_drift(results_list)
            
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
        
        # 💾 Save monitoring results to JSON
        print()
        print("💾 Saving monitoring results...")
        from pathlib import Path
        import json
        
        output_dir = Path("output/monitoring")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = output_dir / f"weekly_monitoring_{timestamp}.json"
        
        # Custom JSON encoder for dataclasses
        def dataclass_serializer(obj):
            """Custom JSON serializer for dataclasses"""
            from dataclasses import is_dataclass, asdict
            if is_dataclass(obj):
                return asdict(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2, default=dataclass_serializer)
        
        logger.info(f"📁 Monitoring results saved to: {json_filename}")
        print(f"   ✅ JSON saved: {json_filename}")
        
        # 📄 Generate PDF executive summary
        print()
        print("📄 Generating PDF executive summary...")
        try:
            from src.core.pdf_report_generator import generate_pdf_from_json
            pdf_path = generate_pdf_from_json(str(json_filename))
            logger.info(f"📄 Executive summary PDF generated: {pdf_path}")
            print(f"   ✅ PDF generated: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to generate PDF report: {e}")
            print(f"   ⚠️  PDF generation failed: {e}")
        
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
