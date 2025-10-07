#!/usr/bin/env python3
"""
Simple script to run the automated monitoring with satellite image support
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.automated_monitor import AutomatedMonitor

async def main():
    """Run monitoring with satellite image display"""
    print("🤖 CloudClearing Automated Monitor with Satellite Images")
    print("=" * 60)
    
    monitor = AutomatedMonitor()
    
    try:
        results = await monitor.run_weekly_monitoring()
        
        print("\n✅ Weekly Monitoring Complete!")
        print("📊 Summary:")
        
        # Show basic summary
        summary = results.get('summary', {})
        if summary.get('status') == 'no_data':
            print(f"   Status: {summary['message']}")
        else:
            print(f"   Regions monitored: {summary.get('regions_monitored', 0)}")
            print(f"   Total changes: {summary.get('total_changes', 0)}")
            print(f"   Total area: {summary.get('total_area_hectares', 0)} hectares")
            print(f"   Alerts: {summary.get('alert_summary', {}).get('total', 0)}")
        
        # Show alerts
        if results.get('alerts'):
            print("\n🚨 Alerts:")
            for alert in results['alerts']:
                print(f"   - {alert['level']}: {alert['message']}")
        
        # Show investment analysis with satellite images
        investment_analysis = results.get('investment_analysis', {})
        if investment_analysis.get('status') != 'no_data':
            print("\n💰 INVESTMENT ANALYSIS WITH SATELLITE IMAGERY:")
            
            # Show executive summary
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
                    print(f"🏆 TOP OPPORTUNITY: {top_opp['region'].upper()} ({top_opp['score']:.1f}/100)")
            
            # Show opportunities with satellite images
            show_opportunities_with_images(investment_analysis, results)
        
        print(f"\n📁 Results saved to ./output/monitoring/")
        
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        import traceback
        traceback.print_exc()

def show_opportunities_with_images(investment_analysis, results):
    """Show investment opportunities with satellite image links"""
    
    # Show Yogyakarta opportunities
    yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
    if yogyakarta_analysis.get('buy_recommendations'):
        buy_recs = yogyakarta_analysis['buy_recommendations']
        print(f"\n🏠 YOGYAKARTA OPPORTUNITIES ({len(buy_recs)}):")
        
        for rec in buy_recs:
            print(f"   🎯 {rec['region'].upper()}: {rec['score']:.1f}/100")
            for reason in rec['reasoning'][:2]:
                print(f"      - {reason}")
            
            # Find satellite images for this region
            region_data = find_region_satellite_images(rec['region'], results)
            if region_data:
                show_satellite_images(region_data)
    
    # Show Strategic corridor opportunities
    strategic_analysis = investment_analysis.get('strategic_corridor_analysis', {})
    if strategic_analysis.get('high_conviction_opportunities'):
        high_conv = strategic_analysis['high_conviction_opportunities']
        print(f"\n🇮🇩 STRATEGIC CORRIDORS ({len(high_conv)} high-conviction):")
        
        for opp in high_conv:
            tier = opp.get('investment_tier', 'unknown')
            island = opp.get('island', 'unknown').title()
            changes = opp.get('change_count', 0)
            signals = len(opp.get('investment_signals', []))
            print(f"   🏆 {opp['corridor_name'].upper()}: {opp['score']:.1f}/100")
            print(f"      📍 {island} • {tier} • {changes} satellite changes • {signals} signals")
            
            # Show investment signals
            for signal in opp.get('investment_signals', [])[:2]:
                print(f"      ✓ {signal}")
            
            # Show satellite images
            satellite_activity = opp.get('satellite_activity', {})
            if satellite_activity.get('satellite_images'):
                show_satellite_images(satellite_activity)

def find_region_satellite_images(region_name, results):
    """Find satellite images for a specific region"""
    for region_data in results.get('regions_analyzed', []):
        if region_data.get('region_name') == region_name:
            return region_data
    return None

def show_satellite_images(region_data):
    """Display satellite image links for a region"""
    satellite_images = region_data.get('satellite_images', {})
    if satellite_images and 'error' not in satellite_images:
        print(f"      📡 SATELLITE IMAGERY:")
        if 'week_a_true_color' in satellite_images:
            print(f"         🌍 Before (Natural): {satellite_images['week_a_true_color']}")
        if 'week_b_true_color' in satellite_images:
            print(f"         🌍 After (Natural):  {satellite_images['week_b_true_color']}")
        if 'week_a_false_color' in satellite_images:
            print(f"         🌿 Before (Vegetation): {satellite_images['week_a_false_color']}")
        if 'week_b_false_color' in satellite_images:
            print(f"         🌿 After (Vegetation):  {satellite_images['week_b_false_color']}")
        if 'ndvi_change' in satellite_images:
            print(f"         🌱 Change Map: {satellite_images['ndvi_change']}")
        print(f"         📅 Period: {satellite_images.get('week_a_date')} to {satellite_images.get('week_b_date')}")

if __name__ == "__main__":
    asyncio.run(main())