"""
Java Priority 1 Test Monitor
Tests expansion system with 15 highest-priority Java regions

This script validates the expansion to Java-wide coverage by testing
the 15 Priority 1 regions across Java (Jakarta, Bandung, Semarang, Yogyakarta, Surabaya, Banten)
"""

import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Run monitoring for Priority 1 Java regions"""
    
    print("=" * 80)
    print("🇮🇩 JAVA PRIORITY 1 EXPANSION TEST")
    print("=" * 80)
    print()
    
    # Import expansion manager
    from src.indonesia_expansion_regions import get_expansion_manager
    expansion_manager = get_expansion_manager()
    
    # Get Priority 1 Java regions
    priority1_regions = expansion_manager.get_priority1_java_regions()
    
    print(f"📊 **Test Scope**: {len(priority1_regions)} Priority 1 Java Regions")
    print()
    print("**Regions to Monitor:**")
    for i, region in enumerate(priority1_regions, 1):
        print(f"  {i}. {region.name} ({region.province}) - {region.focus}")
    
    print()
    print("=" * 80)
    print()
    
    # Import and configure the automated monitor
    from src.core.automated_monitor import AutomatedMonitor
    from src.core.config import get_config
    
    # Initialize monitor
    logger.info("Initializing Automated Monitor with Java Priority 1 regions...")
    monitor = AutomatedMonitor()
    
    # OVERRIDE the yogyakarta_regions with Java Priority 1 regions
    monitor.yogyakarta_regions = [region.name for region in priority1_regions]
    
    # Update region manager to handle expansion regions
    from src.indonesia_expansion_regions import get_expansion_manager
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
    
    print(f"✅ Monitor configured with {len(monitor.yogyakarta_regions)} Java Priority 1 regions")
    print()
    
    # Show expected processing time
    estimated_time = len(priority1_regions) * 2  # ~2 minutes per region
    print(f"⏱️  **Estimated Processing Time**: ~{estimated_time} minutes")
    print(f"📅 **Start Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run the monitoring
    start_time = datetime.now()
    
    try:
        print("🚀 Starting Java Priority 1 monitoring...")
        print("=" * 80)
        print()
        
        results = await monitor.run_weekly_monitoring()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        print()
        print("=" * 80)
        print("✅ MONITORING COMPLETED!")
        print("=" * 80)
        print()
        print("📊 **Results Summary:**")
        print(f"   • Total Regions Analyzed: {len(results['regions_analyzed'])}/{len(priority1_regions)}")
        print(f"   • Success Rate: {len(results['regions_analyzed'])/len(priority1_regions)*100:.1f}%")
        print(f"   • Total Changes Detected: {results['total_changes']:,}")
        print(f"   • Total Area Changed: {results['total_area_m2']/10000:.1f} hectares")
        print(f"   • Critical Alerts: {len([a for a in results['alerts'] if a['level'] == 'CRITICAL'])}")
        print(f"   • Processing Time: {duration:.1f} minutes")
        print(f"   • Avg Time per Region: {duration/len(priority1_regions):.1f} minutes")
        print()
        
        # Investment analysis summary
        investment = results.get('investment_analysis', {})
        yogyakarta_analysis = investment.get('yogyakarta_analysis', {})
        buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
        
        print("💰 **Investment Intelligence:**")
        print(f"   • Buy Recommendations: {len(buy_recs)}")
        if buy_recs:
            print(f"   • Top Opportunity: {buy_recs[0]['region']} ({buy_recs[0]['investment_score']:.1f}/100)")
            print()
            print("   **Top 5 Opportunities:**")
            for i, opp in enumerate(buy_recs[:5], 1):
                print(f"      {i}. {opp['region']}: {opp['investment_score']:.1f}/100")
                print(f"         {opp.get('rationale', 'N/A')}")
        
        print()
        print("=" * 80)
        print("🎯 **Next Steps:**")
        print("   1. Review PDF report in output/reports/")
        print("   2. Check satellite images in output/satellite_images/")
        print("   3. Analyze investment opportunities")
        print("   4. If successful, proceed to ALL Java (29 regions)")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Monitoring failed: {e}", exc_info=True)
        print()
        print("=" * 80)
        print("❌ MONITORING FAILED!")
        print("=" * 80)
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    print()
    print("🚀 CloudClearing - Java Priority 1 Expansion Test")
    print("   Testing comprehensive Java-wide monitoring capabilities")
    print()
    
    asyncio.run(main())
