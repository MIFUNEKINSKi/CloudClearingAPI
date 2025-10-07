#!/usr/bin/env python3
"""
Test the new resilient scoring approach where missing API data 
reduces confidence but not the score itself.
"""

from src.core.dynamic_scoring_integration import DynamicScoringIntegration
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Initialize dynamic scorer
scorer = DynamicScoringIntegration()

# Test with a region that will likely have API timeouts (large area)
test_regions = [
    {
        'name': 'yogyakarta_periurban',
        'bbox': {'north': -7.6, 'south': -7.9, 'east': 110.5, 'west': 110.3},
        'center': {'lat': -7.75, 'lng': 110.4},
        'expected': 'Large region - may timeout on OSM API'
    },
    {
        'name': 'yogyakarta_urban',
        'bbox': {'north': -7.75, 'south': -7.85, 'east': 110.42, 'west': 110.32},
        'center': {'lat': -7.8, 'lng': 110.37},
        'expected': 'Smaller region - likely success'
    }
]

print("="*80)
print("RESILIENT SCORING TEST: Missing Data Reduces Confidence, Not Score")
print("="*80)
print()

for region_info in test_regions:
    region_name = region_info['name']
    region_config = {k: v for k, v in region_info.items() if k != 'expected'}
    
    print(f"\n{'='*80}")
    print(f"Testing: {region_name}")
    print(f"Expected: {region_info['expected']}")
    print(f"{'='*80}\n")
    
    try:
        # This should NOT throw an error even if APIs timeout
        result = scorer.calculate_dynamic_score(region_name, region_config)
        
        print(f"✅ SCORING SUCCEEDED")
        print(f"   Investment Score: {result.final_investment_score:.1f}/100")
        print(f"   Overall Confidence: {result.overall_confidence:.1%}")
        print()
        
        # Check data sources
        if isinstance(result.data_sources, dict):
            print(f"   📊 Data Availability:")
            availability = result.data_sources.get('availability', {})
            for source, available in availability.items():
                status = "✓" if available else "✗"
                print(f"      {status} {source.replace('_', ' ').title()}")
            
            print()
            missing_note = result.data_sources.get('missing_data_note', 'N/A')
            if 'unavailable' in missing_note.lower():
                print(f"   ⚠️  {missing_note}")
            else:
                print(f"   ✓ {missing_note}")
        
        print()
        print(f"   💡 Interpretation:")
        if result.overall_confidence < 0.5:
            print(f"      Low confidence ({result.overall_confidence:.0%}) due to missing API data")
            print(f"      BUT score ({result.final_investment_score:.1f}) based on satellite evidence")
        elif result.overall_confidence < 0.7:
            print(f"      Medium confidence - some data sources available")
        else:
            print(f"      High confidence - all data sources available!")
            
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print(f"   This should NOT happen - scorer should handle all failures gracefully")
        import traceback
        traceback.print_exc()
    
    print()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
