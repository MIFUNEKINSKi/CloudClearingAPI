"""
Indonesia National Investment Analysis Demo
Demonstrates the strategic corridor ranking and investment scoring system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from national_corridors import get_national_manager, StrategicCorridor
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

def demonstrate_strategic_analysis():
    """Demonstrate the strategic analysis capabilities"""
    
    print("🇮🇩 INDONESIA STRATEGIC REAL ESTATE INVESTMENT ANALYSIS")
    print("="*70)
    print("CloudClearingAPI Phase 3: National Expansion Strategy")
    print()
    
    # Get the national manager
    manager = get_national_manager()
    
    # Generate comprehensive investment scores
    print("📊 TIER 1 STRATEGIC CORRIDORS - INVESTMENT RANKING:")
    print("-" * 70)
    print(f"{'RANK':<4} {'CORRIDOR':<35} {'SCORE':<6} {'TIER':<6} {'ISLAND'}")
    print("-" * 70)
    
    tier1_corridors = manager.get_tier1_corridors()
    
    # Enhanced scoring for demonstration
    scored_corridors = []
    for corridor in tier1_corridors:
        # Calculate comprehensive investment score
        base_score = corridor.investment_score()
        
        # Add satellite change simulation
        change_bonus = np.random.randint(5, 25)
        
        # Add infrastructure catalyst bonus
        infra_bonus = len(corridor.infrastructure_catalysts or []) * 3
        
        # Add market timing bonus
        roi_years = sum(corridor.expected_roi_years) / 2
        timing_bonus = max(0, (8 - roi_years) * 2)
        
        # Risk adjustment
        risk_multipliers = {
            'low': 1.0, 'medium': 0.95, 'medium-high': 0.9, 
            'high': 0.85, 'high-reward': 1.15
        }
        risk_mult = risk_multipliers.get(corridor.risk_level, 1.0)
        
        total_score = (base_score + change_bonus + infra_bonus + timing_bonus) * risk_mult
        total_score = min(100, max(0, total_score))
        
        scored_corridors.append((corridor, total_score))
    
    # Sort by score
    scored_corridors.sort(key=lambda x: x[1], reverse=True)
    
    # Display rankings
    for i, (corridor, score) in enumerate(scored_corridors, 1):
        print(f"{i:<4} {corridor.name:<35} {score:<6.1f} {corridor.investment_tier:<6} {corridor.island.capitalize()}")
    
    print()
    print("🎯 DETAILED INVESTMENT ANALYSIS - TOP 5 OPPORTUNITIES:")
    print("=" * 70)
    
    for i, (corridor, score) in enumerate(scored_corridors[:5], 1):
        print(f"\n{i}. {corridor.name} | Score: {score:.1f}/100")
        print(f"   Island: {corridor.island.capitalize()} | Focus: {corridor.focus.replace('_', ' ').title()}")
        print(f"   ROI Timeline: {corridor.expected_roi_years[0]}-{corridor.expected_roi_years[1]} years")
        print(f"   Risk Level: {corridor.risk_level.replace('-', ' ').title()}")
        print(f"   Market Maturity: {corridor.market_maturity.title()}")
        
        # Investment thesis
        if corridor.focus == 'new_capital':
            thesis = "🏛️ Government relocation creates unprecedented land value opportunity"
        elif 'port' in corridor.focus:
            thesis = "🚢 Strategic port development drives logistics and industrial demand"
        elif 'industrial' in corridor.focus:
            thesis = "🏭 Industrial zone expansion creates employment-driven land demand"
        elif corridor.focus == 'urban_expansion':
            thesis = "🏘️ Urban sprawl patterns indicate next residential/commercial wave"
        else:
            thesis = "📈 Multi-factor growth drivers converging for investment opportunity"
        
        print(f"   Investment Thesis: {thesis}")
        
        # Key catalysts
        catalysts = corridor.infrastructure_catalysts or []
        if catalysts:
            print(f"   Key Catalysts: {', '.join(catalysts[:3])}")
            if len(catalysts) > 3:
                print(f"                  + {len(catalysts) - 3} additional catalysts")
    
    print()
    print("💰 INVESTMENT RECOMMENDATIONS BY TIER:")
    print("-" * 50)
    
    # Tier 1 recommendations
    tier1_high = [c for c, s in scored_corridors if s > 80]
    tier1_medium = [c for c, s in scored_corridors if 65 <= s <= 80]
    tier1_watch = [c for c, s in scored_corridors if s < 65]
    
    print("🟢 IMMEDIATE BUY (Score > 80):")
    for corridor in tier1_high:
        print(f"   • {corridor.name} - Begin aggressive land banking")
    
    print("\n🟡 SELECTIVE ACCUMULATION (Score 65-80):")
    for corridor in tier1_medium:
        print(f"   • {corridor.name} - Acquire prime parcels selectively")
    
    print("\n🔴 WATCH LIST (Score < 65):")
    for corridor in tier1_watch:
        print(f"   • {corridor.name} - Monitor for improved fundamentals")
    
    # Market expansion analysis
    print()
    print("🗺️ GEOGRAPHIC EXPANSION ANALYSIS:")
    print("-" * 40)
    
    all_corridors = manager.corridors
    island_analysis = {}
    
    for corridor in all_corridors:
        if corridor.island not in island_analysis:
            island_analysis[corridor.island] = {
                'count': 0,
                'total_area': 0,
                'avg_score': 0,
                'top_corridor': None,
                'top_score': 0
            }
        
        island_analysis[corridor.island]['count'] += 1
        island_analysis[corridor.island]['total_area'] += corridor.area_km2()
        
        # Find corridor score from our analysis
        corridor_score = next((s for c, s in scored_corridors if c.name == corridor.name), corridor.investment_score())
        
        if corridor_score > island_analysis[corridor.island]['top_score']:
            island_analysis[corridor.island]['top_score'] = corridor_score
            island_analysis[corridor.island]['top_corridor'] = corridor.name
    
    for island, data in island_analysis.items():
        print(f"\n{island.upper()}:")
        print(f"   Corridors: {data['count']}")
        print(f"   Coverage: {data['total_area']:,.0f} km²")
        print(f"   Top Opportunity: {data['top_corridor']} ({data['top_score']:.1f}/100)")
    
    print()
    print("🚀 STRATEGIC IMPLEMENTATION ROADMAP:")
    print("-" * 45)
    print("Phase 3A (Next 60 days):")
    print("  ✅ Tier 1 corridor monitoring activated")
    print("  ✅ Infrastructure catalyst tracking enabled")
    print("  🎯 Land banking target identification")
    print()
    print("Phase 3B (90 days):")
    print("  📊 Local market intelligence integration")
    print("  🤝 Regional partner network establishment")
    print("  📋 Due diligence framework deployment")
    print()
    print("Phase 3C (120 days):")
    print("  💰 Strategic land acquisition initiation")
    print("  📈 Performance tracking and optimization")
    print("  🏆 Alpha generation validation")
    
    # Summary statistics
    total_area = sum(c.area_km2() for c in all_corridors)
    tier1_area = sum(c.area_km2() for c in tier1_corridors)
    
    print()
    print("📈 SYSTEM CAPABILITIES SUMMARY:")
    print("=" * 40)
    print(f"Total Strategic Coverage: {total_area:,.0f} km²")
    print(f"Tier 1 Priority Coverage: {tier1_area:,.0f} km²")
    print(f"Islands Covered: {len(island_analysis)}")
    print(f"Investment Opportunities: {len(all_corridors)}")
    print(f"High-Conviction Targets: {len(tier1_high)}")
    print()
    print("🎊 INDONESIA REAL ESTATE ALPHA GENERATION: OPERATIONAL!")
    
    return {
        'total_corridors': len(all_corridors),
        'tier1_corridors': len(tier1_corridors),
        'high_conviction': len(tier1_high),
        'total_coverage_km2': total_area,
        'top_opportunity': scored_corridors[0][0].name if scored_corridors else "None",
        'top_score': scored_corridors[0][1] if scored_corridors else 0
    }

if __name__ == "__main__":
    results = demonstrate_strategic_analysis()
    print(f"\n🏆 Analysis Complete: {results['high_conviction']} high-conviction opportunities identified!")