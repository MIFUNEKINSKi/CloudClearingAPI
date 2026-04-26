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

    # Part 5: SAR Fusion (v2.10) - Sentinel-1 radar + Sentinel-2 optical fusion
    sar_fusion_source: Optional[str] = None       # 'optical+sar_fusion', 'sar_only', 'optical_only'
    sar_confidence_boost: Optional[float] = None   # 0.0-0.10 confidence increase from dual-sensor

    # Part 6: News Catalyst (v2.10) - Development news scoring multiplier
    news_catalyst_multiplier: Optional[float] = None  # 0.95-1.20
    news_articles_found: Optional[int] = None

    # Part 7: Sensitivity Analysis - how close is the score to flipping recommendation?
    sensitivity_flag: Optional[str] = None  # 'BORDERLINE_BUY', 'BORDERLINE_WATCH', 'BORDERLINE_PASS', None
    sensitivity_detail: Optional[str] = None  # Human-readable explanation
    score_headroom: Optional[float] = None  # Points above/below nearest threshold (negative = below)


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
                                   actual_price_m2: Optional[float] = None,
                                   sar_confidence_boost: float = 0.0,
                                   news_catalyst_multiplier: float = 1.0,
                                   satellite_data_source: str = 'optical',
                                   satellite_data_age_days: int = 0,
                                   cancel_event=None) -> CorrectedScoringResult:
        """
        Calculate investment score using the CORRECT three-part system.

        Args:
            region_name: Name of region
            satellite_changes: Total pixel changes detected (PRIMARY SIGNAL!) — fused optical+SAR if available
            area_affected_m2: Area of changes in square meters
            region_config: Region configuration
            coordinates: Center coordinates
            bbox: Bounding box
            actual_price_m2: Optional actual land price for RVI calculation (v2.6-alpha)
            sar_confidence_boost: Confidence increase from SAR dual-sensor fusion (0.0-0.10)
            news_catalyst_multiplier: News-based scoring multiplier (0.95-1.20, default 1.0)

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
            region_name, bbox, data_availability, cancel_event=cancel_event
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
        confidence = self._calculate_confidence(
            data_availability, market_data, infrastructure_data,
            satellite_data_source=satellite_data_source,
            satellite_data_age_days=satellite_data_age_days,
            market_clamped=str(market_data.get('data_source', '')).endswith('_clamped'),
        )
        # SAR dual-sensor boost increases confidence (max +0.10)
        confidence = min(1.0, confidence + sar_confidence_boost)
        
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
        # Apply news catalyst multiplier (0.95x-1.20x based on development news)
        final_score = final_score * news_catalyst_multiplier
        final_score = max(0, min(100, final_score))  # Clamp to 0-100
        
        logger.info(f"   ✨ Final Score: {final_score:.1f}/100 (confidence: {confidence:.0%})")
        logger.info(f"      Calculation: {base_score:.1f} × {infra_multiplier:.2f} × {market_multiplier:.2f} × {confidence_multiplier:.2f} = {final_score:.1f}")
        
        # Generate recommendation
        recommendation, rationale = self._generate_recommendation(
            final_score, confidence, satellite_changes, infrastructure_data, market_data
        )

        # Sensitivity analysis — flag borderline regions
        sensitivity_flag, sensitivity_detail, score_headroom = self._analyze_sensitivity(
            final_score, confidence, recommendation
        )
        if sensitivity_flag:
            logger.info(f"   ⚠️ SENSITIVITY: {sensitivity_flag} — {sensitivity_detail}")

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
        
        if actual_price_m2 is not None and self.financial_engine:
            try:
                # Prepare satellite data for RVI calculation
                satellite_data_for_rvi = {
                    'vegetation_loss_pixels': satellite_changes // 2,  # Estimate
                    'construction_activity_pct': development_score / 200.0  # Normalize to 0-0.20 range
                }

                # Calculate RVI using financial metrics engine
                rvi_result = self.financial_engine.calculate_relative_value_index(
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
            rvi_breakdown=rvi_breakdown,  # NEW (v2.6-alpha)
            sar_fusion_source='optical+sar' if sar_confidence_boost > 0 else None,  # v2.10
            sar_confidence_boost=sar_confidence_boost if sar_confidence_boost > 0 else None,  # v2.10
            news_catalyst_multiplier=news_catalyst_multiplier if news_catalyst_multiplier != 1.0 else None,  # v2.10
            sensitivity_flag=sensitivity_flag,
            sensitivity_detail=sensitivity_detail,
            score_headroom=score_headroom,
        )
    
    def _calculate_development_score(self, satellite_changes: int) -> float:
        """
        Calculate development score from satellite change count.
        This is the PRIMARY signal — the foundation of the entire score.

        Switched to logarithmic scaling 2026-04-26. The previous step-function
        capped at 40 for any region with >50,000 changes — but actual regions
        in the Apr 25/26 runs had between 8,000 and 8,000,000 changes, so the
        cap saturated almost every meaningful BUY at exactly 40 and removed
        all spread between "moderate" (100K) and "extreme" (5M) development.
        Result: 7 STRONG_BUY regions tied at the same score.

        Logarithmic formula: score = clip(5 + 5 * log10(max(10, changes)), 5, 40)
        - 10        →  5  (noise floor)
        - 100       → 15
        - 1,000     → 20
        - 10,000    → 25
        - 100,000   → 30
        - 1,000,000 → 35
        - 10M+      → 40 (cap, real megaprojects)

        CALIBRATION NOTE: thresholds are still heuristic — not backtested
        against realized land-value changes. Treat scores as relative rankings,
        not absolute return predictions.
        """
        import math
        if satellite_changes < 10:
            return 5.0
        score = 5.0 + 5.0 * math.log10(satellite_changes)
        return max(5.0, min(40.0, score))
    
    def _get_infrastructure_multiplier(self,
                                      region_name: str,
                                      bbox: Dict[str, float],
                                      data_availability: Dict[str, bool],
                                      cancel_event=None) -> tuple:
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
                region_name=region_name,
                cancel_event=cancel_event,
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
                             infrastructure_data: Dict,
                             satellite_data_source: str = 'optical',
                             satellite_data_age_days: int = 0,
                             market_clamped: bool = False) -> float:
        """
        Calculate confidence level (0.2-0.95) based on data availability and quality.

        2026-04-26: Now penalizes single-sensor (SAR-only) and outlier-clamped
        market data instead of leaving them at full confidence. Mean confidence
        on prior runs was 0.98 with no spread; the gate had become a no-op.

        Penalties applied to per-component confidence BEFORE weighted average:
        - SAR-only (no optical verification): satellite_conf 1.0 → 0.75
        - Stale SAR (>14d old): additional drop to 0.60
        - Market clamped (outlier prices): market_conf scaled down by 0.65
        - Infrastructure fallback (not live OSM): -0.10
        """
        # Get data quality metrics
        market_confidence = market_data.get('data_confidence', 0.0)
        infra_confidence = infrastructure_data.get('data_confidence', 0.0)

        # Satellite confidence: penalize SAR-only and stale data
        if satellite_data_source == 'sar_only':
            if satellite_data_age_days > 14:
                satellite_confidence = 0.60  # heavily penalized stale single-sensor
            else:
                satellite_confidence = 0.75  # SAR-only baseline (no optical verification)
        else:
            satellite_confidence = 1.0  # Optical (with or without SAR fusion)

        # Market clamp penalty: outlier prices clamped to median/benchmark
        # signal a data extraction issue that downstream scoring should treat
        # cautiously even if the clamped value seems sensible.
        if market_clamped:
            market_confidence = min(market_confidence, 0.55)

        # Infrastructure live vs fallback: penalize fallback
        infra_source = str(infrastructure_data.get('data_source', ''))
        if infra_source in ('fallback', 'fallback_breaker', 'unavailable', ''):
            infra_confidence = max(0.30, infra_confidence - 0.10)

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
    
    # Recommendation thresholds.
    # Tightened 2026-04-25 after the first full 65-region run on the new
    # cloud-relaxation code showed median score = 46.8 — half the universe was
    # clearing the old BUY≥40 gate. That defeats the point of a screen. New
    # tiers are calibrated against the observed distribution so a "BUY" badge
    # actually means something: STRONG_BUY = top decile (~6 regions),
    # BUY = top third with positive headroom, WATCH = on the radar.
    THRESHOLD_STRONG_BUY = 58.0
    THRESHOLD_BUY = 50.0
    THRESHOLD_WATCH = 35.0
    CONF_GATE_STRONG_BUY = 0.85
    CONF_GATE_BUY = 0.75
    CONF_GATE_WATCH = 0.50

    def _generate_recommendation(self,
                                final_score: float,
                                confidence: float,
                                satellite_changes: int,
                                infrastructure_data: Dict,
                                market_data: Dict) -> tuple:
        """
        Generate investment recommendation based on CORRECTED scoring.

        Tiers (calibrated to the actual score distribution observed on the
        first 65-region run after cloud-relaxation rescue):
        - STRONG_BUY: ≥58, conf ≥0.85  — top decile, due-diligence-ready
        - BUY:        ≥50, conf ≥0.75  — active interest, verify before acting
        - WATCH:      ≥35, conf ≥0.50  — monitor for strengthening signals
        - PASS:       below WATCH or below confidence gate

        Returns:
            (recommendation str, rationale str)
        """
        # Top-conviction tier: real shortlist for capital deployment
        if final_score >= self.THRESHOLD_STRONG_BUY and confidence >= self.CONF_GATE_STRONG_BUY:
            recommendation = 'STRONG_BUY'
            rationale = (
                f"🔥 STRONG BUY: Top-decile signal with high confidence — "
                f"{satellite_changes:,} satellite changes, strong infrastructure + market support. "
                f"Score: {final_score:.1f}/100, Confidence: {confidence:.0%}. "
                "Prioritize for due diligence."
            )

        # BUY: meaningful interest, verify before acting
        elif final_score >= self.THRESHOLD_BUY and confidence >= self.CONF_GATE_BUY:
            recommendation = 'BUY'
            rationale = (
                f"✅ BUY: Solid development signal ({satellite_changes:,} changes) with good "
                f"fundamentals. Score: {final_score:.1f}/100, Confidence: {confidence:.0%}. "
                "Verify pricing and zoning before committing."
            )

        # WATCH: not actionable yet, monitor for upgrade
        elif final_score >= self.THRESHOLD_WATCH and confidence >= self.CONF_GATE_WATCH:
            recommendation = 'WATCH'
            rationale = (
                f"👀 WATCH: Moderate activity ({satellite_changes:,} changes) — monitor for "
                f"strengthening signals. Score: {final_score:.1f}/100, Confidence: {confidence:.0%}."
            )

        # Pass — score or confidence too low
        else:
            recommendation = 'PASS'
            if confidence < self.CONF_GATE_WATCH:
                rationale = (
                    f"⚠️ PASS: Insufficient data confidence ({confidence:.0%}). "
                    "Requires additional validation."
                )
            else:
                rationale = (
                    f"❌ PASS: Low development activity ({satellite_changes:,} changes). "
                    f"Score: {final_score:.1f}/100"
                )

        return recommendation, rationale

    def _analyze_sensitivity(self, final_score: float, confidence: float,
                             recommendation: str) -> tuple:
        """
        Determine if a region is borderline — a small data change could flip
        the recommendation category.

        A region is "borderline" if its score is within ±5 points of the
        nearest category boundary, OR if its confidence is within 10pp of
        the gate.

        Returns:
            (sensitivity_flag, sensitivity_detail, score_headroom)
        """
        SCORE_MARGIN = 5.0   # points
        CONF_MARGIN = 0.10   # 10 percentage-points

        flag = None
        detail_parts = []
        T_SB = self.THRESHOLD_STRONG_BUY
        T_B = self.THRESHOLD_BUY
        T_W = self.THRESHOLD_WATCH

        if recommendation == 'STRONG_BUY':
            score_buffer = final_score - T_SB
            conf_buffer = confidence - self.CONF_GATE_STRONG_BUY
            if score_buffer < SCORE_MARGIN:
                detail_parts.append(f"score only {score_buffer:+.1f}pts above STRONG_BUY threshold ({T_SB})")
            if conf_buffer < CONF_MARGIN:
                detail_parts.append(f"confidence only {conf_buffer:+.0%} above STRONG_BUY gate ({self.CONF_GATE_STRONG_BUY:.0%})")
            if detail_parts:
                flag = 'BORDERLINE_STRONG_BUY'
            headroom = score_buffer

        elif recommendation == 'BUY':
            score_buffer = final_score - T_B
            up_to_strong = T_SB - final_score
            conf_buffer = confidence - self.CONF_GATE_BUY
            if score_buffer < SCORE_MARGIN:
                detail_parts.append(f"score only {score_buffer:+.1f}pts above BUY threshold ({T_B})")
            if up_to_strong < SCORE_MARGIN:
                detail_parts.append(f"only {up_to_strong:.1f}pts below STRONG_BUY threshold ({T_SB})")
            if conf_buffer < CONF_MARGIN:
                detail_parts.append(f"confidence only {conf_buffer:+.0%} above BUY gate ({self.CONF_GATE_BUY:.0%})")
            if detail_parts:
                flag = 'BORDERLINE_BUY'
            headroom = score_buffer

        elif recommendation == 'WATCH':
            to_buy = T_B - final_score
            to_pass = final_score - T_W
            conf_to_buy = self.CONF_GATE_BUY - confidence
            conf_to_pass = confidence - self.CONF_GATE_WATCH

            if to_buy < SCORE_MARGIN:
                detail_parts.append(f"only {to_buy:.1f}pts below BUY threshold ({T_B})")
            if to_pass < SCORE_MARGIN:
                detail_parts.append(f"only {to_pass:.1f}pts above PASS threshold ({T_W})")
            if conf_to_buy < CONF_MARGIN:
                detail_parts.append(f"confidence {conf_to_buy:.0%} short of BUY gate ({self.CONF_GATE_BUY:.0%})")
            if conf_to_pass < CONF_MARGIN:
                detail_parts.append(f"confidence only {conf_to_pass:.0%} above PASS gate ({self.CONF_GATE_WATCH:.0%})")
            if detail_parts:
                flag = 'BORDERLINE_WATCH'
            headroom = min(to_pass, to_buy)

        else:  # PASS
            score_gap = T_W - final_score
            conf_gap = self.CONF_GATE_WATCH - confidence
            if score_gap < SCORE_MARGIN and score_gap > 0:
                detail_parts.append(f"only {score_gap:.1f}pts below WATCH threshold ({T_W})")
            if conf_gap < CONF_MARGIN and conf_gap > 0:
                detail_parts.append(f"confidence only {conf_gap:.0%} below WATCH gate ({self.CONF_GATE_WATCH:.0%})")
            if detail_parts:
                flag = 'BORDERLINE_PASS'
            headroom = -score_gap

        detail = '; '.join(detail_parts) if detail_parts else None
        return flag, detail, headroom


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
