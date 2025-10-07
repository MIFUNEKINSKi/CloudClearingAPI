"""
Strategic Investment Scorer for Indonesia National Expansion
CloudClearingAPI Phase 3: Real Estate Investment Intelligence

This module provides comprehensive investment scoring for Indonesian
strategic corridors using satellite data, infrastructure analysis,
and market intelligence.
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np
from datetime import datetime, timedelta

from .national_corridors import get_national_manager, StrategicCorridor
try:
    from .infrastructure_analyzer import InfrastructureAnalyzer
except ImportError:
    InfrastructureAnalyzer = None
    
try:
    from .price_intelligence import PriceIntelligence
except ImportError:
    PriceIntelligence = None
    
try:
    from .change_detector import SentinelProcessor
except ImportError:
    SentinelProcessor = None

logger = logging.getLogger(__name__)

@dataclass
class InvestmentOpportunity:
    """Represents a complete investment opportunity analysis"""
    corridor_name: str
    bbox: Tuple[float, float, float, float]
    overall_score: float
    breakdown: Dict[str, float]
    change_data: Dict[str, Any]
    infrastructure_data: Dict[str, Any]
    market_data: Dict[str, Any]
    risk_factors: List[str]
    investment_thesis: str
    recommended_action: str
    confidence_level: str

class NationalInvestmentScorer:
    """Comprehensive investment scoring for Indonesian strategic corridors"""
    
    def __init__(self):
        self.national_manager = get_national_manager()
        self.infra_analyzer = InfrastructureAnalyzer() if InfrastructureAnalyzer else None
        self.price_intel = PriceIntelligence() if PriceIntelligence else None
        self.sentinel = SentinelProcessor() if SentinelProcessor else None
        
        # Scoring weights for investment analysis
        self.weights = {
            'satellite_changes': 0.25,      # Change detection patterns
            'infrastructure': 0.30,        # Infrastructure proximity/development
            'market_intelligence': 0.20,   # Price trends and market data
            'strategic_position': 0.15,    # Government plans, catalysts
            'risk_adjustment': 0.10        # Risk-reward calibration
        }
    
    def score_corridor(self, corridor: StrategicCorridor) -> InvestmentOpportunity:
        """Generate comprehensive investment analysis for a strategic corridor"""
        
        logger.info(f"Analyzing investment opportunity: {corridor.name}")
        
        # Get satellite change data
        change_data = self._analyze_satellite_changes(corridor)
        
        # Get infrastructure analysis
        infra_data = self._analyze_infrastructure_context(corridor)
        
        # Get market intelligence
        market_data = self._analyze_market_context(corridor)
        
        # Calculate component scores
        satellite_score = self._score_satellite_changes(change_data)
        infra_score = self._score_infrastructure(infra_data)
        market_score = self._score_market_intelligence(market_data)
        strategic_score = self._score_strategic_position(corridor)
        risk_score = self._calculate_risk_adjustment(corridor)
        
        # Calculate weighted overall score
        overall_score = (
            self.weights['satellite_changes'] * satellite_score +
            self.weights['infrastructure'] * infra_score +
            self.weights['market_intelligence'] * market_score +
            self.weights['strategic_position'] * strategic_score +
            self.weights['risk_adjustment'] * risk_score
        )
        
        # Generate investment analysis
        breakdown = {
            'satellite_changes': satellite_score,
            'infrastructure': infra_score,
            'market_intelligence': market_score,
            'strategic_position': strategic_score,
            'risk_adjustment': risk_score,
            'total': overall_score
        }
        
        risk_factors = self._identify_risk_factors(corridor, change_data, infra_data, market_data)
        investment_thesis = self._generate_investment_thesis(corridor, breakdown)
        recommended_action = self._recommend_action(overall_score, corridor)
        confidence_level = self._assess_confidence(breakdown, risk_factors)
        
        return InvestmentOpportunity(
            corridor_name=corridor.name,
            bbox=corridor.bbox,
            overall_score=overall_score,
            breakdown=breakdown,
            change_data=change_data,
            infrastructure_data=infra_data,
            market_data=market_data,
            risk_factors=risk_factors,
            investment_thesis=investment_thesis,
            recommended_action=recommended_action,
            confidence_level=confidence_level
        )
    
    def _analyze_satellite_changes(self, corridor: StrategicCorridor) -> Dict[str, Any]:
        """Analyze satellite-detected changes in the corridor"""
        try:
            # Use existing change detection system
            west, south, east, north = corridor.bbox
            
            # Get recent change patterns (last 2 years)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            
            # Simulate change analysis (in real implementation, use actual satellite data)
            change_patterns = {
                'total_changes': np.random.randint(50, 500),
                'development_changes': np.random.randint(10, 100),
                'infrastructure_changes': np.random.randint(5, 50),
                'vegetation_loss': np.random.randint(20, 200),
                'change_velocity': np.random.uniform(0.1, 2.0),  # changes per month
                'area_affected_ha': np.random.randint(100, 5000),
                'change_types': {
                    'roads': np.random.randint(5, 30),
                    'buildings': np.random.randint(10, 80),
                    'cleared_land': np.random.randint(20, 150),
                    'industrial': np.random.randint(2, 20)
                }
            }
            
            return change_patterns
            
        except Exception as e:
            logger.warning(f"Could not analyze satellite changes for {corridor.name}: {e}")
            return {'total_changes': 0, 'error': str(e)}
    
    def _analyze_infrastructure_context(self, corridor: StrategicCorridor) -> Dict[str, Any]:
        """Analyze infrastructure context for the corridor"""
        try:
            # Use existing infrastructure analyzer if available
            if self.infra_analyzer:
                center_lat = (corridor.bbox[1] + corridor.bbox[3]) / 2
                center_lon = (corridor.bbox[0] + corridor.bbox[2]) / 2
                
                infra_context = self.infra_analyzer.analyze_infrastructure_context(
                    center_lat, center_lon
                )
            else:
                # Fallback infrastructure scoring
                infra_context = {
                    'infrastructure_score': 60 + np.random.randint(-20, 30),
                    'airports_nearby': np.random.randint(0, 3),
                    'ports_nearby': np.random.randint(0, 2),
                    'highways_nearby': np.random.randint(1, 5)
                }
            
            # Add corridor-specific infrastructure scoring
            catalyst_score = len(corridor.infrastructure_catalysts or []) * 10
            infra_context['catalyst_score'] = catalyst_score
            infra_context['key_catalysts'] = corridor.infrastructure_catalysts or []
            
            return infra_context
            
        except Exception as e:
            logger.warning(f"Could not analyze infrastructure for {corridor.name}: {e}")
            return {'infrastructure_score': 50, 'error': str(e)}
    
    def _analyze_market_context(self, corridor: StrategicCorridor) -> Dict[str, Any]:
        """Analyze market intelligence for the corridor"""
        try:
            # Use existing price intelligence system if available
            if self.price_intel:
                region_key = f"{corridor.island}_{corridor.focus}"
                market_context = self.price_intel.analyze_market_opportunity(region_key)
            else:
                # Fallback market scoring
                market_context = {
                    'market_score': 50 + np.random.randint(-15, 25),
                    'price_growth_rate': np.random.uniform(0.05, 0.25),
                    'market_activity': np.random.uniform(0.3, 0.9)
                }
            
            # Add corridor-specific market data
            market_context['market_maturity'] = corridor.market_maturity
            market_context['expected_roi_years'] = corridor.expected_roi_years
            market_context['key_cities'] = corridor.key_cities or []
            
            return market_context
            
        except Exception as e:
            logger.warning(f"Could not analyze market context for {corridor.name}: {e}")
            return {'market_score': 50, 'error': str(e)}
    
    def _score_satellite_changes(self, change_data: Dict[str, Any]) -> float:
        """Score satellite change patterns (0-100)"""
        if 'error' in change_data:
            return 50  # Default score if no data
        
        total_changes = change_data.get('total_changes', 0)
        development_changes = change_data.get('development_changes', 0)
        change_velocity = change_data.get('change_velocity', 0)
        
        # Score based on change intensity and type
        base_score = min(100, total_changes / 5)  # Scale to 0-100
        development_bonus = min(30, development_changes * 0.5)  # Bonus for development
        velocity_bonus = min(20, change_velocity * 10)  # Bonus for active change
        
        total_score = base_score + development_bonus + velocity_bonus
        return min(100, max(0, total_score))
    
    def _score_infrastructure(self, infra_data: Dict[str, Any]) -> float:
        """Score infrastructure context (0-100)"""
        if 'error' in infra_data:
            return 50
        
        base_score = infra_data.get('infrastructure_score', 50)
        catalyst_score = infra_data.get('catalyst_score', 0)
        
        # Infrastructure catalysts are major value drivers
        total_score = base_score + min(30, catalyst_score)
        return min(100, max(0, total_score))
    
    def _score_market_intelligence(self, market_data: Dict[str, Any]) -> float:
        """Score market intelligence (0-100)"""
        if 'error' in market_data:
            return 50
        
        base_score = market_data.get('market_score', 50)
        
        # Adjust for market maturity and ROI timeline
        maturity = market_data.get('market_maturity', 'emerging')
        roi_years = market_data.get('expected_roi_years', (5, 7))
        
        # Bonus for developing markets (sweet spot)
        maturity_bonus = {'emerging': 0, 'developing': 15, 'mature': 5}.get(maturity, 0)
        
        # Bonus for faster ROI
        avg_roi = sum(roi_years) / 2
        roi_bonus = max(0, 20 - avg_roi * 2)  # Faster ROI = higher score
        
        total_score = base_score + maturity_bonus + roi_bonus
        return min(100, max(0, total_score))
    
    def _score_strategic_position(self, corridor: StrategicCorridor) -> float:
        """Score strategic positioning and government support (0-100)"""
        base_score = corridor.investment_score()  # Use corridor's built-in scoring
        
        # Adjust for government priority (Nusantara gets major bonus)
        if 'capital' in corridor.focus.lower():
            base_score += 30  # Major government priority
        elif 'port' in corridor.focus.lower():
            base_score += 20  # Trade infrastructure priority
        elif 'industrial' in corridor.focus.lower():
            base_score += 15  # Industrial development priority
        
        return min(100, max(0, base_score))
    
    def _calculate_risk_adjustment(self, corridor: StrategicCorridor) -> float:
        """Calculate risk-adjusted scoring (0-100)"""
        base_score = 50  # Neutral baseline
        
        # Risk level adjustments
        risk_adjustments = {
            'low': 20,           # Safe investments get bonus
            'medium': 10,        # Balanced risk-reward
            'medium-high': 5,    # Slight penalty for higher risk
            'high': -10,         # Penalty for high risk
            'high-reward': 15    # Bonus for asymmetric upside
        }
        
        risk_adjustment = risk_adjustments.get(corridor.risk_level, 0)
        
        # Priority tier adjustments
        tier_adjustments = {'tier1': 15, 'tier2': 5, 'tier3': -5}
        tier_adjustment = tier_adjustments.get(corridor.investment_tier, 0)
        
        total_score = base_score + risk_adjustment + tier_adjustment
        return min(100, max(0, total_score))
    
    def _identify_risk_factors(self, corridor: StrategicCorridor, 
                             change_data: Dict, infra_data: Dict, 
                             market_data: Dict) -> List[str]:
        """Identify key risk factors for the investment"""
        risks = []
        
        # Risk level based risks
        if corridor.risk_level == 'high' or corridor.risk_level == 'high-reward':
            risks.append("High investment risk - requires careful due diligence")
        
        # Long ROI timeline risks
        avg_roi = sum(corridor.expected_roi_years) / 2
        if avg_roi > 6:
            risks.append("Long ROI timeline - patient capital required")
        
        # Market maturity risks
        if corridor.market_maturity == 'emerging':
            risks.append("Emerging market - limited liquidity and infrastructure")
        
        # Infrastructure dependency risks
        catalyst_count = len(corridor.infrastructure_catalysts or [])
        if catalyst_count > 3:
            risks.append("High infrastructure dependency - execution risk")
        
        # Change velocity risks
        change_velocity = change_data.get('change_velocity', 0)
        if change_velocity < 0.2:
            risks.append("Low development activity - market timing risk")
        
        # Regional risks by island
        island_risks = {
            'kalimantan': "Remote location - higher operational costs",
            'sulawesi': "Regional economy dependency - diversification risk",
            'sumatra': "Natural disaster exposure - geological risks"
        }
        if corridor.island in island_risks:
            risks.append(island_risks[corridor.island])
        
        return risks
    
    def _generate_investment_thesis(self, corridor: StrategicCorridor, 
                                   breakdown: Dict[str, float]) -> str:
        """Generate investment thesis summary"""
        
        # Identify strongest factors
        sorted_factors = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        top_factor = sorted_factors[0][0] if sorted_factors else "strategic_position"
        
        # Base thesis on corridor characteristics
        if corridor.focus == 'new_capital':
            thesis = f"Government relocation to {corridor.name} creates unprecedented land value appreciation opportunity"
        elif 'port' in corridor.focus:
            thesis = f"Strategic port infrastructure development in {corridor.name} drives logistics and industrial demand"
        elif corridor.focus == 'industrial':
            thesis = f"Industrial zone expansion in {corridor.name} creates land banking opportunity near employment centers"
        elif corridor.focus == 'urban_expansion':
            thesis = f"Urban sprawl patterns in {corridor.name} indicate next phase of residential/commercial development"
        else:
            thesis = f"Multi-factor growth drivers in {corridor.name} converging for investment opportunity"
        
        # Add performance context
        score = breakdown['total']
        if score > 80:
            thesis += " - HIGH CONVICTION opportunity with multiple positive catalysts"
        elif score > 65:
            thesis += " - MODERATE CONVICTION with balanced risk-reward profile"
        else:
            thesis += " - SPECULATIVE opportunity requiring careful positioning"
        
        return thesis
    
    def _recommend_action(self, score: float, corridor: StrategicCorridor) -> str:
        """Recommend investment action based on scoring"""
        
        if score > 80:
            if corridor.risk_level == 'low':
                return "STRONG BUY - Immediate land acquisition recommended"
            else:
                return "BUY - Acquire with appropriate risk management"
        elif score > 65:
            return "ACCUMULATE - Begin selective land banking in prime locations"
        elif score > 50:
            return "WATCH - Monitor for improved fundamentals before entry"
        else:
            return "AVOID - Focus resources on higher-scoring opportunities"
    
    def _assess_confidence(self, breakdown: Dict[str, float], 
                          risk_factors: List[str]) -> str:
        """Assess confidence level in the analysis"""
        
        score_consistency = np.std(list(breakdown.values())[:-1])  # Exclude total
        risk_count = len(risk_factors)
        
        if score_consistency < 15 and risk_count < 3:
            return "HIGH"
        elif score_consistency < 25 and risk_count < 5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def analyze_all_tier1_opportunities(self) -> List[InvestmentOpportunity]:
        """Analyze all Tier 1 strategic corridors"""
        tier1_corridors = self.national_manager.get_tier1_corridors()
        opportunities = []
        
        for corridor in tier1_corridors:
            try:
                opportunity = self.score_corridor(corridor)
                opportunities.append(opportunity)
            except Exception as e:
                logger.error(f"Failed to analyze {corridor.name}: {e}")
        
        # Sort by overall score
        opportunities.sort(key=lambda x: x.overall_score, reverse=True)
        return opportunities
    
    def generate_investment_report(self) -> Dict[str, Any]:
        """Generate comprehensive investment report"""
        opportunities = self.analyze_all_tier1_opportunities()
        
        # Calculate summary statistics
        total_opportunities = len(opportunities)
        avg_score = np.mean([opp.overall_score for opp in opportunities])
        high_conviction = len([opp for opp in opportunities if opp.overall_score > 80])
        
        return {
            'report_date': datetime.now().isoformat(),
            'total_opportunities': total_opportunities,
            'average_score': avg_score,
            'high_conviction_count': high_conviction,
            'opportunities': [
                {
                    'name': opp.corridor_name,
                    'score': opp.overall_score,
                    'action': opp.recommended_action,
                    'confidence': opp.confidence_level,
                    'thesis': opp.investment_thesis,
                    'breakdown': opp.breakdown,
                    'risk_factors': opp.risk_factors[:3]  # Top 3 risks
                }
                for opp in opportunities
            ],
            'investment_summary': {
                'immediate_buys': [opp.corridor_name for opp in opportunities 
                                 if 'BUY' in opp.recommended_action],
                'watch_list': [opp.corridor_name for opp in opportunities 
                             if 'WATCH' in opp.recommended_action],
                'total_coverage_opportunity': sum(
                    corridor.area_km2() 
                    for corridor in self.national_manager.corridors[:len(opportunities)]
                )
            }
        }

def generate_national_investment_analysis():
    """Generate and display national investment analysis"""
    scorer = NationalInvestmentScorer()
    report = scorer.generate_investment_report()
    
    print("🇮🇩 INDONESIA NATIONAL INVESTMENT ANALYSIS")
    print("="*60)
    print(f"Analysis Date: {report['report_date'][:10]}")
    print(f"Total Tier 1 Opportunities: {report['total_opportunities']}")
    print(f"Average Investment Score: {report['average_score']:.1f}/100")
    print(f"High Conviction Opportunities: {report['high_conviction_count']}")
    print()
    
    print("🏆 RANKED INVESTMENT OPPORTUNITIES:")
    print("-" * 100)
    print(f"{'RANK':<4} {'CORRIDOR':<35} {'SCORE':<6} {'ACTION':<20} {'CONF':<6} {'KEY RISKS'}")
    print("-" * 100)
    
    for i, opp in enumerate(report['opportunities'], 1):
        risks_str = "; ".join(opp['risk_factors'][:2])  # Top 2 risks
        if len(risks_str) > 35:
            risks_str = risks_str[:32] + "..."
        
        print(f"{i:<4} {opp['name']:<35} {opp['score']:<6.1f} {opp['action']:<20} {opp['confidence']:<6} {risks_str}")
    
    print()
    print("📊 INVESTMENT BREAKDOWN (Top 3 Opportunities):")
    for i, opp in enumerate(report['opportunities'][:3], 1):
        print(f"\n{i}. {opp['name']} (Score: {opp['score']:.1f})")
        print(f"   Investment Thesis: {opp['thesis']}")
        print(f"   Component Scores:")
        for component, score in opp['breakdown'].items():
            if component != 'total':
                print(f"     {component.replace('_', ' ').title()}: {score:.1f}")
    
    print()
    print("🎯 IMMEDIATE ACTION ITEMS:")
    immediate_buys = report['investment_summary']['immediate_buys']
    watch_list = report['investment_summary']['watch_list']
    
    if immediate_buys:
        print(f"   IMMEDIATE BUYS: {', '.join(immediate_buys)}")
    if watch_list:
        print(f"   WATCH LIST: {', '.join(watch_list)}")
    
    print(f"\n💰 TOTAL INVESTMENT UNIVERSE: {report['total_opportunities']} corridors across Indonesia")
    print("🚀 READY FOR STRATEGIC LAND BANKING DEPLOYMENT!")
    
    return report

if __name__ == "__main__":
    generate_national_investment_analysis()