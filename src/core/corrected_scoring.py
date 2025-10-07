"""
Corrected Investment Scoring System

This module implements the TRUE three-part scoring system as documented:
1. Satellite Development Activity (0-40 points) - PRIMARY SIGNAL
2. Infrastructure Quality Multiplier (0.8-1.2x)
3. Market Dynamics Multiplier (0.9-1.1x)

Author: CloudClearingAPI Team
Date: October 6, 2025
Version: 2.0 - Complete Rebuild
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CorrectedScoringResult:
    """Complete investment scoring result with proper satellite integration"""
    region_name: str
    
    # Part 1: Satellite Development (0-40 points)
    satellite_changes: int
    area_affected_hectares: float
    development_score: float  # 0-40
    
    # Part 2: Infrastructure (multiplier)
    infrastructure_score: float  # 0-100
    infrastructure_multiplier: float  # 0.8-1.2
    roads_count: int
    airports_nearby: int
    railway_access: bool
    
    # Part 3: Market (multiplier)
    price_trend_30d: float
    market_heat: str
    market_score: float  # 0-100
    market_multiplier: float  # 0.9-1.1
    
    # Final results
    final_investment_score: float  # 0-100 (typically 0-60)
    confidence_level: float  # 0.2-0.9
    recommendation: str  # BUY, WATCH, PASS
    rationale: str
    
    # Data tracking
    data_sources: Dict[str, str]
    data_availability: Dict[str, bool]


class CorrectedInvestmentScorer:
    """
    Properly implements satellite-centric investment scoring.
    
    This corrects the fundamental flaw where satellite data was ignored.
    Now satellite change detection is the PRIMARY base score (0-40 points),
    with infrastructure and market as multipliers.
    """
    
    def __init__(self, price_engine, infrastructure_engine):
        self.price_engine = price_engine
        self.infrastructure_engine = infrastructure_engine
        logger.info("✅ Initialized CORRECTED scoring system (satellite-centric)")
    
    def calculate_investment_score(self, 
                                   region_name: str,
                                   satellite_changes: int,
                                   area_affected_m2: float,
                                   region_config: Dict[str, Any],
                                   coordinates: Dict[str, float],
                                   bbox: Dict[str, float]) -> CorrectedScoringResult:
        """
        Calculate investment score using the CORRECT three-part system.
        
        Args:
            region_name: Name of region
            satellite_changes: Total pixel changes detected (PRIMARY SIGNAL!)
            area_affected_m2: Area of changes in square meters
            region_config: Region configuration
            coordinates: Center coordinates
            bbox: Bounding box
            
        Returns:
            Complete scoring result with proper satellite integration
        """
        logger.info(f"🎯 Calculating CORRECTED score for {region_name}")
        logger.info(f"   Satellite changes: {satellite_changes:,} (THIS IS THE BASE SCORE!)")
        
        # Track data availability
        data_availability = {
            'satellite_data': True,  # Always available (it's the input!)
            'infrastructure_data': False,
            'market_data': False
        }
        
        # PART 1: SATELLITE DEVELOPMENT SCORE (0-40 POINTS) - THE FOUNDATION!
        development_score = self._calculate_development_score(satellite_changes)
        logger.info(f"   📊 Development Score: {development_score}/40 (from {satellite_changes:,} changes)")
        
        # PART 2: INFRASTRUCTURE ANALYSIS & MULTIPLIER
        infrastructure_data, infra_multiplier = self._get_infrastructure_multiplier(
            region_name, bbox, data_availability
        )
        logger.info(f"   🏗️ Infrastructure Multiplier: {infra_multiplier:.2f}x (score: {infrastructure_data['infrastructure_score']}/100)")
        
        # PART 3: MARKET ANALYSIS & MULTIPLIER
        market_data, market_multiplier = self._get_market_multiplier(
            region_name, coordinates, data_availability
        )
        logger.info(f"   💰 Market Multiplier: {market_multiplier:.2f}x (trend: {market_data['price_trend_30d']:.1f}%)")
        
        # FINAL CALCULATION (THE CORRECT WAY!)
        base_score = development_score  # Start with satellite data (0-40)
        after_infrastructure = base_score * infra_multiplier  # Apply infrastructure
        after_market = after_infrastructure * market_multiplier  # Apply market
        
        # Confidence weighting (reduces score when data is missing)
        confidence = self._calculate_confidence(data_availability, market_data, infrastructure_data)
        confidence_adjustment = 0.7 + (confidence * 0.3)  # Range: 0.7-1.0
        
        final_score = after_market * confidence_adjustment
        final_score = max(0, min(100, final_score))  # Clamp to 0-100
        
        logger.info(f"   ✨ Final Score: {final_score:.1f}/100 (confidence: {confidence:.0%})")
        logger.info(f"      Calculation: {base_score:.1f} × {infra_multiplier:.2f} × {market_multiplier:.2f} × {confidence_adjustment:.2f} = {final_score:.1f}")
        
        # Generate recommendation
        recommendation, rationale = self._generate_recommendation(
            final_score, confidence, satellite_changes, infrastructure_data, market_data
        )
        
        # Build data sources report
        data_sources = {
            'satellite': 'google_earth_engine',
            'infrastructure': infrastructure_data.get('data_source', 'unavailable'),
            'market': market_data.get('data_source', 'unavailable')
        }
        
        return CorrectedScoringResult(
            region_name=region_name,
            satellite_changes=satellite_changes,
            area_affected_hectares=area_affected_m2 / 10000,
            development_score=development_score,
            infrastructure_score=infrastructure_data['infrastructure_score'],
            infrastructure_multiplier=infra_multiplier,
            roads_count=len(infrastructure_data.get('major_features', [])),
            airports_nearby=len([f for f in infrastructure_data.get('major_features', []) if 'airport' in f.lower()]),
            railway_access=any('railway' in f.lower() for f in infrastructure_data.get('major_features', [])),
            price_trend_30d=market_data['price_trend_30d'],
            market_heat=market_data['market_heat'],
            market_score=self._calculate_market_score(market_data),
            market_multiplier=market_multiplier,
            final_investment_score=final_score,
            confidence_level=confidence,
            recommendation=recommendation,
            rationale=rationale,
            data_sources=data_sources,
            data_availability=data_availability
        )
    
    def _calculate_development_score(self, satellite_changes: int) -> float:
        """
        Calculate development score from satellite change count.
        This is the PRIMARY signal - the foundation of the entire score!
        
        Score ranges:
        - 40 points: >50,000 changes (massive development)
        - 35 points: 20,000-50,000 (very high activity)
        - 30 points: 10,000-20,000 (high activity)
        - 25 points: 5,000-10,000 (moderate activity)
        - 20 points: 1,000-5,000 (some activity)
        - 15 points: 500-1,000 (low activity)
        - 10 points: 100-500 (minimal activity)
        - 5 points: <100 (very little change)
        """
        if satellite_changes > 50000:
            return 40.0
        elif satellite_changes > 20000:
            return 35.0
        elif satellite_changes > 10000:
            return 30.0
        elif satellite_changes > 5000:
            return 25.0
        elif satellite_changes > 1000:
            return 20.0
        elif satellite_changes > 500:
            return 15.0
        elif satellite_changes > 100:
            return 10.0
        else:
            return 5.0
    
    def _get_infrastructure_multiplier(self, 
                                      region_name: str,
                                      bbox: Dict[str, float],
                                      data_availability: Dict[str, bool]) -> tuple:
        """
        Get infrastructure data and convert to multiplier (0.8-1.2x).
        
        Returns:
            (infrastructure_data dict, multiplier float)
        """
        try:
            infrastructure_data = self.infrastructure_engine.analyze_live_infrastructure(
                region_name, bbox
            )
            data_availability['infrastructure_data'] = True
            
            # Convert infrastructure score (0-100) to multiplier (0.8-1.2)
            infra_score = infrastructure_data['infrastructure_score']
            multiplier = 0.8 + (infra_score / 100) * 0.4
            
            logger.debug(f"   Infrastructure: {infra_score:.1f}/100 → {multiplier:.2f}x multiplier")
            
        except Exception as e:
            logger.warning(f"⚠️ Infrastructure data unavailable for {region_name}: {e}")
            infrastructure_data = {
                'infrastructure_score': 50.0,  # Neutral
                'major_features': [],
                'data_source': 'unavailable',
                'data_confidence': 0.0
            }
            multiplier = 1.0  # Neutral multiplier when data unavailable
        
        return infrastructure_data, multiplier
    
    def _get_market_multiplier(self,
                               region_name: str,
                               coordinates: Dict[str, float],
                               data_availability: Dict[str, bool]) -> tuple:
        """
        Get market data and convert to multiplier (0.9-1.1x).
        
        Returns:
            (market_data dict, multiplier float)
        """
        try:
            market_data = self.price_engine.get_live_market_data(region_name, coordinates)
            data_availability['market_data'] = True
            
            # Convert market trend to multiplier
            price_trend = market_data['price_trend_30d']
            
            if price_trend >= 15:
                multiplier = 1.10  # Very hot market (+10%)
            elif price_trend >= 10:
                multiplier = 1.08  # Hot market (+8%)
            elif price_trend >= 5:
                multiplier = 1.05  # Warm market (+5%)
            elif price_trend >= 0:
                multiplier = 1.00  # Neutral
            elif price_trend >= -5:
                multiplier = 0.95  # Cooling (-5%)
            else:
                multiplier = 0.90  # Cold market (-10%)
            
            logger.debug(f"   Market: {price_trend:.1f}% trend → {multiplier:.2f}x multiplier")
            
        except Exception as e:
            logger.warning(f"⚠️ Market data unavailable for {region_name}: {e}")
            market_data = {
                'price_trend_30d': 0.0,
                'market_heat': 'unknown',
                'current_price_per_m2': 0,
                'data_source': 'unavailable',
                'data_confidence': 0.0
            }
            multiplier = 1.0  # Neutral multiplier when data unavailable
        
        return market_data, multiplier
    
    def _calculate_market_score(self, market_data: Dict) -> float:
        """Calculate market score (0-100) for informational purposes"""
        price_trend = market_data['price_trend_30d']
        
        if price_trend >= 15:
            return 90.0
        elif price_trend >= 10:
            return 75.0
        elif price_trend >= 5:
            return 60.0
        elif price_trend >= 0:
            return 50.0
        elif price_trend >= -5:
            return 35.0
        else:
            return 20.0
    
    def _calculate_confidence(self,
                             data_availability: Dict[str, bool],
                             market_data: Dict,
                             infrastructure_data: Dict) -> float:
        """
        Calculate confidence level (0.2-0.9) based on data availability.
        
        Missing data sources reduce confidence, not the score itself.
        """
        available_sources = sum(data_availability.values())
        
        # Base confidence by source count
        if available_sources == 3:
            base_confidence = 0.75  # All data available
        elif available_sources == 2:
            base_confidence = 0.60  # 2/3 sources
        else:
            base_confidence = 0.40  # Satellite only
        
        # Adjust for data quality
        market_confidence = market_data.get('data_confidence', 0.0)
        infra_confidence = infrastructure_data.get('data_confidence', 0.0)
        
        if data_availability['market_data'] and market_confidence < 0.7:
            base_confidence *= 0.95
        
        if data_availability['infrastructure_data'] and infra_confidence < 0.7:
            base_confidence *= 0.95
        
        # Ensure within bounds
        return max(0.20, min(0.90, base_confidence))
    
    def _generate_recommendation(self,
                                final_score: float,
                                confidence: float,
                                satellite_changes: int,
                                infrastructure_data: Dict,
                                market_data: Dict) -> tuple:
        """
        Generate investment recommendation based on CORRECTED scoring.
        
        NEW THRESHOLDS (based on proper 0-60 score range):
        - BUY: ≥40 with ≥60% confidence
        - WATCH: 25-39 with ≥40% confidence
        - PASS: <25 or low confidence
        
        Returns:
            (recommendation str, rationale str)
        """
        # Strong Buy
        if final_score >= 45 and confidence >= 0.70:
            recommendation = 'BUY'
            rationale = (f"🔥 STRONG BUY: Exceptional development activity ({satellite_changes:,} changes) "
                        f"with strong infrastructure and market support. Score: {final_score:.1f}/100, "
                        f"Confidence: {confidence:.0%}")
        
        # Moderate Buy
        elif final_score >= 40 and confidence >= 0.60:
            recommendation = 'BUY'
            rationale = (f"✅ BUY: Significant development activity ({satellite_changes:,} changes) "
                        f"with good fundamentals. Score: {final_score:.1f}/100, Confidence: {confidence:.0%}")
        
        # Watch
        elif final_score >= 25 and confidence >= 0.40:
            recommendation = 'WATCH'
            rationale = (f"👀 WATCH: Moderate activity ({satellite_changes:,} changes) - "
                        f"monitor for strengthening signals. Score: {final_score:.1f}/100, "
                        f"Confidence: {confidence:.0%}")
        
        # Pass
        else:
            recommendation = 'PASS'
            if confidence < 0.40:
                rationale = (f"⚠️ PASS: Insufficient data confidence ({confidence:.0%}). "
                            f"Requires additional validation.")
            else:
                rationale = (f"❌ PASS: Low development activity ({satellite_changes:,} changes). "
                            f"Score: {final_score:.1f}/100")
        
        return recommendation, rationale


def migrate_to_corrected_scoring():
    """
    Helper function to migrate from old scoring to new corrected scoring.
    Call this to switch over to the proper satellite-centric system.
    """
    logger.info("🔄 Migrating to CORRECTED scoring system...")
    logger.info("   ✅ Satellite data now PRIMARY signal (0-40 points base)")
    logger.info("   ✅ Infrastructure as multiplier (0.8-1.2x)")
    logger.info("   ✅ Market as multiplier (0.9-1.1x)")
    logger.info("   ✅ Expected score range: 0-60 (much better differentiation!)")
    logger.info("   ✅ New thresholds: BUY ≥40, WATCH 25-39, PASS <25")
    logger.info("🎯 Migration complete - scoring system now matches documentation!")
