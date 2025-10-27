#!/usr/bin/env python3
"""
Test script to verify API fixes are working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.core.infrastructure_analyzer import InfrastructureAnalyzer
from src.core.price_intelligence import PriceIntelligenceEngine

def test_infrastructure_api():
    """Test InfrastructureAnalyzer API"""
    print("\n🔍 Testing InfrastructureAnalyzer...")
    
    analyzer = InfrastructureAnalyzer()
    
    # Test bbox for Yogyakarta
    test_bbox = {
        'west': 110.3,
        'south': -7.9,
        'east': 110.5,
        'north': -7.7
    }
    
    try:
        result = analyzer.analyze_infrastructure_context(
            bbox=test_bbox,
            region_name="Yogyakarta Test"
        )
        
        print(f"✅ Infrastructure API working!")
        print(f"   Score: {result['infrastructure_score']:.1f}/100")
        print(f"   Major features: {len(result.get('major_features', []))}")
        print(f"   Reasoning: {len(result.get('reasoning', []))} items")
        return True
        
    except Exception as e:
        print(f"❌ Infrastructure API failed: {e}")
        return False

def test_price_api():
    """Test PriceIntelligenceEngine API"""
    print("\n💰 Testing PriceIntelligenceEngine...")
    
    engine = PriceIntelligenceEngine()
    
    try:
        # Test with _get_pricing_data which is what corrected_scoring.py calls
        pricing_data = engine._get_pricing_data("Yogyakarta Test")
        
        print(f"✅ Price API working!")
        print(f"   Price: IDR {pricing_data.avg_price_per_m2:,.0f}/m²")
        print(f"   3-month trend: {pricing_data.price_trend_3m * 100:.1f}%")
        print(f"   Market heat: {pricing_data.market_heat}")
        print(f"   Data confidence: {pricing_data.data_confidence:.0%}")
        return True
        
    except Exception as e:
        print(f"❌ Price API failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("API FIX VERIFICATION TEST")
    print("="*60)
    
    infra_ok = test_infrastructure_api()
    price_ok = test_price_api()
    
    print("\n" + "="*60)
    if infra_ok and price_ok:
        print("✅ BOTH APIs WORKING - Ready to re-run monitoring!")
    else:
        print("❌ API ISSUES DETECTED")
        sys.exit(1)
    print("="*60)
