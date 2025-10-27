"""
Validation Monitoring Test - Market Data Flow Verification
CloudClearingAPI - October 26, 2025 - Post v2.8.1 Lamudi Fix

Tests market data flow after Lamudi scraper fix on a subset of diverse regions.

Goal: Verify that:
1. Live market data is being retrieved (market_data: true)
2. Data source is "lamudi" (not "static_benchmark")  
3. RVI calculations produce non-zero, sensible values
4. Market multipliers vary appropriately (not all 1.0x)
5. Market heat classifications are accurate

Test Regions (5 diverse regions across all tiers):
- jakarta_north_sprawl (Tier 1 Metro - Expected: HEATING, high RVI, 1.25-1.4x multiplier)
- yogyakarta_periurban (Tier 2 Secondary - Expected: MODERATE, mid RVI, 1.0-1.15x)
- bandung_north_expansion (Tier 2 Secondary - Expected: WARMING, mid RVI, 1.0-1.25x)
- semarang_industrial (Tier 3 Emerging - Expected: WEAK to MODERATE, low-mid RVI, 0.85-1.15x)
- tegal_brebes_coastal (Tier 4 Frontier - Expected: WEAK, low RVI, 0.85-1.0x)

Expected Runtime: ~15-25 minutes (5 regions with OSM cache)
Success Criteria: ≥3/5 regions show market_data: true with valid RVI
"""

import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.automated_monitor import AutomatedMonitor
from src.indonesia_expansion_regions import get_expansion_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def run_validation_monitoring():
    """
    Run validation monitoring on subset of diverse regions
    
    Returns:
        dict: Validation results with market data metrics
    """
    logger.info("="*70)
    logger.info("VALIDATION MONITORING - MARKET DATA FLOW TEST")
    logger.info("="*70)
    logger.info(f"Post v2.8.1 Lamudi Fix Deployment")
    logger.info(f"Expected: Market data from Lamudi (40% coverage)")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    # Select test regions (5 diverse regions across tiers)
    expansion_manager = get_expansion_manager()
    all_regions = expansion_manager.get_all_regions()
    
    # Use actual region names with underscores (from indonesia_expansion_regions.py)
    test_region_names = [
        "jakarta_north_sprawl",           # Tier 1 Metro
        "yogyakarta_urban_core",          # Tier 2 Secondary (corrected name)
        "bandung_north_expansion",        # Tier 2 Secondary
        "semarang_port_expansion",        # Tier 3 Emerging (corrected name)
        "tegal_brebes_coastal"            # Tier 4 Frontier
    ]
    
    # Filter to selected regions
    test_regions = [r for r in all_regions if r.name in test_region_names]
    
    logger.info(f"\nTest Regions Selected: {len(test_regions)}/5")
    for region in test_regions:
        logger.info(f"  - {region.name} ({region.island}, Priority {region.priority})")
    
    if len(test_regions) == 0:
        logger.error("No test regions found! Check region names.")
        sys.exit(1)
    
    # Initialize monitor
    monitor = AutomatedMonitor()
    
    # Replace yogyakarta_regions with our test regions
    monitor.yogyakarta_regions = [region.name for region in test_regions]
    logger.info(f"✅ Configured monitor with {len(monitor.yogyakarta_regions)} test regions")
    
    # Enhance region manager to use expansion regions
    original_get_bbox = monitor.region_manager.get_region_bbox
    
    def enhanced_get_bbox(name: str):
        """Enhanced bbox getter that checks expansion regions first"""
        bbox = expansion_manager.get_region_bbox_dict(name)
        if bbox:
            return bbox
        return original_get_bbox(name)
    
    monitor.region_manager.get_region_bbox = enhanced_get_bbox
    logger.info("✅ Enhanced region manager with expansion support")
    
    logger.info(f"\nStarting analysis...")
    logger.info(f"Expected Runtime: ~15-25 minutes (5 regions with OSM cache)")
    logger.info("="*70 + "\n")
    
    # Run weekly monitoring (which will use our test regions)
    results = await monitor.run_weekly_monitoring()
    
    logger.info("\n" + "="*70)
    logger.info("VALIDATION MONITORING COMPLETE")
    logger.info("="*70)
    
    return results


def analyze_validation_results(results_file: Path):
    """
    Analyze validation monitoring results
    
    Args:
        results_file: Path to validation monitoring JSON
        
    Returns:
        dict: Analysis summary with pass/fail metrics
    """
    logger.info("\n" + "="*70)
    logger.info("VALIDATION RESULTS ANALYSIS")
    logger.info("="*70)
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    regions_analyzed = data.get('summary', {}).get('regions_analyzed', 0)
    logger.info(f"\nRegions Analyzed: {regions_analyzed}")
    
    # Analyze each region's market data status
    market_data_results = []
    
    for region_data in data.get('regions', []):
        region_name = region_data.get('region_name', 'Unknown')
        
        # Check market data availability
        missing_data = region_data.get('missing_data', {})
        has_market_data = not missing_data.get('market_data', False)
        
        # Get market data details
        market_data = region_data.get('market_data', {})
        data_source = market_data.get('data_source', 'unknown')
        avg_price = market_data.get('average_price_per_m2', 0)
        confidence = market_data.get('data_confidence', 0)
        
        # Get scoring results
        corrected_score = region_data.get('corrected_scoring', {})
        final_score = corrected_score.get('final_score', 0)
        
        # Get RVI if available
        rvi_pct = corrected_score.get('rvi_pct', None)
        
        # Get market multiplier
        market_multiplier = corrected_score.get('market_multiplier', 1.0)
        
        # Get market heat
        market_heat = corrected_score.get('market_heat', 'UNKNOWN')
        
        result = {
            'region': region_name,
            'has_market_data': has_market_data,
            'data_source': data_source,
            'avg_price': avg_price,
            'confidence': confidence,
            'rvi_pct': rvi_pct,
            'market_multiplier': market_multiplier,
            'market_heat': market_heat,
            'final_score': final_score
        }
        
        market_data_results.append(result)
        
        # Log result
        status = "✅" if has_market_data else "❌"
        logger.info(f"\n{status} {region_name}:")
        logger.info(f"   Market Data: {has_market_data}")
        logger.info(f"   Data Source: {data_source}")
        if has_market_data:
            logger.info(f"   Avg Price: Rp {avg_price:,.0f}/m²")
            logger.info(f"   Confidence: {confidence:.0%}")
            if rvi_pct is not None:
                logger.info(f"   RVI: {rvi_pct:+.1f}%")
            logger.info(f"   Market Multiplier: {market_multiplier:.2f}x")
            logger.info(f"   Market Heat: {market_heat}")
            logger.info(f"   Final Score: {final_score:.1f}/100")
    
    # Summary statistics
    logger.info("\n" + "="*70)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*70)
    
    regions_with_market_data = sum(1 for r in market_data_results if r['has_market_data'])
    regions_with_lamudi = sum(1 for r in market_data_results if r['data_source'] == 'lamudi')
    regions_with_static = sum(1 for r in market_data_results if r['data_source'] == 'static_benchmark')
    regions_with_rvi = sum(1 for r in market_data_results if r['rvi_pct'] is not None and r['rvi_pct'] != 0)
    
    varied_multipliers = len(set(r['market_multiplier'] for r in market_data_results)) > 1
    
    logger.info(f"\n📊 Market Data Availability:")
    logger.info(f"   Live Data: {regions_with_market_data}/{regions_analyzed} ({regions_with_market_data/regions_analyzed*100:.0f}%)")
    logger.info(f"   Lamudi Source: {regions_with_lamudi}/{regions_analyzed}")
    logger.info(f"   Static Fallback: {regions_with_static}/{regions_analyzed}")
    
    logger.info(f"\n📈 RVI Calculations:")
    logger.info(f"   Non-Zero RVI: {regions_with_rvi}/{regions_analyzed} ({regions_with_rvi/regions_analyzed*100:.0f}%)")
    
    logger.info(f"\n🎯 Market Multipliers:")
    logger.info(f"   Varied Multipliers: {'✅ YES' if varied_multipliers else '❌ NO (all identical)'}")
    unique_multipliers = sorted(set(r['market_multiplier'] for r in market_data_results))
    logger.info(f"   Range: {min(unique_multipliers):.2f}x - {max(unique_multipliers):.2f}x")
    
    # Success criteria
    logger.info("\n" + "="*70)
    logger.info("SUCCESS CRITERIA CHECK")
    logger.info("="*70)
    
    criteria = {
        '≥40% Live Market Data': regions_with_market_data/regions_analyzed >= 0.4,
        '≥60% Non-Zero RVI': regions_with_rvi/regions_analyzed >= 0.6,
        'Varied Market Multipliers': varied_multipliers,
        '≥1 Lamudi Source': regions_with_lamudi >= 1
    }
    
    all_pass = all(criteria.values())
    
    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {criterion}")
    
    logger.info("\n" + "="*70)
    logger.info("FINAL VERDICT")
    logger.info("="*70)
    
    if all_pass:
        logger.info("✅ VALIDATION SUCCESSFUL")
        logger.info("🎯 CCAPI-27.1 Full Validation: CAN PROCEED")
        logger.info("\nNext Steps:")
        logger.info("  1. Proceed with CCAPI-27.1 Full End-to-End Validation")
        logger.info("  2. Run full 12-region test suite")
        logger.info("  3. Verify ≥75% RVI sensibility rate")
        logger.info("  4. Validate market multiplier differentiation")
        verdict = "PASS"
    else:
        logger.info("⚠️ VALIDATION INCOMPLETE")
        logger.info("Some criteria not met, but may still proceed with caution")
        logger.info("\nFailed Criteria:")
        for criterion, passed in criteria.items():
            if not passed:
                logger.info(f"  - {criterion}")
        verdict = "PARTIAL"
    
    return {
        'verdict': verdict,
        'regions_analyzed': regions_analyzed,
        'live_data_pct': regions_with_market_data/regions_analyzed,
        'rvi_success_pct': regions_with_rvi/regions_analyzed,
        'varied_multipliers': varied_multipliers,
        'criteria': criteria,
        'results': market_data_results
    }


if __name__ == '__main__':
    print("\n" + "="*70)
    print("STARTING VALIDATION MONITORING")
    print("="*70 + "\n")
    
    # Run validation monitoring using asyncio
    import asyncio
    results = asyncio.run(run_validation_monitoring())
    
    # Find the generated JSON file
    output_dir = Path('output/monitoring')
    validation_files = sorted(output_dir.glob('weekly_monitoring_*.json'), reverse=True)
    
    if validation_files:
        latest_file = validation_files[0]
        logger.info(f"\nAnalyzing results from: {latest_file}")
        
        # Analyze results
        analysis = analyze_validation_results(latest_file)
        
        print("\n" + "="*70)
        print("VALIDATION COMPLETE")
        print("="*70)
        print(f"\nVerdict: {analysis['verdict']}")
        print(f"Live Data: {analysis['live_data_pct']:.0%}")
        print(f"RVI Success: {analysis['rvi_success_pct']:.0%}")
        
        if analysis['verdict'] == 'PASS':
            print("\n✅ Ready to proceed with CCAPI-27.1 Full Validation!\n")
            sys.exit(0)
        else:
            print("\n⚠️ Validation incomplete but may proceed with caution.\n")
            sys.exit(1)
    else:
        logger.error("No validation results file found!")
        sys.exit(1)
