"""
Test script to verify financial projection and infrastructure details fixes
Quick test on a single region before running full monitoring
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_single_region():
    """Test financial projection and infrastructure details for a single region"""
    from src.core.automated_monitor import AutomatedMonitor
    
    logger.info("🧪 Starting test of financial projection and infrastructure details fixes...")
    
    # Initialize monitor
    monitor = AutomatedMonitor()
    
    # Check if financial engine initialized
    logger.info(f"💰 Financial Engine Available: {monitor.financial_engine is not None}")
    
    # Run analysis on a single region (Bekasi - known to have high activity)
    # We'll manually trigger analysis by running monitoring in test mode
    logger.info("📊 Running single region analysis...")
    
    # Run full monitoring but we'll only check one region's output
    results = await monitor.run_weekly_monitoring()
    
    # Check if results contain financial projections
    if results and 'investment_analysis' in results:
        inv_analysis = results['investment_analysis']
        
        # Check buy recommendations
        if 'buy_recommendations' in inv_analysis:
            logger.info(f"\n✅ Found {len(inv_analysis['buy_recommendations'])} BUY recommendations")
            
            for rec in inv_analysis['buy_recommendations'][:3]:  # Check first 3
                region_name = rec.get('region')
                logger.info(f"\n🔍 Checking region: {region_name}")
                logger.info(f"   Investment Score: {rec.get('investment_score')}")
                logger.info(f"   Infrastructure Score: {rec.get('infrastructure_score')}")
                
                # Check infrastructure details
                infra_details = rec.get('infrastructure_details', {})
                if infra_details:
                    logger.info(f"   ✅ Infrastructure Details Present:")
                    logger.info(f"      - Roads: {infra_details.get('roads', 'N/A')}")
                    logger.info(f"      - Airports: {infra_details.get('airports', 'N/A')}")
                    logger.info(f"      - Railways: {infra_details.get('railways', 'N/A')}")
                    logger.info(f"      - Ports: {infra_details.get('ports', 'N/A')}")
                    logger.info(f"      - Construction Projects: {infra_details.get('construction_projects', 'N/A')}")
                else:
                    logger.warning(f"   ❌ Infrastructure Details Missing!")
                
                # Check financial projection
                fin_proj = rec.get('financial_projection')
                if fin_proj:
                    logger.info(f"   ✅ Financial Projection Present:")
                    logger.info(f"      - Current Land Value: Rp {fin_proj.get('current_land_value_per_m2', 0):,.0f}/m²")
                    logger.info(f"      - Projected Value: Rp {fin_proj.get('estimated_future_value_per_m2', 0):,.0f}/m²")
                    logger.info(f"      - 3-Year ROI: {fin_proj.get('projected_roi_3yr', 0):.1%}")
                    logger.info(f"      - Data Sources: {fin_proj.get('data_sources', [])}")
                else:
                    logger.warning(f"   ❌ Financial Projection Missing!")
        
        # Also check watch list
        if 'watch_list' in inv_analysis:
            logger.info(f"\n✅ Found {len(inv_analysis['watch_list'])} WATCH recommendations")
            
            # Check first watch item for data presence
            if inv_analysis['watch_list']:
                rec = inv_analysis['watch_list'][0]
                region_name = rec.get('region')
                logger.info(f"\n🔍 Sample WATCH region: {region_name}")
                logger.info(f"   Has Infrastructure Details: {bool(rec.get('infrastructure_details'))}")
                logger.info(f"   Has Financial Projection: {bool(rec.get('financial_projection'))}")
    
    logger.info("\n✅ Test completed!")
    return results


if __name__ == "__main__":
    asyncio.run(test_single_region())
