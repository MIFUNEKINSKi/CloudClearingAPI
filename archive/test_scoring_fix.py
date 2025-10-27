#!/usr/bin/env python3
"""
Quick test to verify the scoring fix works
Tests scoring on 1 region to confirm no more crashes
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_single_region():
    """Test scoring on a single region to verify the fix"""
    
    print("\n" + "="*80)
    print("🧪 TESTING SCORING FIX - Single Region Test")
    print("="*80)
    print()
    
    # Import after path setup
    from src.core.automated_monitor import AutomatedMonitor
    from src.indonesia_expansion_regions import get_expansion_manager
    import ee
    from src.core.config import get_config
    
    # Initialize Earth Engine
    config = get_config()
    print(f"🔧 Initializing Earth Engine (project: {config.gee_project})...")
    ee.Initialize(project=config.gee_project)
    print("✅ Earth Engine ready")
    print()
    
    # Get a test region
    expansion_manager = get_expansion_manager()
    java_regions = expansion_manager.get_java_regions()
    test_region = java_regions[0]  # Use first region as test
    
    print(f"📍 Test Region: {test_region.name}")
    print(f"   Priority: {test_region.priority}")
    print()
    
    # Initialize monitor with just 1 region
    monitor = AutomatedMonitor()
    monitor.yogyakarta_regions = [test_region.name]
    
    # Enhance region manager to handle expansion regions
    original_get_bbox = monitor.region_manager.get_region_bbox
    
    def enhanced_get_bbox(name: str):
        bbox = expansion_manager.get_region_bbox_dict(name)
        if bbox:
            return bbox
        return original_get_bbox(name)
    
    monitor.region_manager.get_region_bbox = enhanced_get_bbox
    
    print(f"🚀 Starting test analysis...")
    print(f"⏱️  Start time: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    try:
        results = await monitor.run_weekly_monitoring()
        
        print()
        print("="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        print()
        
        # Check if investment analysis was generated
        investment_analysis = results.get('investment_analysis', {})
        yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
        
        if yogyakarta_analysis and yogyakarta_analysis != {}:
            print("✅ Investment analysis generated!")
            
            buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
            watch_recs = yogyakarta_analysis.get('watch_list', [])
            pass_recs = yogyakarta_analysis.get('pass_regions', [])
            
            print(f"   • BUY recommendations: {len(buy_recs)}")
            print(f"   • WATCH list: {len(watch_recs)}")
            print(f"   • PASS regions: {len(pass_recs)}")
            
            if buy_recs:
                rec = buy_recs[0]
                print()
                print(f"📊 Sample Result: {rec['region_name']}")
                print(f"   Score: {rec.get('final_investment_score', 0):.1f}/100")
                print(f"   Recommendation: {rec.get('recommendation', 'N/A')}")
                print(f"   Confidence: {rec.get('overall_confidence', 0):.0%}")
            
            print()
            print("🎉 The scoring fix is WORKING! Ready for full Java run.")
            return True
        else:
            print("❌ Investment analysis is EMPTY - fix didn't work!")
            print(f"   yogyakarta_analysis: {yogyakarta_analysis}")
            return False
            
    except Exception as e:
        print()
        print("="*80)
        print("❌ TEST FAILED")
        print("="*80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_single_region())
    sys.exit(0 if success else 1)
