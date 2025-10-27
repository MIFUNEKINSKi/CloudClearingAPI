#!/usr/bin/env python3
"""
Test that pass_list fix is working correctly.
This verifies that PASS regions (<25) are now captured in the pass_list.
"""

import json
from pathlib import Path

# Find the most recent monitoring JSON
output_dir = Path("output/monitoring")
json_files = sorted(output_dir.glob("weekly_monitoring_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

if not json_files:
    print("❌ No monitoring JSON files found!")
    exit(1)

latest_json = json_files[0]
print(f"📄 Testing with: {latest_json.name}\n")

with open(latest_json, 'r') as f:
    data = json.load(f)

# Get investment analysis
investment_analysis = data.get('investment_analysis', {})
yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})

# Get all recommendation lists
buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
watch_list = yogyakarta_analysis.get('watch_list', [])
pass_list = yogyakarta_analysis.get('pass_list', [])

print("=" * 70)
print("RECOMMENDATION COUNTS")
print("=" * 70)
print(f"BUY recommendations (≥40):   {len(buy_recs)}")
print(f"WATCH list (≥25, <40):       {len(watch_list)}")
print(f"PASS list (<25):             {len(pass_list)}")
print(f"TOTAL:                       {len(buy_recs) + len(watch_list) + len(pass_list)}")
print()

# Check if pass_list exists (new fix)
if 'pass_list' in yogyakarta_analysis:
    print("✅ pass_list EXISTS in JSON (fix is working!)")
else:
    print("⚠️  pass_list MISSING from JSON (using old monitoring run)")
print()

# Show sample scores from each category
print("=" * 70)
print("SAMPLE SCORES BY CATEGORY")
print("=" * 70)

if buy_recs:
    print("\n🟢 BUY Recommendations (score ≥40):")
    for rec in buy_recs[:3]:
        print(f"   • {rec.get('region', 'N/A')}: {rec.get('investment_score', 0):.1f}/100")

if watch_list:
    print("\n🟡 WATCH List (score ≥25, <40):")
    for rec in watch_list[:3]:
        print(f"   • {rec.get('region', 'N/A')}: {rec.get('investment_score', 0):.1f}/100")

if pass_list:
    print("\n🔴 PASS List (score <25):")
    for rec in pass_list[:5]:
        print(f"   • {rec.get('region', 'N/A')}: {rec.get('investment_score', 0):.1f}/100")
else:
    print("\n🔴 PASS List: (empty or not yet generated)")

print()
print("=" * 70)
print("VERIFICATION STATUS")
print("=" * 70)

# Get regions analyzed
regions_analyzed = data.get('analysis', {}).get('regions_analyzed', [])
total_analyzed = len(regions_analyzed)
total_with_scores = len(buy_recs) + len(watch_list) + len(pass_list)

print(f"Total regions analyzed:      {total_analyzed}")
print(f"Total regions with scores:   {total_with_scores}")

if total_with_scores == total_analyzed:
    print("\n✅ SUCCESS: All analyzed regions have scores!")
    print("✅ The pass_list fix is working correctly!")
elif total_with_scores == 0:
    print("\n⚠️  This JSON was created BEFORE the pass_list fix.")
    print("⚠️  Run monitoring again to test the fix.")
else:
    print(f"\n⚠️  WARNING: {total_analyzed - total_with_scores} regions missing scores!")

print("=" * 70)
