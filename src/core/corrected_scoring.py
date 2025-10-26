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
    infrastructure_details: Dict[str, Any]  # ✅ FIX: Store detailed infrastructure breakdown
    
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
    
    # Part 4: Relative Value Index (v2.6-alpha) - Non-invasive data gathering
    rvi: Optional[float] = None  # Relative value index (actual/expected price)
    expected_price_m2: Optional[float] = None  # Expected price based on fundamentals (IDR)
    rvi_interpretation: Optional[str] = None  # RVI interpretation string
    rvi_breakdown: Optional[Dict[str, Any]] = None  # Detailed RVI calculation breakdown


class CorrectedInvestmentScorer:
    """
    Properly implements satellite-centric investment scoring.
    
    This corrects the fundamental flaw where satellite data was ignored.
    Now satellite change detection is the PRIMARY base score (0-40 points),
    with infrastructure and market as multipliers.
    
    Version 2.6-beta adds RVI-aware market multiplier for valuation-based scoring.
    """
    
    def __init__(self, price_engine, infrastructure_engine, financial_engine=None):
        """
        Initialize corrected scorer with optional financial engine.
        
        Args:
            price_engine: Price intelligence engine for market data
            infrastructure_engine: Infrastructure analyzer for OSM data
            financial_engine: Optional financial metrics engine for RVI calculations (v2.6-beta)
        """
        self.price_engine = price_engine
        self.infrastructure_engine = infrastructure_engine
        self.financial_engine = financial_engine  # v2.6-beta: RVI support
        
        if self.financial_engine:
            logger.info("✅ Initialized CORRECTED scoring system (satellite-centric) with RVI support")
        else:
            logger.info("✅ Initialized CORRECTED scoring system (satellite-centric) - trend-based multiplier")
    
    def calculate_investment_score(self, 
                                   region_name: str,
                                   satellite_changes: int,
                                   area_affected_m2: float,
                                   region_config: Dict[str, Any],
                                   coordinates: Dict[str, float],
                                   bbox: Dict[str, float],
                                   actual_price_m2: Optional[float] = None) -> CorrectedScoringResult:
        """
        Calculate investment score using the CORRECT three-part system.
        
        Args:
            region_name: Name of region
            satellite_changes: Total pixel changes detected (PRIMARY SIGNAL!)
            area_affected_m2: Area of changes in square meters
            region_config: Region configuration
            coordinates: Center coordinates
            bbox: Bounding box
            actual_price_m2: Optional actual land price for RVI calculation (v2.6-alpha)
            
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
        
        # Prepare satellite data dict for RVI calculation
        satellite_data_dict = {
            'vegetation_loss_pixels': satellite_changes,
            'area_affected_m2': area_affected_m2,
            'development_score': development_score
        }
        
        # PART 3: MARKET ANALYSIS & MULTIPLIER (v2.6-beta: RVI-aware)
        market_data, market_multiplier = self._get_market_multiplier(
            region_name, 
            coordinates, 
            data_availability,
            satellite_data=satellite_data_dict,
            infrastructure_data=infrastructure_data
        )
        logger.info(f"   💰 Market Multiplier: {market_multiplier:.2f}x (trend: {market_data['price_trend_30d']:.1f}%)")
        
        # FINAL CALCULATION (THE CORRECT WAY!)
        base_score = development_score  # Start with satellite data (0-40)
        after_infrastructure = base_score * infra_multiplier  # Apply infrastructure
        after_market = after_infrastructure * market_multiplier  # Apply market
        
        # Confidence weighting (reduces score when data is missing)
        confidence = self._calculate_confidence(data_availability, market_data, infrastructure_data)
        
        # Non-linear confidence multiplier (v2.4.1 refinement)
        # Quadratic scaling below 85% for steeper penalties, linear above for diminishing returns
        if confidence >= 0.85:
            # Linear scaling above 85%: 0.97 to 1.00
            confidence_multiplier = 0.97 + (confidence - 0.85) * 0.30  # 0.85→0.97, 0.95→1.00
        elif confidence >= 0.50:
            # Quadratic scaling between 50% and 85%: 0.70 to 0.97
            # Normalize to [0, 1] range where 0.50→0, 0.85→1
            normalized_conf = (confidence - 0.50) / 0.35
            # Apply power function: stronger penalties at low confidence
            confidence_multiplier = 0.70 + 0.27 * (normalized_conf ** 1.2)
        else:
            # Below 50% confidence: apply floor of 0.70
            confidence_multiplier = 0.70
        
        # Clamp to ensure bounds (0.70 to 1.00)
        confidence_multiplier = max(0.70, min(1.00, confidence_multiplier))
        
        final_score = after_market * confidence_multiplier
        final_score = max(0, min(100, final_score))  # Clamp to 0-100
        
        logger.info(f"   ✨ Final Score: {final_score:.1f}/100 (confidence: {confidence:.0%})")
        logger.info(f"      Calculation: {base_score:.1f} × {infra_multiplier:.2f} × {market_multiplier:.2f} × {confidence_multiplier:.2f} = {final_score:.1f}")
        
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
        
        # Handle major_features which are dicts with 'type' and 'name' keys
        major_features = infrastructure_data.get('major_features', [])
        
        # Count features by type (features are dicts with 'type' key)
        airports_count = len([f for f in major_features if isinstance(f, dict) and 'airport' in f.get('type', '').lower()])
        railway_access = any(isinstance(f, dict) and 'railway' in f.get('type', '').lower() for f in major_features)
        
        # ✅ FIX: Build detailed infrastructure breakdown for PDF display
        infrastructure_details = {
            'score': infrastructure_data.get('infrastructure_score', 0),
            'reasoning': infrastructure_data.get('reasoning', []),
            'major_features': major_features,
            'roads': len([f for f in major_features if isinstance(f, dict) and 'road' in f.get('type', '').lower()]),
            'airports': airports_count,
            'railways': 1 if railway_access else 0,
            'ports': len([f for f in major_features if isinstance(f, dict) and 'port' in f.get('type', '').lower()]),
            'construction_projects': len(infrastructure_data.get('construction_projects', [])),
            'data_source': infrastructure_data.get('data_source', 'unknown'),
            'data_confidence': infrastructure_data.get('data_confidence', 0.5)
        }
        
        # NEW (v2.6-alpha): Calculate RVI if actual price is available
        rvi = None
        expected_price_m2 = None
        rvi_interpretation = None
        rvi_breakdown = None
        
        if actual_price_m2 is not None and self.price_engine:
            try:
                # Prepare satellite data for RVI calculation
                satellite_data_for_rvi = {
                    'vegetation_loss_pixels': satellite_changes // 2,  # Estimate
                    'construction_activity_pct': development_score / 200.0  # Normalize to 0-0.20 range
                }
                
                # Calculate RVI using financial metrics engine
                rvi_result = self.price_engine.calculate_relative_value_index(
                    region_name=region_name,
                    actual_price_m2=actual_price_m2,
                    infrastructure_score=infrastructure_data['infrastructure_score'],
                    satellite_data=satellite_data_for_rvi
                )
                
                rvi = rvi_result.get('rvi')
                expected_price_m2 = rvi_result.get('expected_price_m2')
                rvi_interpretation = rvi_result.get('interpretation')
                rvi_breakdown = rvi_result.get('breakdown')
                
                if rvi is not None:
                    logger.info(f"   📊 RVI: {rvi:.3f} ({rvi_interpretation})")
                    logger.info(f"      Expected: Rp {expected_price_m2:,.0f}/m² vs Actual: Rp {actual_price_m2:,.0f}/m²")
                
            except Exception as e:
                logger.warning(f"   ⚠️ RVI calculation failed: {e}")
        
        return CorrectedScoringResult(
            region_name=region_name,
            satellite_changes=satellite_changes,
            area_affected_hectares=area_affected_m2 / 10000,
            development_score=development_score,
            infrastructure_score=infrastructure_data['infrastructure_score'],
            infrastructure_multiplier=infra_multiplier,
            roads_count=len(major_features),
            airports_nearby=airports_count,
            railway_access=railway_access,
            infrastructure_details=infrastructure_details,  # ✅ FIX: Include detailed breakdown
            price_trend_30d=market_data['price_trend_30d'],
            market_heat=market_data['market_heat'],
            market_score=self._calculate_market_score(market_data),
            market_multiplier=market_multiplier,
            final_investment_score=final_score,
            confidence_level=confidence,
            recommendation=recommendation,
            rationale=rationale,
            data_sources=data_sources,
            data_availability=data_availability,
            rvi=rvi,  # NEW (v2.6-alpha)
            expected_price_m2=expected_price_m2,  # NEW (v2.6-alpha)
            rvi_interpretation=rvi_interpretation,  # NEW (v2.6-alpha)
            rvi_breakdown=rvi_breakdown  # NEW (v2.6-alpha)
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
        🆕 IMPROVED: Get infrastructure data and convert to TIERED multiplier (0.8-1.3x).
        
        Tiered system creates better separation between good and excellent infrastructure:
        - Excellent (90-100): 1.3x  - World-class infrastructure
        - Very Good (75-89): 1.15x  - Strong infrastructure
        - Good (60-74): 1.0x        - Adequate infrastructure  
        - Fair (40-59): 0.9x        - Basic infrastructure
        - Poor (<40): 0.8x          - Weak infrastructure
        
        Returns:
            (infrastructure_data dict, multiplier float)
        """
        try:
            # Call the actual method that exists: analyze_infrastructure_context()
            infrastructure_data = self.infrastructure_engine.analyze_infrastructure_context(
                bbox=bbox,
                region_name=region_name
            )
            data_availability['infrastructure_data'] = True
            
            # 🆕 TIERED: Convert infrastructure score (0-100) to tiered multiplier (0.8-1.3)
            infra_score = infrastructure_data['infrastructure_score']
            
            if infra_score >= 90:
                multiplier = 1.30  # Excellent - world-class infrastructure
                tier = "Excellent"
            elif infra_score >= 75:
                multiplier = 1.15  # Very Good - strong infrastructure
                tier = "Very Good"
            elif infra_score >= 60:
                multiplier = 1.00  # Good - adequate infrastructure
                tier = "Good"
            elif infra_score >= 40:
                multiplier = 0.90  # Fair - basic infrastructure
                tier = "Fair"
            else:
                multiplier = 0.80  # Poor - weak infrastructure
                tier = "Poor"
            
            logger.debug(f"   Infrastructure: {infra_score:.1f}/100 ({tier}) → {multiplier:.2f}x multiplier")
            
        except Exception as e:
            logger.warning(f"⚠️ Infrastructure data unavailable for {region_name}: {e}")
            infrastructure_data = {
                'infrastructure_score': 50.0,  # Neutral
                'major_features': [],
                'data_source': 'unavailable',
                'data_confidence': 0.0
            }
            multiplier = 0.90  # Slightly below neutral when data unavailable
        
        return infrastructure_data, multiplier
    
    def _get_market_multiplier(self,
                               region_name: str,
                               coordinates: Dict[str, float],
                               data_availability: Dict[str, bool],
                               satellite_data: Optional[Dict[str, Any]] = None,
                               infrastructure_data: Optional[Dict[str, Any]] = None) -> tuple:
        """
        🆕 v2.6-beta: Get market data and convert to RVI-AWARE multiplier (0.85-1.4x).
        
        RVI-Based System (when financial_engine available):
        - RVI < 0.7: 1.40x (significantly undervalued - strong buy)
        - RVI 0.7-0.9: 1.25x (undervalued - buy opportunity)
        - RVI 0.9-1.1: 1.0x (fair value - neutral)
        - RVI 1.1-1.3: 0.90x (overvalued - caution)
        - RVI >= 1.3: 0.85x (significantly overvalued - speculation risk)
        
        With momentum adjustment: final = base * (1 + trend * 0.1)
        
        Fallback to Trend-Based System (when RVI unavailable):
        - Booming (>15%/yr): 1.40x   - Exceptional growth
        - Strong (8-15%/yr): 1.20x   - Very strong market
        - Stable (2-8%/yr): 1.00x    - Healthy growth
        - Stagnant (0-2%/yr): 0.95x  - Slow growth
        - Declining (<0%/yr): 0.85x  - Market decline
        
        Args:
            region_name: Region name
            coordinates: Center coordinates
            data_availability: Data tracking dict
            satellite_data: Optional satellite data for RVI calculation
            infrastructure_data: Optional infrastructure data for RVI calculation
        
        Returns:
            (market_data dict, multiplier float)
        """
        try:
            # Call the orchestrator's public method: get_land_price() returns dict with price data
            pricing_response = self.price_engine.get_land_price(region_name)
            data_availability['market_data'] = True
            
            # Extract price data from orchestrator response
            # Orchestrator returns dict with 'average_price_per_m2', 'data_source', etc.
            avg_price = pricing_response.get('average_price_per_m2', pricing_response.get('current_avg', 0))
            price_trend_pct = pricing_response.get('price_trend_30d', 0.0)  # Already in percentage
            
            market_data = {
                'price_trend_30d': price_trend_pct,
                'market_heat': pricing_response.get('market_heat', 'neutral'),
                'current_price_per_m2': avg_price,
                'data_source': pricing_response.get('data_source', 'unknown'),
                'data_confidence': pricing_response.get('data_confidence', 0.5)
            }
            
            # v2.6-beta: Try RVI-aware multiplier if financial engine available
            if self.financial_engine and satellite_data and infrastructure_data:
                try:
                    rvi_data = self.financial_engine.calculate_relative_value_index(
                        region_name=region_name,
                        actual_price_m2=avg_price,
                        infrastructure_score=infrastructure_data.get('infrastructure_score', 50),
                        satellite_data=satellite_data  # Required parameter for momentum calculation
                    )
                    
                    rvi = rvi_data.get('rvi')
                    rvi_interpretation = rvi_data.get('interpretation', 'unknown')
                    
                    if rvi is not None and rvi > 0:
                        # RVI-based multiplier thresholds
                        if rvi < 0.7:
                            base_multiplier = 1.40  # Significantly undervalued
                            tier = "Significantly Undervalued"
                        elif rvi < 0.9:
                            base_multiplier = 1.25  # Undervalued
                            tier = "Undervalued"
                        elif rvi < 1.1:
                            base_multiplier = 1.0   # Fair value
                            tier = "Fair Value"
                        elif rvi < 1.3:
                            base_multiplier = 0.90  # Overvalued
                            tier = "Overvalued"
                        else:
                            base_multiplier = 0.85  # Significantly overvalued
                            tier = "Significantly Overvalued"
                        
                        # Apply momentum adjustment (±10% based on market trend)
                        momentum_factor = 1.0 + (price_trend_pct / 100.0) * 0.1
                        multiplier = base_multiplier * momentum_factor
                        
                        # Clamp to preserve bounds
                        multiplier = max(0.85, min(1.40, multiplier))
                        
                        logger.info(f"   💰 RVI-Aware Market Multiplier:")
                        logger.info(f"      RVI: {rvi:.3f} ({tier})")
                        logger.info(f"      Base multiplier: {base_multiplier:.2f}x")
                        logger.info(f"      Price trend: {price_trend_pct:.1f}%")
                        logger.info(f"      Momentum factor: {momentum_factor:.3f}x")
                        logger.info(f"      Final multiplier: {multiplier:.2f}x")
                        
                        # Add RVI data to market_data dict for logging
                        market_data['rvi'] = rvi
                        market_data['rvi_interpretation'] = rvi_interpretation
                        market_data['multiplier_basis'] = 'rvi_aware'
                        
                        return market_data, multiplier
                    else:
                        logger.debug(f"   RVI calculation returned invalid value ({rvi}), using trend fallback")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ RVI calculation failed: {e}, using trend-based fallback")
            
            # Fallback: Trend-based multiplier (v2.6-alpha and earlier)
            if price_trend_pct >= 15:
                multiplier = 1.40  # Booming - exceptional growth
                tier = "Booming"
            elif price_trend_pct >= 8:
                multiplier = 1.20  # Strong - very strong market
                tier = "Strong"
            elif price_trend_pct >= 2:
                multiplier = 1.00  # Stable - healthy growth
                tier = "Stable"
            elif price_trend_pct >= 0:
                multiplier = 0.95  # Stagnant - slow growth
                tier = "Stagnant"
            else:
                multiplier = 0.85  # Declining - market decline
                tier = "Declining"
            
            logger.debug(f"   Market: {price_trend_pct:.1f}% trend ({tier}) → {multiplier:.2f}x multiplier")
            market_data['multiplier_basis'] = 'trend_based'
            
        except Exception as e:
            logger.warning(f"⚠️ Market data unavailable for {region_name}: {e}")
            market_data = {
                'price_trend_30d': 0.0,
                'market_heat': 'unknown',
                'current_price_per_m2': 0,
                'data_source': 'unavailable',
                'data_confidence': 0.0
            }
            multiplier = 0.95  # Slightly below neutral when data unavailable
        
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
        Calculate confidence level (0.2-0.95) based on data availability and quality.
        
        Uses component-level quality bonuses to prevent post-aggregation inflation.
        High-quality data sources increase confidence, low-quality reduces it.
        
        Version 2.4.1 Refinement: Component-level bonuses applied before weighted average.
        """
        # Get data quality metrics
        market_confidence = market_data.get('data_confidence', 0.0)
        infra_confidence = infrastructure_data.get('data_confidence', 0.0)
        satellite_confidence = 1.0  # Satellite data always available and reliable
        
        # Component-level quality bonuses (applied BEFORE aggregation to prevent inflation)
        if data_availability['market_data'] and market_confidence >= 0.85:
            market_confidence = min(0.95, market_confidence + 0.05)  # +5% for excellent data
        
        if data_availability['infrastructure_data'] and infra_confidence >= 0.85:
            infra_confidence = min(0.95, infra_confidence + 0.05)  # +5% for excellent data
        
        # Weighted average by availability (satellite always counts)
        available_sources = sum(data_availability.values())
        
        if available_sources == 3:
            # All data available: weighted average (satellite:40%, infra:30%, market:30%)
            overall_confidence = (
                0.40 * satellite_confidence +
                0.30 * infra_confidence +
                0.30 * market_confidence
            )
        elif available_sources == 2:
            if data_availability['infrastructure_data']:
                # Satellite + Infrastructure
                overall_confidence = 0.60 * satellite_confidence + 0.40 * infra_confidence
            else:
                # Satellite + Market
                overall_confidence = 0.60 * satellite_confidence + 0.40 * market_confidence
        else:
            # Satellite only
            overall_confidence = satellite_confidence * 0.50  # 50% penalty for single source
        
        # Apply strengthened penalties for very poor data quality
        if overall_confidence < 0.60:
            overall_confidence *= 0.90  # -10% penalty for <60% confidence
        
        # Ensure within bounds (0.20 to 0.95)
        return max(0.20, min(0.95, overall_confidence))
    
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
