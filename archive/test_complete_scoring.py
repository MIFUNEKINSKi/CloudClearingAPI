#!/usr/bin/env python3
"""
End-to-end test of corrected scoring with working APIs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import ee
from src.core.corrected_scoring import CorrectedInvestmentScorer
from src.core.change_detector import ChangeDetector
from src.core.infrastructure_analyzer import InfrastructureAnalyzer
from src.core.price_intelligence import PriceIntelligenceEngine

# Initialize Earth Engine
try:
    ee.Initialize()
except:
    ee.Authenticate()
    ee.Initialize()

def test_complete_scoring():
    """Test complete scoring pipeline with real data"""
    print("\n🧪 Testing Complete Scoring Pipeline...")
    print("="*60)
    
    # Test region: Yogyakarta
    test_region = {
        'name': 'Yogyakarta Test',
        'coordinates': {
            'lat': -7.8,
            'lon': 110.4,
            'bbox': {
                'west': 110.3,
                'south': -7.9,
                'east': 110.5,
                'north': -7.7
            }
        }
    }
    
    print(f"📍 Test Region: {test_region['name']}")
    print(f"   Coordinates: {test_region['coordinates']['lat']}, {test_region['coordinates']['lon']}")
    
    # Initialize components
    print("\n🔧 Initializing components...")
    detector = ChangeDetector()
    price_engine = PriceIntelligenceEngine()
    infrastructure_engine = InfrastructureAnalyzer()
    scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine)
    
    # Detect changes
    print("\n🛰️  Detecting satellite changes (90 days)...")
    changes = detector.detect_changes(
        region_name=test_region['name'],
        coordinates=test_region['coordinates'],
        days_back=90
    )
    
    print(f"   Changes detected: {changes['total_changes']:,}")
    print(f"   Area affected: {changes['area_affected_hectares']:.2f} hectares")
    
    # Score the region
    print("\n💯 Scoring investment opportunity...")
    result = scorer.score_region(
        region_name=test_region['name'],
        coordinates=test_region['coordinates'],
        change_data=changes
    )
    
    # Display results
    print("\n" + "="*60)
    print("📊 SCORING RESULTS")
    print("="*60)
    
    print(f"\n🛰️  Part 1: Satellite Development (0-40 points)")
    print(f"   Changes: {result.satellite_changes:,}")
    print(f"   Area: {result.area_affected_hectares:.2f} ha")
    print(f"   Score: {result.development_score:.1f}/40")
    
    print(f"\n🏗️  Part 2: Infrastructure Multiplier (0.8-1.2x)")
    print(f"   Infrastructure Score: {result.infrastructure_score:.1f}/100")
    print(f"   Roads: {result.roads_count}")
    print(f"   Airports: {result.airports_nearby}")
    print(f"   Railway: {'Yes' if result.railway_access else 'No'}")
    print(f"   Multiplier: {result.infrastructure_multiplier:.2f}x")
    
    print(f"\n💰 Part 3: Market Multiplier (0.9-1.1x)")
    print(f"   Price Trend (30d): {result.price_trend_30d:+.1f}%")
    print(f"   Market Heat: {result.market_heat}")
    print(f"   Market Score: {result.market_score:.1f}/100")
    print(f"   Multiplier: {result.market_multiplier:.2f}x")
    
    print(f"\n🎯 FINAL INVESTMENT SCORE: {result.final_score:.1f}/60")
    print(f"   Recommendation: {result.recommendation}")
    print(f"   Confidence: {result.confidence_level:.0%}")
    
    print(f"\n📊 Data Availability:")
    print(f"   Infrastructure: {'✅ Live' if result.data_availability['infrastructure_data'] else '❌ Unavailable'}")
    print(f"   Market: {'✅ Live' if result.data_availability['market_data'] else '❌ Unavailable'}")
    
    # Verify APIs worked
    print("\n" + "="*60)
    if result.data_availability['infrastructure_data'] and result.data_availability['market_data']:
        print("✅ SUCCESS - Both APIs working and integrated!")
        print(f"   Confidence level: {result.confidence_level:.0%} (should be >40%)")
        return True
    else:
        print("❌ FAILURE - APIs still not working")
        return False
    
if __name__ == "__main__":
    success = test_complete_scoring()
    sys.exit(0 if success else 1)
