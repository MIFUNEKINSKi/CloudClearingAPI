#!/usr/bin/env python3
"""Test why some regions don't get investment scores"""

import json
from src.core.dynamic_scoring_integration import DynamicScoringIntegration

# Load monitoring data
with open('output/monitoring/weekly_monitoring_20251005_154603.json', 'r') as f:
    data = json.load(f)

# Initialize dynamic scorer
scorer = DynamicScoringIntegration()

# Test all regions
unscored_regions = ['yogyakarta_periurban', 'bantul_south', 'semarang_industrial', 'surakarta_suburbs']

print("Testing unscored regions:\n")

for region_data in data['regions_analyzed']:
    region_name = region_data['region_name']
    
    if region_name not in unscored_regions:
        continue
    
    print(f"=== {region_name} ===")
    print(f"Changes: {region_data.get('change_count', 0):,}")
    print(f"Area: {region_data.get('total_area_m2', 0) / 10000:.1f} ha")
    
    # Prepare config
    region_config = {
        'name': region_name,
        'bbox': region_data['bbox'],
        'center': {
            'lat': (region_data['bbox']['north'] + region_data['bbox']['south']) / 2,
            'lng': (region_data['bbox']['east'] + region_data['bbox']['west']) / 2
        }
    }
    
    # Try to score
    try:
        result = scorer.calculate_dynamic_score(region_name, region_config)
        print(f"✅ Investment Score: {result.final_investment_score:.1f}/100")
        print(f"   Confidence: {result.overall_confidence:.1%}")
        print(f"   Market: ${result.current_price_per_m2:,.0f}/m² ({result.price_trend_30d:+.1f}%)")
        print(f"   Infrastructure: {result.infrastructure_score:.1f}")
        
        # Check if it meets buy criteria
        if result.final_investment_score >= 70 and result.overall_confidence >= 0.6:
            print(f"   📈 Would be BUY recommendation")
        elif result.final_investment_score >= 50:
            print(f"   👀 Would be WATCH recommendation")
        else:
            print(f"   ❌ Below threshold - not recommended")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print()

