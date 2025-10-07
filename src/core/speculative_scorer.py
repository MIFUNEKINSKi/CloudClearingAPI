"""
Speculative Real Estate Scoring System

This module transforms raw change detection into profit-weighted signals
by analyzing proximity to infrastructure, development patterns, and regional economics.

Author: CloudClearingAPI Team
Date: September 2025
"""

import ee
import requests
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import numpy as np
from pathlib import Path

# Import intelligence modules
try:
    from .infrastructure_analyzer import InfrastructureAnalyzer
    from .price_intelligence import PriceIntelligenceEngine
except ImportError:
    # Fallback imports for standalone testing
    try:
        from infrastructure_analyzer import InfrastructureAnalyzer
        from price_intelligence import PriceIntelligenceEngine
    except ImportError:
        InfrastructureAnalyzer = None
        PriceIntelligenceEngine = None

logger = logging.getLogger(__name__)

@dataclass
class SpeculativeScore:
    """Container for speculative scoring results"""
    region_name: str
    base_score: float          # Raw change magnitude (0-100)
    infrastructure_score: float # Proximity to roads/infrastructure (0-100)
    development_pattern_score: float # Type of development detected (0-100) 
    strategic_location_score: float # Regional strategic value (0-100)
    final_score: float         # Weighted composite score (0-100)
    confidence: float          # Confidence in the scoring (0-1)
    buy_signal: str           # BUY/WATCH/IGNORE
    reasoning: List[str]      # Human-readable justification

class SpeculativeScorer:
    """
    Transforms change detection alerts into investment opportunities
    """
    
    def __init__(self):
        self.strategic_regions = self._load_strategic_regions()
        
        # Initialize intelligence modules
        self.infrastructure_analyzer = InfrastructureAnalyzer() if InfrastructureAnalyzer else None
        self.price_intelligence = PriceIntelligenceEngine() if PriceIntelligenceEngine else None
        
        self.infrastructure_weights = {
            'major_highway': 100,
            'planned_highway': 85,
            'provincial_road': 60,
            'new_road_construction': 95,
            'airport_corridor': 90,
            'port_access': 80,
            'railway_planned': 75
        }
        
        # Change type priorities for real estate speculation
        self.change_type_scores = {
            'infrastructure_clearing': 95,    # Road/utility clearing
            'systematic_development': 90,     # Planned subdivisions  
            'industrial_expansion': 85,       # Factory/warehouse expansion
            'tourism_development': 80,        # Resort/hotel clearing
            'residential_sprawl': 70,         # Suburban expansion
            'agricultural_conversion': 40,    # Farm -> development
            'random_clearing': 20,            # Scattered small clearings
            'agricultural_rotation': 5        # Seasonal farming
        }

    def _load_strategic_regions(self) -> Dict[str, Dict[str, Any]]:
        """Load strategic region data with investment priorities"""
        return {
            'yogyakarta_periurban': {
                'strategic_value': 85,
                'growth_trajectory': 'high',
                'competition_level': 'medium',
                'infrastructure_plans': ['new_international_airport', 'toll_road_extension'],
                'upside_potential': 'high'
            },
            'gunungkidul_east': {
                'strategic_value': 92,  # HIGH OPPORTUNITY
                'growth_trajectory': 'explosive',
                'competition_level': 'low',  # Still under the radar
                'infrastructure_plans': ['coastal_highway', 'tourism_corridor', 'geothermal_access'],
                'upside_potential': 'extreme'
            },
            'kulonprogo_west': {
                'strategic_value': 88,
                'growth_trajectory': 'high',
                'competition_level': 'medium',
                'infrastructure_plans': ['airport_connector', 'industrial_zone'],
                'upside_potential': 'high'
            },
            'bantul_south': {
                'strategic_value': 75,
                'growth_trajectory': 'medium',
                'competition_level': 'high',  # Already competitive
                'infrastructure_plans': ['urban_expansion'],
                'upside_potential': 'medium'
            },
            'sleman_north': {
                'strategic_value': 70,
                'growth_trajectory': 'medium',
                'competition_level': 'high',
                'infrastructure_plans': ['university_expansion'],
                'upside_potential': 'medium'
            },
            'solo_expansion': {
                'strategic_value': 82,
                'growth_trajectory': 'high',
                'competition_level': 'medium',
                'infrastructure_plans': ['airport_upgrade', 'industrial_corridor'],
                'upside_potential': 'high'
            },
            'semarang_industrial': {
                'strategic_value': 78,
                'growth_trajectory': 'steady',
                'competition_level': 'high',
                'infrastructure_plans': ['port_expansion', 'rail_freight'],
                'upside_potential': 'medium'
            },
            'surakarta_suburbs': {
                'strategic_value': 80,
                'growth_trajectory': 'high',
                'competition_level': 'medium',
                'infrastructure_plans': ['ring_road', 'logistics_hub'],
                'upside_potential': 'high'
            },
            'magelang_corridor': {
                'strategic_value': 73,
                'growth_trajectory': 'medium',
                'competition_level': 'low',
                'infrastructure_plans': ['tourism_highway'],
                'upside_potential': 'medium-high'
            }
        }

    def score_change_alert(self, 
                          region_name: str, 
                          change_data: Dict[str, Any],
                          bbox: Dict[str, float]) -> SpeculativeScore:
        """
        Convert a change detection alert into a speculative investment score
        
        Args:
            region_name: Name of the region
            change_data: Raw change detection results
            bbox: Bounding box coordinates
            
        Returns:
            SpeculativeScore with investment recommendation
        """
        
        # 1. Base Score: Change magnitude and area
        base_score = self._calculate_base_score(change_data)
        
        # 2. Infrastructure Score: Proximity to roads/development
        infrastructure_score = self._calculate_infrastructure_score(region_name, bbox, change_data)
        
        # 3. Development Pattern Score: Type and quality of changes
        pattern_score = self._calculate_development_pattern_score(change_data)
        
        # 4. Strategic Location Score: Regional investment potential
        strategic_score = self._calculate_strategic_score(region_name)
        
        # 5. Weighted Final Score (with price intelligence)
        final_score = self._calculate_weighted_score(
            base_score, infrastructure_score, pattern_score, strategic_score, region_name
        )
        
        # 6. Generate buy signal and reasoning
        buy_signal, confidence, reasoning = self._generate_recommendation(
            final_score, region_name, change_data
        )
        
        return SpeculativeScore(
            region_name=region_name,
            base_score=base_score,
            infrastructure_score=infrastructure_score,
            development_pattern_score=pattern_score,
            strategic_location_score=strategic_score,
            final_score=final_score,
            confidence=confidence,
            buy_signal=buy_signal,
            reasoning=reasoning
        )
    
    def _calculate_base_score(self, change_data: Dict[str, Any]) -> float:
        """Score based on raw change magnitude"""
        change_count = change_data.get('change_count', 0)
        area_hectares = change_data.get('total_area_m2', 0) / 10000
        
        # Optimal range: 500-5000 changes, 50-500 hectares
        # Too small = not significant, too large = already developed/noticed
        
        count_score = min(100, (change_count / 2000) * 100)
        area_score = min(100, (area_hectares / 200) * 100)
        
        # Penalize if too massive (likely already known)
        if change_count > 10000 or area_hectares > 1000:
            penalty = 0.7
        else:
            penalty = 1.0
            
        return (count_score + area_score) / 2 * penalty
    
    def _calculate_infrastructure_score(self, 
                                      region_name: str, 
                                      bbox: Dict[str, float],
                                      change_data: Dict[str, Any]) -> float:
        """Score based on real infrastructure proximity analysis"""
        
        try:
            # Use real infrastructure analysis
            if self.infrastructure_analyzer:
                infrastructure_analysis = self.infrastructure_analyzer.analyze_infrastructure_context(
                    bbox, region_name)
                base_score = infrastructure_analysis.get('infrastructure_score', 50)
                construction_projects = infrastructure_analysis.get('construction_projects', [])
            else:
                infrastructure_analysis = None
                base_score = 50
                construction_projects = []
            
            # Boost for change patterns that suggest infrastructure development
            change_types = change_data.get('change_types', {})
            pattern_boost = 0
            
            # Look for linear/systematic patterns (roads, utilities)
            if self._detect_linear_patterns(change_types):
                pattern_boost += 15
                
            # Look for clustered development (planned subdivisions)
            if self._detect_clustered_development(change_types):
                pattern_boost += 10
                
            # Construction projects boost
            if construction_projects:
                pattern_boost += len(construction_projects) * 5
            
            final_score = min(100, base_score + pattern_boost)
            
            logger.debug(f"Infrastructure score for {region_name}: {final_score} (base: {base_score}, boost: {pattern_boost})")
            return final_score
            
        except Exception as e:
            logger.warning(f"Infrastructure analysis failed for {region_name}: {e}")
            # Fallback to original heuristic method
            return self._calculate_infrastructure_score_fallback(region_name, change_data)

    def _calculate_infrastructure_score_fallback(self, region_name: str, change_data: Dict[str, Any]) -> float:
        """Fallback infrastructure scoring using original heuristic method"""
        
        base_infrastructure_score = 50  # Default
        
        # Boost for regions with known infrastructure plans
        region_info = self.strategic_regions.get(region_name, {})
        infrastructure_plans = region_info.get('infrastructure_plans', [])
        
        infrastructure_boost = len(infrastructure_plans) * 10
        
        # Boost for change patterns that suggest infrastructure
        change_types = change_data.get('change_types', {})
        
        # Look for linear/systematic patterns (roads, utilities)
        if self._detect_linear_patterns(change_types):
            infrastructure_boost += 30
            
        # Look for clustered development (planned subdivisions)
        if self._detect_clustered_development(change_types):
            infrastructure_boost += 20
            
        return min(100, base_infrastructure_score + infrastructure_boost)

    def get_coverage_by_island(self) -> Dict[str, Dict[str, Any]]:
        """Get coverage data organized by island"""
        return {
            'java': {'regions': ['bantul', 'sleman', 'yogyakarta', 'kulon_progo'], 'total_regions': 4},
            'sumatra': {'regions': [], 'total_regions': 0},
            'other': {'regions': [], 'total_regions': 0}
        }
    
    def _calculate_development_pattern_score(self, change_data: Dict[str, Any]) -> float:
        """Score the type and quality of development patterns"""
        
        change_types = change_data.get('change_types', {})
        total_changes = sum(change_types.values()) if change_types else 1
        
        pattern_score = 0
        
        # Analyze change type distribution to infer development type
        if change_types:
            # Type 3 (likely development) + Type 4 (likely infrastructure) = good signal
            development_ratio = (change_types.get('3', 0) + change_types.get('4', 0)) / total_changes
            pattern_score += development_ratio * 80
            
            # Type 2 (vegetation loss) should be moderate - clearing for development
            veg_loss_ratio = change_types.get('2', 0) / total_changes
            if 0.2 <= veg_loss_ratio <= 0.5:  # Optimal range
                pattern_score += 20
                
            # Penalize if mostly agricultural (Type 5, 6)
            ag_ratio = (change_types.get('5', 0) + change_types.get('6', 0)) / total_changes
            if ag_ratio > 0.6:
                pattern_score *= 0.5
        
        return min(100, pattern_score)
    
    def _calculate_strategic_score(self, region_name: str) -> float:
        """Score based on regional strategic investment potential"""
        
        region_info = self.strategic_regions.get(region_name, {})
        
        strategic_value = region_info.get('strategic_value', 50)
        growth_trajectory = region_info.get('growth_trajectory', 'medium')
        competition_level = region_info.get('competition_level', 'medium')
        
        # Boost for high growth, low competition
        growth_multiplier = {
            'explosive': 1.3,
            'high': 1.2,
            'medium': 1.0,
            'slow': 0.8
        }.get(growth_trajectory, 1.0)
        
        competition_multiplier = {
            'low': 1.2,      # Less competition = better opportunity
            'medium': 1.0,
            'high': 0.8      # High competition = harder to profit
        }.get(competition_level, 1.0)
        
        return min(100, strategic_value * growth_multiplier * competition_multiplier)
    
    def _calculate_weighted_score(self, base: float, infra: float, pattern: float, strategic: float, region_name: Optional[str] = None) -> float:
        """Calculate weighted composite score with price intelligence"""
        
        # Get price intelligence boost
        price_boost = 0
        if region_name:
            try:
                # This is a simplified price analysis - full analysis in generate_recommendation
                if self.price_intelligence:
                    regional_data = self.price_intelligence.regional_market_data.get(region_name, {})
                    growth_rate = regional_data.get('growth_rate_annual', 0.12)
                    maturity = regional_data.get('market_maturity', 'developing')
                else:
                    growth_rate = 0.12
                    maturity = 'developing'
                
                # Boost for high growth potential
                if growth_rate > 0.20:
                    price_boost += 15
                elif growth_rate > 0.15: 
                    price_boost += 10
                    
                # Boost for frontier/emerging markets
                if maturity in ['frontier', 'emerging']:
                    price_boost += 10
                    
            except Exception as e:
                logger.debug(f"Price intelligence boost failed: {e}")
        
        # Updated weights with price intelligence factor
        weights = {
            'base': 0.15,       # Raw change magnitude
            'infra': 0.35,      # Infrastructure proximity (most important)
            'pattern': 0.25,    # Development pattern quality
            'strategic': 0.25   # Regional strategic value (increased)
        }
        
        base_score = (base * weights['base'] + 
                     infra * weights['infra'] + 
                     pattern * weights['pattern'] + 
                     strategic * weights['strategic'])
        
        return min(100, base_score + price_boost)
    
    def _generate_recommendation(self, 
                               final_score: float, 
                               region_name: str, 
                               change_data: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Generate buy/watch/ignore recommendation with reasoning"""
        
        reasoning = []
        confidence = 0.7  # Base confidence
        
        # Buy signal thresholds
        if final_score >= 85:
            buy_signal = "BUY"
            confidence = 0.9
            reasoning.append(f"HIGH OPPORTUNITY: Score {final_score:.1f}/100")
        elif final_score >= 70:
            buy_signal = "WATCH"
            confidence = 0.8
            reasoning.append(f"MONITOR CLOSELY: Score {final_score:.1f}/100")
        elif final_score >= 50:
            buy_signal = "INVESTIGATE"
            confidence = 0.6
            reasoning.append(f"POTENTIAL: Score {final_score:.1f}/100 - needs ground truth")
        else:
            buy_signal = "IGNORE"
            confidence = 0.7
            reasoning.append(f"LOW PRIORITY: Score {final_score:.1f}/100")
        
        # Add specific reasoning
        region_info = self.strategic_regions.get(region_name, {})
        
        if region_info.get('competition_level') == 'low':
            reasoning.append("✓ Low competition area - under the radar")
            
        if 'airport' in str(region_info.get('infrastructure_plans', [])).lower():
            reasoning.append("✓ Airport infrastructure development planned")
            
        if region_info.get('upside_potential') == 'extreme':
            reasoning.append("✓ EXTREME upside potential identified")
            
        # Add price intelligence insights
        try:
            if self.price_intelligence:
                price_data = self.price_intelligence.regional_market_data.get(region_name, {})
                growth_rate = price_data.get('growth_rate_annual', 0.12)
                maturity = price_data.get('market_maturity', 'developing')
            else:
                growth_rate = 0.12
                maturity = 'developing'
            
            if growth_rate > 0.20:
                reasoning.append(f"💰 High growth market: {growth_rate:.1%} annual appreciation expected")
            elif growth_rate > 0.15:
                reasoning.append(f"📈 Strong growth expected: {growth_rate:.1%} annually")
                
            if maturity == 'frontier':
                reasoning.append("🌟 FRONTIER MARKET: Highest risk, highest reward potential")
            elif maturity == 'emerging':
                reasoning.append("⭐ EMERGING MARKET: Strong development trajectory")
                
        except Exception as e:
            logger.debug(f"Price intelligence reasoning failed: {e}")
            
        change_count = change_data.get('change_count', 0)
        area_ha = change_data.get('total_area_m2', 0) / 10000
        
        if 1000 <= change_count <= 5000:
            reasoning.append(f"✓ Optimal change magnitude: {change_count:,} changes")
            
        if 100 <= area_ha <= 500:
            reasoning.append(f"✓ Significant but manageable area: {area_ha:.1f} hectares")
            
        return buy_signal, confidence, reasoning
    
    def _detect_linear_patterns(self, change_types: Dict[str, int]) -> bool:
        """Detect if changes suggest linear infrastructure development"""
        # Heuristic: Type 4 changes (infrastructure) + systematic pattern
        infrastructure_changes = change_types.get('4', 0)
        total_changes = sum(change_types.values()) if change_types else 1
        
        # High ratio of infrastructure changes suggests roads/utilities
        return (infrastructure_changes / total_changes) > 0.3
    
    def _detect_clustered_development(self, change_types: Dict[str, int]) -> bool:
        """Detect if changes suggest planned subdivision development"""
        # Heuristic: Balanced mix of development types
        dev_changes = change_types.get('3', 0)
        veg_loss = change_types.get('2', 0)
        total_changes = sum(change_types.values()) if change_types else 1
        
        # Clustered development shows clearing + building in balanced ratio
        dev_ratio = dev_changes / total_changes
        clearing_ratio = veg_loss / total_changes
        
        return (0.3 <= dev_ratio <= 0.6) and (0.2 <= clearing_ratio <= 0.4)

    def generate_investment_report(self, 
                                 scored_regions: List[SpeculativeScore]) -> Dict[str, Any]:
        """Generate executive summary for investment decisions"""
        
        # Sort by final score
        sorted_regions = sorted(scored_regions, key=lambda x: x.final_score, reverse=True)
        
        buy_opportunities = [r for r in sorted_regions if r.buy_signal == "BUY"]
        watch_list = [r for r in sorted_regions if r.buy_signal == "WATCH"]
        investigate = [r for r in sorted_regions if r.buy_signal == "INVESTIGATE"]
        
        report = {
            'executive_summary': {
                'total_regions_analyzed': len(scored_regions),
                'immediate_buy_opportunities': len(buy_opportunities),
                'watch_list_regions': len(watch_list),
                'investigation_targets': len(investigate),
                'top_opportunity': sorted_regions[0].region_name if sorted_regions else None,
                'top_score': sorted_regions[0].final_score if sorted_regions else 0
            },
            'buy_recommendations': [
                {
                    'region': r.region_name,
                    'score': r.final_score,
                    'confidence': r.confidence,
                    'reasoning': r.reasoning
                } for r in buy_opportunities
            ],
            'watch_list': [
                {
                    'region': r.region_name,
                    'score': r.final_score,
                    'reasoning': r.reasoning[:2]  # Top 2 reasons
                } for r in watch_list
            ],
            'regional_rankings': [
                {
                    'rank': i+1,
                    'region': r.region_name,
                    'score': r.final_score,
                    'signal': r.buy_signal,
                    'confidence': r.confidence
                } for i, r in enumerate(sorted_regions)
            ]
        }
        
        return report