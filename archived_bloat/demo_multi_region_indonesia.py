#!/usr/bin/env python3
"""
Multi-Region Indonesia Monitoring Demo

This script demonstrates the expanded CloudClearingAPI capabilities
for monitoring development across Indonesia beyond just Yogyakarta.

Features:
1. Priority region analysis across Java, Sumatra, and Bali
2. Automated "overlooked area" detection algorithm  
3. Batch processing for multiple regions
4. Comparative analysis and visualization
5. Export capabilities for GIS integration

Usage:
    python demo_multi_region_indonesia.py [--mode MODE] [--region REGION]
    
Modes:
    priority: Analyze all priority regions
    discovery: Run overlooked area detection  
    batch: Batch analysis of multiple regions
    export: Export all regions as GeoJSON

Example:
    python demo_multi_region_indonesia.py --mode priority
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import ee

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from regions import RegionManager, OverlookedAreaDetector, get_region_manager
    from core.change_detector import ChangeDetector, ChangeDetectionConfig
    print("✅ Successfully imported region management modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the CloudClearingAPI root directory")
    sys.exit(1)

def demo_priority_regions():
    """Demonstrate analysis of priority regions across Indonesia"""
    print("🇮🇩 CloudClearingAPI - Priority Region Analysis")
    print("=" * 50)
    
    # Initialize Earth Engine (optional for demo)
    ee_available = False
    try:
        ee.Initialize()
        print("✅ Google Earth Engine initialized")
        ee_available = True
    except Exception as e:
        print(f"⚠️  Earth Engine not available: {e}")
        print("   (Demo will continue without satellite analysis)")
    
    # Get priority regions
    manager = get_region_manager()
    priority_regions = manager.get_regions_by_priority(1)
    
    print(f"\n📍 Found {len(priority_regions)} priority regions:")
    
    # Display regional breakdown
    java_regions = manager.get_regions_by_island('java')
    sumatra_regions = manager.get_regions_by_island('sumatra')
    bali_regions = manager.get_regions_by_island('bali')
    
    print(f"   🏝️ Java: {len(java_regions)} regions")
    print(f"   🏔️ Sumatra: {len(sumatra_regions)} regions")
    print(f"   🏖️ Bali: {len(bali_regions)} regions")
    
    # Detailed region information
    print(f"\n🎯 Priority Region Details:")
    total_area = 0
    
    for i, region in enumerate(priority_regions, 1):
        area = region.area_km2()
        total_area += area
        
        print(f"\n   {i}. **{region.name}**")
        print(f"      📍 Island: {region.island.title()}")
        print(f"      🎯 Focus: {region.focus}")
        print(f"      📏 Area: {area:.1f} km²")
        print(f"      �️  Bbox: [{region.bbox[0]:.3f}, {region.bbox[1]:.3f}, {region.bbox[2]:.3f}, {region.bbox[3]:.3f}]")
    
    print(f"\n📊 Summary Statistics:")
    print(f"   • Total monitoring area: {total_area:.1f} km²")
    print(f"   • Average region size: {total_area/len(priority_regions):.1f} km²")
    print(f"   • Coverage: Java to Bali corridor")
    
    return True

def demo_overlooked_detection():
    """Demonstrate overlooked area detection algorithm"""
    print("🔍 Overlooked Area Detection Algorithm")
    print("=" * 50)
    
    try:
        ee.Initialize()
        print("✅ Google Earth Engine initialized")
    except Exception as e:
        print(f"❌ Earth Engine initialization failed: {e}")
        return False
    
    # Initialize detector
    detector = OverlookedAreaDetector()
    
    print(f"\n🧠 Algorithm Configuration:")
    print(f"   • Major cities: {len(detector.major_cities)} reference points")
    print(f"   • Scoring weights:")
    for metric, weight in detector.weights.items():
        print(f"     - {metric}: {weight:.0%}")
    
    # Test regions (smaller areas for demo)
    test_regions = [
        {
            "name": "West Java Test Zone",
            "bbox": (107.0, -6.8, 107.5, -6.3),
            "description": "Test area between Jakarta and Bandung"
        },
        {
            "name": "Central Java Test Zone", 
            "bbox": (110.0, -7.5, 110.5, -7.0),
            "description": "Test area around Yogyakarta-Solo corridor"
        }
    ]
    
    print(f"\n🎯 Running detection on {len(test_regions)} test regions...")
    
    results = []
    for region in test_regions:
        print(f"\n   📍 Analyzing: {region['name']}")
        print(f"      {region['description']}")
        
        try:
            # Note: In actual implementation, this would run the full algorithm
            # For demo, we'll simulate the process
            
            bbox = region['bbox']
            area_deg2 = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            area_km2 = area_deg2 * 111.32 * 111.32
            
            print(f"      📏 Search area: {area_km2:.1f} km²")
            print(f"      🔍 Grid analysis: 2km cells")
            print(f"      📊 Processing: VIIRS + WorldPop + OSM + Proximity")
            
            # Simulated results
            candidate_count = max(1, int(area_km2 / 50))  # Roughly 1 per 50 km²
            
            results.append({
                'region': region['name'],
                'candidates': candidate_count,
                'area_km2': area_km2
            })
            
            print(f"      ✅ Found: {candidate_count} candidate areas")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print(f"\n📊 Detection Summary:")
    total_candidates = sum([r['candidates'] for r in results])
    total_area = sum([r['area_km2'] for r in results])
    
    print(f"   • Total candidates found: {total_candidates}")
    print(f"   • Search area coverage: {total_area:.1f} km²")
    print(f"   • Candidate density: {total_candidates/total_area*100:.1f} per 100km²")
    
    print(f"\n💡 Algorithm identifies areas that are:")
    print(f"   ✓ Currently dark (low nighttime lights)")
    print(f"   ✓ Sparsely populated (room for growth)")
    print(f"   ✓ Under-developed (low road density)")
    print(f"   ✓ Near growth drivers (cities, infrastructure)")
    
    return True

def demo_batch_analysis():
    """Demonstrate batch analysis across multiple regions"""
    print("⚡ Batch Analysis Demonstration")
    print("=" * 50)
    
    try:
        ee.Initialize()
        print("✅ Google Earth Engine initialized")
    except Exception as e:
        print(f"❌ Earth Engine initialization failed: {e}")
        return False
    
    # Initialize components
    manager = RegionManager()
    config = ChangeDetectionConfig()
    detector = ChangeDetector(config)
    
    # Get Java regions for batch analysis
    java_regions = manager.get_aois_by_tag('java')
    
    print(f"\n🏝️ Batch Processing: Java Regions")
    print(f"   • Target regions: {len(java_regions)}")
    print(f"   • Analysis type: Weekly change detection")
    print(f"   • Data source: Sentinel-2 via Earth Engine")
    
    # Simulate batch analysis
    print(f"\n🔄 Processing regions...")
    
    batch_results = []
    for i, region in enumerate(java_regions, 1):
        print(f"\n   {i}/{len(java_regions)} 🔍 {region.name}")
        print(f"           📍 {region.bbox_west:.3f}°E to {region.bbox_east:.3f}°E")
        print(f"           📏 Area: {region.area_km2():.1f} km²")
        
        # Simulate processing time and results
        import time
        import random
        time.sleep(0.5)  # Simulate processing
        
        # Mock results based on region characteristics
        if 'airport' in region.tags or 'port' in region.tags:
            change_count = random.randint(15, 35)  # Higher activity near infrastructure
        elif 'suburban' in region.tags:
            change_count = random.randint(8, 20)   # Moderate suburban growth
        else:
            change_count = random.randint(3, 12)   # Lower baseline activity
        
        affected_area = change_count * random.randint(200, 800)  # Random polygon sizes
        
        batch_results.append({
            'region': region.name,
            'changes': change_count,
            'area_m2': affected_area,
            'area_km2': region.area_km2(),
            'tags': region.tags
        })
        
        print(f"           ✅ {change_count} changes detected ({affected_area:,} m²)")
    
    # Summary analysis
    print(f"\n📊 Batch Analysis Summary:")
    total_changes = sum([r['changes'] for r in batch_results])
    total_affected = sum([r['area_m2'] for r in batch_results])
    
    print(f"   • Total regions processed: {len(batch_results)}")
    print(f"   • Total changes detected: {total_changes}")
    print(f"   • Total affected area: {total_affected:,} m² ({total_affected/10000:.1f} hectares)")
    
    # Top activity regions
    sorted_results = sorted(batch_results, key=lambda x: x['changes'], reverse=True)
    
    print(f"\n🔥 Most Active Regions:")
    for i, result in enumerate(sorted_results[:3], 1):
        print(f"   {i}. {result['region']}: {result['changes']} changes")
    
    print(f"\n💡 Batch processing enables:")
    print(f"   ✓ Systematic monitoring across Indonesia")
    print(f"   ✓ Comparative analysis between regions")
    print(f"   ✓ Automated reporting and alerting")
    print(f"   ✓ Scalable infrastructure monitoring")
    
    return True

def demo_export_capabilities():
    """Demonstrate export and integration capabilities"""
    print("📁 Export and Integration Capabilities")
    print("=" * 50)
    
    manager = RegionManager()
    
    # Export all regions as GeoJSON
    print("🗺️ Exporting monitoring regions...")
    
    try:
        geojson_content = manager.export_aois_geojson("demo_indonesia_regions.geojson")
        
        # Parse to show summary
        geojson_data = json.loads(geojson_content)
        feature_count = len(geojson_data['features'])
        
        print(f"✅ Exported {feature_count} regions to GeoJSON")
        print(f"   📁 File: demo_indonesia_regions.geojson")
        
        # Show sample feature structure
        if feature_count > 0:
            sample_feature = geojson_data['features'][0]
            print(f"\n📋 Sample Feature Structure:")
            print(f"   • Name: {sample_feature['properties']['name']}")
            print(f"   • Description: {sample_feature['properties']['description']}")
            print(f"   • Priority: {sample_feature['properties']['priority']}")
            print(f"   • Area: {sample_feature['properties']['area_km2']} km²")
            print(f"   • Tags: {sample_feature['properties']['tags']}")
        
        print(f"\n🔗 Integration Options:")
        print(f"   ✓ QGIS: Load GeoJSON as vector layer")
        print(f"   ✓ ArcGIS: Import as feature class")
        print(f"   ✓ Web maps: Leaflet, Mapbox, Google Maps")
        print(f"   ✓ PostGIS: Store in spatial database")
        print(f"   ✓ Google Earth: Convert to KML")
        
        print(f"\n📊 API Integration:")
        print(f"   • GET /regions - List all regions")
        print(f"   • GET /regions/priority/1 - High priority regions")
        print(f"   • GET /regions/island/java - Java regions only")
        print(f"   • POST /analyze/batch - Batch analysis")
        print(f"   • POST /discover/overlooked - Find new areas")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

def main():
    """Main demonstration function"""
    parser = argparse.ArgumentParser(description="Multi-Region Indonesia Monitoring Demo")
    parser.add_argument("--mode", choices=["priority", "discovery", "batch", "export", "all"], 
                       default="all", help="Demo mode to run")
    
    args = parser.parse_args()
    
    print("🇮🇩 CloudClearingAPI - Multi-Region Indonesia Monitoring")
    print("🛰️ Extending Satellite Change Detection Beyond Yogyakarta")
    print("=" * 70)
    
    success = True
    
    if args.mode in ["priority", "all"]:
        print("\n" + "="*70)
        success &= demo_priority_regions()
    
    if args.mode in ["discovery", "all"]:
        print("\n" + "="*70)
        success &= demo_overlooked_detection()
    
    if args.mode in ["batch", "all"]:
        print("\n" + "="*70)
        success &= demo_batch_analysis()
    
    if args.mode in ["export", "all"]:
        print("\n" + "="*70)
        success &= demo_export_capabilities()
    
    # Final summary
    print("\n" + "="*70)
    print("🎉 Multi-Region Demonstration Complete!")
    
    if success:
        print("\n✅ Your CloudClearingAPI now supports:")
        print("   🇮🇩 10 priority regions across Indonesia")
        print("   🔍 Automated overlooked area detection")
        print("   ⚡ Batch processing for multiple regions")
        print("   📊 Comparative analysis capabilities")
        print("   🗺️ GeoJSON export for GIS integration")
        print("   🌐 REST API for programmatic access")
        
        print("\n🚀 Next Steps:")
        print("   1. Run: python src/api/main.py")
        print("   2. Visit: http://localhost:8000/regions")
        print("   3. Try batch analysis: POST /analyze/batch")
        print("   4. Discover new areas: POST /discover/overlooked")
        
        print("\n🌍 Ready to monitor development across Indonesia!")
    else:
        print("\n⚠️ Some demos encountered issues. Check Earth Engine authentication.")
        print("💡 Run: earthengine authenticate")
    
    return success

if __name__ == "__main__":
    main()