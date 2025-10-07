#!/usr/bin/env python3
"""
Direct test of the monitoring system with satellite images
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def test_monitoring_with_images():
    """Test the monitoring system and show satellite images"""
    print("🤖 Testing CloudClearing Monitoring with Satellite Images")
    print("=" * 60)
    
    # Import here to avoid syntax issues in automated_monitor.py
    try:
        from src.core.change_detector import ChangeDetector
        from src.regions import RegionManager
        
        # Initialize components
        detector = ChangeDetector()
        region_manager = RegionManager()
        
        print("✅ Components initialized successfully")
        
        # Test with Yogyakarta urban region
        region_name = "yogyakarta_urban"
        region_bbox = region_manager.get_region_bbox(region_name)
        
        if region_bbox:
            print(f"📍 Testing region: {region_name}")
            print(f"   Bounds: {region_bbox}")
            
            # Create Earth Engine geometry
            bbox = {
                'type': 'Polygon',
                'coordinates': [[
                    [region_bbox['west'], region_bbox['south']],
                    [region_bbox['east'], region_bbox['south']],
                    [region_bbox['east'], region_bbox['north']],
                    [region_bbox['west'], region_bbox['north']],
                    [region_bbox['west'], region_bbox['south']]
                ]]
            }
            
            # Run change detection with satellite image generation
            print("🛰️  Running satellite analysis...")
            result = detector.detect_weekly_changes(
                week_a_start='2025-06-22',
                week_b_start='2025-06-29', 
                bbox=bbox,
                export_results=False
            )
            
            print(f"✅ Analysis complete!")
            print(f"   Changes detected: {result['change_count']}")
            print(f"   Total area: {result['total_area']:.2f} m²")
            print(f"   Period: {result['week_a']} → {result['week_b']}")
            
            # Show satellite images
            if 'satellite_images' in result:
                sat_images = result['satellite_images']
                if 'error' not in sat_images:
                    print("\n🌍 SATELLITE IMAGERY FOR INVESTMENT ANALYSIS:")
                    print("=" * 50)
                    
                    print(f"📅 Analysis Period: {sat_images.get('week_a_date')} to {sat_images.get('week_b_date')}")
                    print()
                    
                    print("🖼️  BEFORE & AFTER COMPARISON:")
                    if 'week_a_true_color' in sat_images:
                        print(f"   🌍 Week A (Natural Color): {sat_images['week_a_true_color']}")
                    if 'week_b_true_color' in sat_images:
                        print(f"   🌍 Week B (Natural Color): {sat_images['week_b_true_color']}")
                    
                    print("\n🌿 VEGETATION ANALYSIS:")
                    if 'week_a_false_color' in sat_images:
                        print(f"   🌿 Week A (Vegetation View): {sat_images['week_a_false_color']}")
                    if 'week_b_false_color' in sat_images:
                        print(f"   🌿 Week B (Vegetation View): {sat_images['week_b_false_color']}")
                    
                    print("\n🔍 CHANGE DETECTION:")
                    if 'ndvi_change' in sat_images:
                        print(f"   🌱 NDVI Change Map: {sat_images['ndvi_change']}")
                        print("      (Red = vegetation loss, Green = vegetation gain)")
                    
                    print("\n📋 IMAGE DESCRIPTIONS:")
                    descriptions = sat_images.get('description', {})
                    for key, desc in descriptions.items():
                        print(f"   • {key}: {desc}")
                    
                    print("\n💡 INVESTMENT INSIGHT:")
                    print("   These satellite images show real land use changes that can indicate:")
                    print("   • Development activity (new buildings, infrastructure)")
                    print("   • Vegetation clearing for construction")
                    print("   • Urban expansion patterns")
                    print("   • Infrastructure development")
                    
                    if result['change_count'] > 10:
                        print(f"\n🎯 INVESTMENT SIGNAL: High activity detected ({result['change_count']} changes)")
                        print("   This region shows significant development activity!")
                    else:
                        print(f"\n📊 INVESTMENT STATUS: Moderate activity ({result['change_count']} changes)")
                        print("   This region shows some development activity.")
                
                else:
                    print(f"❌ Satellite image generation error: {sat_images.get('error')}")
            else:
                print("⚠️  No satellite images generated")
        
        else:
            print(f"❌ Could not find region: {region_name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_monitoring_with_images())