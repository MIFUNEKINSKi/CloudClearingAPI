#!/usr/bin/env python3
"""
Quick Validation: Analyze Existing Monitoring Results

This script analyzes the most recent successful monitoring run to validate
that the corrected scoring system is working properly.
"""

import json
import sys
from pathlib import Path

def analyze_monitoring_file(filepath):
    """Analyze a monitoring JSON file"""
    print(f"\n📄 Analyzing: {filepath.name}")
    print("=" * 80)
    
    with open(filepath) as f:
        data = json.load(f)
    
    regions = data.get('regions', [])
    
    if not regions:
        print("❌ No regions found in this file")
        return None
    
    print(f"✅ Found {len(regions)} regions\n")
    
    # Collect statistics
    scores = []
    satellite_changes = []
    recommendations = {'BUY': 0, 'WATCH': 0, 'PASS': 0, 'UNKNOWN': 0}
    has_development_score = 0
    
    print("📊 Sample Regions:")
    print("-" * 80)
    
    for i, region in enumerate(regions[:5], 1):  # Show first 5
        name = region.get('region_name', 'Unknown')
        score = region.get('investment_score', 0)
        changes = region.get('changes', 0)
        rec = region.get('recommendation', 'UNKNOWN')
        dev_score = region.get('development_score')
        
        scores.append(score)
        satellite_changes.append(changes)
        recommendations[rec] = recommendations.get(rec, 0) + 1
        
        if dev_score is not None:
            has_development_score += 1
        
        print(f"\n{i}. {name}")
        print(f"   Changes: {changes:,} pixels")
        print(f"   Investment Score: {score:.1f}/100")
        print(f"   Recommendation: {rec}")
        
        if dev_score is not None:
            print(f"   Development Score: {dev_score:.1f}/40 ✅ (NEW FIELD!)")
        else:
            print(f"   Development Score: N/A ⚠️ (OLD SYSTEM?)")
    
    # Process all regions for stats
    for region in regions[5:]:
        score = region.get('investment_score', 0)
        changes = region.get('changes', 0)
        rec = region.get('recommendation', 'UNKNOWN')
        dev_score = region.get('development_score')
        
        scores.append(score)
        satellite_changes.append(changes)
        recommendations[rec] = recommendations.get(rec, 0) + 1
        if dev_score is not None:
            has_development_score += 1
    
    # Statistics
    print("\n" + "=" * 80)
    print("📈 OVERALL STATISTICS")
    print("=" * 80)
    
    if scores:
        min_score = min(scores)
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        
        print(f"\n🎯 Score Distribution:")
        print(f"   Range: {min_score:.1f} - {max_score:.1f}")
        print(f"   Average: {avg_score:.1f}")
        print(f"   Median: {sorted(scores)[len(scores)//2]:.1f}")
    
    print(f"\n📡 Satellite Data:")
    if satellite_changes:
        print(f"   Min changes: {min(satellite_changes):,} pixels")
        print(f"   Max changes: {max(satellite_changes):,} pixels")
        print(f"   Avg changes: {sum(satellite_changes)/len(satellite_changes):,.0f} pixels")
    
    print(f"\n💼 Recommendations:")
    total_recs = sum(recommendations.values())
    for rec, count in recommendations.items():
        if count > 0:
            pct = (count / total_recs * 100)
            print(f"   {rec}: {count} ({pct:.1f}%)")
    
    print(f"\n🆕 New Fields:")
    print(f"   Regions with development_score: {has_development_score}/{len(regions)}")
    if has_development_score > 0:
        print(f"   ✅ CORRECTED SCORING SYSTEM DETECTED!")
    else:
        print(f"   ⚠️  No development_score fields - may be old system")
    
    # Validation
    print("\n" + "=" * 80)
    print("✅ VALIDATION CHECKS")
    print("=" * 80)
    
    checks_passed = []
    checks_failed = []
    
    # Check 1: Score range
    if scores and max(scores) < 65:
        print(f"✅ Score range looks correct (<65): {min(scores):.1f}-{max(scores):.1f}")
        checks_passed.append("Score range")
    elif scores:
        print(f"❌ Scores too high (>65): {max(scores):.1f}")
        print(f"   This suggests OLD scoring system!")
        checks_failed.append("Score range")
    
    # Check 2: Recommendation diversity
    if recommendations['PASS'] > 0 or recommendations['WATCH'] > 0:
        print(f"✅ Recommendation diversity good (not all BUYs)")
        checks_passed.append("Recommendation diversity")
    else:
        print(f"❌ All recommendations are BUY (suggests old system)")
        checks_failed.append("Recommendation diversity")
    
    # Check 3: Development score field
    if has_development_score > 0:
        print(f"✅ New 'development_score' field present")
        checks_passed.append("New fields")
    else:
        print(f"❌ Missing 'development_score' field")
        checks_failed.append("New fields")
    
    # Check 4: Correlation
    if len(scores) >= 2:
        # Check if low changes correlate with low scores
        low_change_regions = [(s, c) for s, c in zip(scores, satellite_changes) if c < 5000]
        if low_change_regions:
            low_avg_score = sum(s for s, c in low_change_regions) / len(low_change_regions)
            if low_avg_score < 35:
                print(f"✅ Low changes → low scores (correlation good)")
                checks_passed.append("Satellite correlation")
            else:
                print(f"⚠️  Low changes → high scores (weak correlation)")
                checks_failed.append("Satellite correlation")
    
    print(f"\n📊 Summary: {len(checks_passed)}/{len(checks_passed)+len(checks_failed)} checks passed")
    
    return {
        'passed': len(checks_passed),
        'failed': len(checks_failed),
        'has_new_fields': has_development_score > 0,
        'score_range': (min(scores) if scores else 0, max(scores) if scores else 0),
        'regions': len(regions)
    }

def main():
    print("\n🔍 CORRECTED SCORING VALIDATION")
    print("=" * 80)
    print("Analyzing recent monitoring runs for corrected scoring system...")
    
    # Find recent monitoring files
    output_dir = Path(__file__).parent / "output" / "monitoring"
    files = sorted(output_dir.glob("*.json"), reverse=True, key=lambda x: x.stat().st_size)
    
    # Filter files >1KB (has data)
    files_with_data = [f for f in files if f.stat().st_size > 1024][:3]
    
    if not files_with_data:
        print("❌ No monitoring files with data found!")
        return False
    
    print(f"\nFound {len(files_with_data)} recent files with data\n")
    
    results = []
    for filepath in files_with_data:
        result = analyze_monitoring_file(filepath)
        if result:
            results.append(result)
    
    # Overall assessment
    print("\n" + "🎉" * 40)
    print("OVERALL ASSESSMENT")
    print("🎉" * 40)
    
    if results:
        any_new_fields = any(r['has_new_fields'] for r in results)
        all_score_ranges_good = all(r['score_range'][1] < 65 for r in results if r['score_range'][1] > 0)
        
        if any_new_fields and all_score_ranges_good:
            print("\n✅ CORRECTED SCORING SYSTEM IS WORKING!")
            print("   - New 'development_score' fields detected")
            print("   - Score ranges look correct (<65)")
            print("   - Ready for documentation updates")
            return True
        else:
            if not any_new_fields:
                print("\n⚠️  WARNING: No 'development_score' fields found")
                print("   The system may not be using the corrected scorer yet")
            if not all_score_ranges_good:
                print("\n⚠️  WARNING: Some scores are too high (>65)")
                print("   This suggests old scoring system is still in use")
            return False
    else:
        print("\n❌ Could not validate - no usable results found")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
