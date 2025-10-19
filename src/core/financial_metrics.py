"""
Financial Metrics Engine for Investment Analysis
CloudClearingAPI - October 19, 2025

Translates satellite data and infrastructure analysis into concrete financial projections:
- Land value estimation from real estate data
- Projected ROI calculations
- Development cost indexing
- Investment return timeline estimates
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
import math

logger = logging.getLogger(__name__)

# Import scraper orchestrator
try:
    from src.scrapers.scraper_orchestrator import LandPriceOrchestrator
    SCRAPERS_AVAILABLE = True
except ImportError:
    logger.warning("Scrapers module not available, will use static benchmarks only")
    SCRAPERS_AVAILABLE = False


@dataclass
class FinancialProjection:
    """Complete financial analysis for a region"""
    region_name: str
    
    # Land Value Estimates
    current_land_value_per_m2: float  # IDR
    estimated_future_value_per_m2: float  # IDR (3-year projection)
    appreciation_rate_annual: float  # Decimal (0.15 = 15%)
    
    # Development Costs
    development_cost_index: float  # 0-100 (higher = more expensive to develop)
    estimated_dev_cost_per_m2: float  # IDR
    terrain_difficulty: str  # Easy/Moderate/Difficult
    
    # ROI Projections
    projected_roi_3yr: float  # Decimal (0.45 = 45% return)
    projected_roi_5yr: float  # Decimal
    break_even_years: float  # Years to break even
    
    # Investment Sizing
    recommended_plot_size_m2: float  # Recommended acquisition size
    total_acquisition_cost: float  # IDR
    total_development_cost: float  # IDR
    projected_exit_value: float  # IDR (3-year)
    
    # Risk Factors
    liquidity_risk: str  # Low/Medium/High
    speculation_risk: str  # Low/Medium/High
    infrastructure_risk: str  # Low/Medium/High
    
    # Confidence
    projection_confidence: float  # 0-1
    data_sources: List[str]


class FinancialMetricsEngine:
    """
    Calculates financial projections and ROI estimates for land investment opportunities
    """
    
    def __init__(self, enable_web_scraping: bool = True, cache_expiry_hours: int = 24):
        """
        Initialize with regional benchmarks and cost factors
        
        Args:
            enable_web_scraping: If True, attempt live scraping of land prices
            cache_expiry_hours: Hours before cached scrape data expires
        """
        # Initialize scraper orchestrator if available
        self.price_orchestrator = None
        if SCRAPERS_AVAILABLE and enable_web_scraping:
            try:
                self.price_orchestrator = LandPriceOrchestrator(
                    cache_expiry_hours=cache_expiry_hours,
                    enable_live_scraping=True
                )
                logger.info("Web scraping enabled for land price data")
            except Exception as e:
                logger.warning(f"Failed to initialize price orchestrator: {str(e)}")
        else:
            logger.info("Web scraping disabled, using static benchmarks only")
        
        # Regional land value benchmarks (IDR per m²)
        self.regional_benchmarks = {
            'jakarta': {
                'current_avg': 8_500_000,
                'historical_appreciation': 0.15,  # 15% annual
                'market_liquidity': 'high'
            },
            'bali': {
                'current_avg': 12_000_000,
                'historical_appreciation': 0.20,  # 20% annual
                'market_liquidity': 'high'
            },
            'yogyakarta': {
                'current_avg': 4_500_000,
                'historical_appreciation': 0.12,  # 12% annual
                'market_liquidity': 'moderate'
            },
            'surabaya': {
                'current_avg': 6_500_000,
                'historical_appreciation': 0.14,  # 14% annual
                'market_liquidity': 'high'
            },
            'bandung': {
                'current_avg': 5_000_000,
                'historical_appreciation': 0.13,  # 13% annual
                'market_liquidity': 'moderate'
            },
            'semarang': {
                'current_avg': 3_500_000,
                'historical_appreciation': 0.11,  # 11% annual
                'market_liquidity': 'moderate'
            }
        }
        
        # Development cost factors (IDR per m²)
        self.base_development_costs = {
            'land_clearing': 50_000,  # Vegetation removal
            'grading_flat': 75_000,  # Flat terrain
            'grading_slope': 150_000,  # Sloped terrain
            'grading_steep': 300_000,  # Steep terrain
            'road_access': 200_000,  # If no road access
            'utilities': 150_000,  # Water, electric connection
            'permits': 100_000  # Licensing and permits
        }
        
        # Recommended investment sizes by development stage
        self.recommended_plot_sizes = {
            'early_stage': 5000,  # m² - land acquisition play
            'mid_stage': 2000,  # m² - development ready
            'late_stage': 1000  # m² - immediate development
        }
    
    def calculate_financial_projection(self,
                                      region_name: str,
                                      satellite_data: Dict[str, Any],
                                      infrastructure_data: Dict[str, Any],
                                      market_data: Dict[str, Any],
                                      scoring_result: Any) -> FinancialProjection:
        """
        Calculate comprehensive financial projection for a region
        
        Args:
            region_name: Name of the region
            satellite_data: Satellite analysis results
            infrastructure_data: Infrastructure analysis results  
            market_data: Market intelligence data
            scoring_result: Investment scoring result
            
        Returns:
            FinancialProjection with ROI estimates and costs
        """
        logger.info(f"Calculating financial projection for {region_name}")
        
        # Step 1: Estimate current land value
        current_value = self._estimate_current_land_value(
            region_name, market_data, infrastructure_data
        )
        
        # Step 2: Calculate development cost index
        dev_cost_index = self._calculate_development_cost_index(
            satellite_data, infrastructure_data
        )
        
        # Step 3: Estimate development costs
        dev_costs = self._estimate_development_costs(
            dev_cost_index, satellite_data
        )
        
        # Step 4: Project future value
        appreciation_rate = self._estimate_appreciation_rate(
            region_name, market_data, scoring_result
        )
        
        future_value_3yr = current_value * math.pow(1 + appreciation_rate, 3)
        future_value_5yr = current_value * math.pow(1 + appreciation_rate, 5)
        
        # Step 5: Calculate ROI
        roi_3yr = self._calculate_roi(
            current_value, dev_costs['total_per_m2'], future_value_3yr
        )
        roi_5yr = self._calculate_roi(
            current_value, dev_costs['total_per_m2'], future_value_5yr
        )
        
        # Step 6: Determine recommended investment size
        plot_size = self._recommend_plot_size(satellite_data, scoring_result)
        
        # Step 7: Calculate total costs and returns
        total_acquisition = current_value * plot_size
        total_development = dev_costs['total_per_m2'] * plot_size
        exit_value_3yr = future_value_3yr * plot_size
        
        # Step 8: Calculate break-even timeline
        break_even_years = self._calculate_break_even(
            current_value, dev_costs['total_per_m2'], appreciation_rate
        )
        
        # Step 9: Assess risks
        liquidity_risk = self._assess_liquidity_risk(region_name, market_data)
        speculation_risk = self._assess_speculation_risk(market_data, appreciation_rate)
        infrastructure_risk = self._assess_infrastructure_risk(infrastructure_data)
        
        # Step 10: Calculate projection confidence
        confidence = self._calculate_projection_confidence(
            market_data, infrastructure_data, satellite_data
        )
        
        return FinancialProjection(
            region_name=region_name,
            current_land_value_per_m2=current_value,
            estimated_future_value_per_m2=future_value_3yr,
            appreciation_rate_annual=appreciation_rate,
            development_cost_index=dev_cost_index,
            estimated_dev_cost_per_m2=dev_costs['total_per_m2'],
            terrain_difficulty=dev_costs['terrain_difficulty'],
            projected_roi_3yr=roi_3yr,
            projected_roi_5yr=roi_5yr,
            break_even_years=break_even_years,
            recommended_plot_size_m2=plot_size,
            total_acquisition_cost=total_acquisition,
            total_development_cost=total_development,
            projected_exit_value=exit_value_3yr,
            liquidity_risk=liquidity_risk,
            speculation_risk=speculation_risk,
            infrastructure_risk=infrastructure_risk,
            projection_confidence=confidence,
            data_sources=self._get_data_sources(market_data, infrastructure_data)
        )
    
    def _estimate_current_land_value(self,
                                     region_name: str,
                                     market_data: Dict[str, Any],
                                     infrastructure_data: Dict[str, Any]) -> float:
        """
        Estimate current land value per m² with cascading data sources:
        1. Live web scraping (Lamudi, Rumah.com)
        2. Cached scrape data (if < 24-48h old)
        3. Static regional benchmarks (fallback)
        """
        base_value = None
        data_source = "unknown"
        
        # Priority 1: Try live scraping / cache via orchestrator
        if self.price_orchestrator:
            try:
                price_data = self.price_orchestrator.get_land_price(region_name, max_listings=20)
                
                if price_data['success'] and price_data['average_price_per_m2'] > 0:
                    base_value = price_data['average_price_per_m2']
                    data_source = price_data['data_source']
                    
                    logger.info(f"Using {data_source} land price: Rp {base_value:,.0f}/m² "
                               f"(listings: {price_data['listing_count']})")
            except Exception as e:
                logger.warning(f"Orchestrator failed for {region_name}: {str(e)}")
        
        # Priority 2: Fallback to static benchmark if scraping failed
        if base_value is None:
            benchmark = self._find_nearest_benchmark(region_name)
            base_value = benchmark['current_avg']
            data_source = "static_benchmark"
            logger.info(f"Using static benchmark for {region_name}: Rp {base_value:,.0f}/m²")
        
        # Adjust for infrastructure quality
        infra_score = infrastructure_data.get('infrastructure_score', 50)
        
        # Infrastructure adjustment: ±40% based on connectivity
        if infra_score >= 80:
            infra_multiplier = 1.40  # Excellent connectivity adds 40%
        elif infra_score >= 60:
            infra_multiplier = 1.15  # Good connectivity adds 15%
        elif infra_score >= 40:
            infra_multiplier = 1.00  # Neutral
        else:
            infra_multiplier = 0.75  # Poor connectivity reduces 25%
        
        # Market heat adjustment
        market_heat = market_data.get('market_heat', 'unknown')
        heat_multipliers = {
            'hot': 1.20,
            'warming': 1.10,
            'stable': 1.00,
            'cooling': 0.90,
            'cold': 0.80,
            'unknown': 0.95
        }
        heat_multiplier = heat_multipliers.get(market_heat, 0.95)
        
        estimated_value = base_value * infra_multiplier * heat_multiplier
        
        logger.debug(f"Land value estimate: {estimated_value:,.0f} IDR/m² "
                    f"(base: {base_value:,.0f}, infra: {infra_multiplier:.2f}x, "
                    f"market: {heat_multiplier:.2f}x)")
        
        return estimated_value
    
    def _calculate_development_cost_index(self,
                                          satellite_data: Dict[str, Any],
                                          infrastructure_data: Dict[str, Any]) -> float:
        """
        Calculate development cost index (0-100) based on:
        - Terrain difficulty (from satellite data)
        - Distance to roads
        - Land clearing requirements
        
        Formula: Dev Cost Index = (Terrain × 0.5) + (Road Distance × 0.3) + (Clearing × 0.2)
        """
        # Component 1: Terrain difficulty (from slope if available, else estimate from NDVI variance)
        terrain_score = 50  # Default moderate
        
        # If we have vegetation loss data, dense vegetation = harder clearing
        vegetation_changes = satellite_data.get('vegetation_loss_pixels', 0)
        total_pixels = satellite_data.get('total_pixels', 1)
        vegetation_pct = (vegetation_changes / total_pixels) * 100 if total_pixels > 0 else 0
        
        if vegetation_pct > 50:
            terrain_score = 75  # Heavy vegetation
        elif vegetation_pct > 25:
            terrain_score = 60  # Moderate vegetation
        else:
            terrain_score = 40  # Light vegetation/cleared
        
        # Component 2: Road distance (from infrastructure data)
        road_distance_score = 50  # Default
        
        major_roads = infrastructure_data.get('major_features', [])
        road_count = len([f for f in major_roads if 'highway' in str(f).lower() or 'road' in str(f).lower()])
        
        if road_count >= 3:
            road_distance_score = 20  # Excellent road access = low development cost
        elif road_count >= 1:
            road_distance_score = 40  # Good access
        else:
            road_distance_score = 80  # Poor access = high cost to build roads
        
        # Component 3: Land clearing percentage (from satellite data)
        clearing_score = vegetation_pct * 0.8  # Scale 0-80
        
        # Calculate weighted index
        dev_cost_index = (
            terrain_score * 0.5 +
            road_distance_score * 0.3 +
            clearing_score * 0.2
        )
        
        logger.debug(f"Development cost index: {dev_cost_index:.1f}/100 "
                    f"(terrain: {terrain_score}, roads: {road_distance_score}, clearing: {clearing_score:.1f})")
        
        return dev_cost_index
    
    def _estimate_development_costs(self,
                                    dev_cost_index: float,
                                    satellite_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate per-m² development costs based on development cost index
        """
        # Base cost starts at clearing cost
        base_cost = self.base_development_costs['land_clearing']
        
        # Add terrain grading cost based on index
        if dev_cost_index >= 70:
            terrain_cost = self.base_development_costs['grading_steep']
            terrain_difficulty = "Difficult"
        elif dev_cost_index >= 50:
            terrain_cost = self.base_development_costs['grading_slope']
            terrain_difficulty = "Moderate"
        else:
            terrain_cost = self.base_development_costs['grading_flat']
            terrain_difficulty = "Easy"
        
        # Road access cost if needed
        road_cost = 0
        if dev_cost_index >= 60:  # Poor road access
            road_cost = self.base_development_costs['road_access']
        
        # Utilities and permits
        utilities_cost = self.base_development_costs['utilities']
        permits_cost = self.base_development_costs['permits']
        
        # Total cost per m²
        total_cost = base_cost + terrain_cost + road_cost + utilities_cost + permits_cost
        
        return {
            'total_per_m2': total_cost,
            'breakdown': {
                'land_clearing': base_cost,
                'grading': terrain_cost,
                'road_access': road_cost,
                'utilities': utilities_cost,
                'permits': permits_cost
            },
            'terrain_difficulty': terrain_difficulty
        }
    
    def _estimate_appreciation_rate(self,
                                    region_name: str,
                                    market_data: Dict[str, Any],
                                    scoring_result: Any) -> float:
        """
        Estimate annual appreciation rate based on:
        - Regional historical appreciation
        - Current market trend
        - Investment score (development momentum)
        """
        # Get regional baseline
        benchmark = self._find_nearest_benchmark(region_name)
        base_appreciation = benchmark['historical_appreciation']
        
        # Adjust for current market trend
        price_trend = market_data.get('price_trend_30d', 0) / 100  # Convert to decimal
        
        # Weight: 60% historical, 40% current trend
        blended_appreciation = (base_appreciation * 0.6) + (price_trend * 0.4)
        
        # Boost for high development momentum (high satellite activity = appreciation catalyst)
        investment_score = getattr(scoring_result, 'final_investment_score', 50)
        
        if investment_score >= 70:
            momentum_boost = 0.03  # +3% for strong momentum
        elif investment_score >= 60:
            momentum_boost = 0.02  # +2%
        else:
            momentum_boost = 0
        
        final_appreciation = blended_appreciation + momentum_boost
        
        # Cap at reasonable limits (5-30% annual)
        final_appreciation = max(0.05, min(0.30, final_appreciation))
        
        logger.debug(f"Appreciation rate: {final_appreciation:.1%} "
                    f"(base: {base_appreciation:.1%}, trend: {price_trend:.1%}, boost: {momentum_boost:.1%})")
        
        return final_appreciation
    
    def _calculate_roi(self,
                      current_value: float,
                      dev_cost: float,
                      future_value: float) -> float:
        """
        Calculate ROI: (Future Value - (Current Value + Dev Costs)) / (Current Value + Dev Costs)
        """
        total_investment = current_value + dev_cost
        profit = future_value - total_investment
        roi = profit / total_investment if total_investment > 0 else 0
        
        return roi
    
    def _calculate_break_even(self,
                             current_value: float,
                             dev_cost: float,
                             appreciation_rate: float) -> float:
        """
        Calculate years to break even (investment = current value)
        """
        total_investment = current_value + dev_cost
        
        if appreciation_rate <= 0:
            return float('inf')  # Never breaks even
        
        # Formula: Years = log(future/present) / log(1 + rate)
        years = math.log(total_investment / current_value) / math.log(1 + appreciation_rate)
        
        return max(0, years)
    
    def _recommend_plot_size(self,
                            satellite_data: Dict[str, Any],
                            scoring_result: Any) -> float:
        """
        Recommend investment plot size based on development stage
        """
        # Determine development stage from satellite activity
        construction_pct = satellite_data.get('construction_activity_pct', 0)
        
        if construction_pct > 30:
            # Late stage - smaller plots for immediate development
            return self.recommended_plot_sizes['late_stage']
        elif construction_pct > 10:
            # Mid stage - medium plots
            return self.recommended_plot_sizes['mid_stage']
        else:
            # Early stage - larger land acquisition play
            return self.recommended_plot_sizes['early_stage']
    
    def _assess_liquidity_risk(self,
                               region_name: str,
                               market_data: Dict[str, Any]) -> str:
        """Assess liquidity risk (ease of selling)"""
        benchmark = self._find_nearest_benchmark(region_name)
        liquidity = benchmark.get('market_liquidity', 'moderate')
        
        if liquidity == 'high':
            return 'Low'
        elif liquidity == 'moderate':
            return 'Medium'
        else:
            return 'High'
    
    def _assess_speculation_risk(self,
                                market_data: Dict[str, Any],
                                appreciation_rate: float) -> str:
        """Assess speculation/bubble risk"""
        # High appreciation + hot market = speculation risk
        market_heat = market_data.get('market_heat', 'unknown')
        
        if appreciation_rate > 0.20 and market_heat in ['hot', 'warming']:
            return 'High'
        elif appreciation_rate > 0.15:
            return 'Medium'
        else:
            return 'Low'
    
    def _assess_infrastructure_risk(self,
                                    infrastructure_data: Dict[str, Any]) -> str:
        """Assess infrastructure risk (dependency on future development)"""
        infra_score = infrastructure_data.get('infrastructure_score', 50)
        
        if infra_score >= 70:
            return 'Low'
        elif infra_score >= 50:
            return 'Medium'
        else:
            return 'High'
    
    def _calculate_projection_confidence(self,
                                        market_data: Dict[str, Any],
                                        infrastructure_data: Dict[str, Any],
                                        satellite_data: Dict[str, Any]) -> float:
        """Calculate confidence in financial projections"""
        # Based on data availability and quality
        market_conf = market_data.get('data_confidence', 0.5)
        infra_conf = infrastructure_data.get('data_confidence', 0.5)
        satellite_conf = 0.85  # Satellite is usually reliable
        
        # Weighted average
        overall = (satellite_conf * 0.4 + market_conf * 0.35 + infra_conf * 0.25)
        
        return overall
    
    def _find_nearest_benchmark(self, region_name: str) -> Dict[str, Any]:
        """Find nearest regional benchmark for a region"""
        region_lower = region_name.lower()
        
        # Direct matches
        for benchmark_name, data in self.regional_benchmarks.items():
            if benchmark_name in region_lower:
                return data
        
        # Province-level matches
        if 'jakarta' in region_lower or 'tangerang' in region_lower or 'bekasi' in region_lower:
            return self.regional_benchmarks['jakarta']
        elif 'yogya' in region_lower or 'sleman' in region_lower or 'bantul' in region_lower:
            return self.regional_benchmarks['yogyakarta']
        elif 'surabaya' in region_lower or 'sidoarjo' in region_lower:
            return self.regional_benchmarks['surabaya']
        elif 'bandung' in region_lower:
            return self.regional_benchmarks['bandung']
        elif 'semarang' in region_lower or 'solo' in region_lower:
            return self.regional_benchmarks['semarang']
        
        # Default to Yogyakarta (mid-tier market)
        return self.regional_benchmarks['yogyakarta']
    
    def _get_data_sources(self,
                         market_data: Dict[str, Any],
                         infrastructure_data: Dict[str, Any]) -> List[str]:
        """List data sources used in projection"""
        sources = ['satellite_sentinel2']
        
        if market_data.get('data_source') == 'live':
            sources.append('market_prices_live')
        else:
            sources.append('regional_benchmarks')
        
        if infrastructure_data.get('data_source') == 'osm_live':
            sources.append('openstreetmap')
        else:
            sources.append('infrastructure_fallback')
        
        return sources
    
    def format_financial_summary(self, projection: FinancialProjection) -> str:
        """
        Format financial projection as readable summary for reports
        """
        return f"""
💰 FINANCIAL PROJECTION - {projection.region_name}

LAND VALUE ESTIMATES:
  Current Value:        {projection.current_land_value_per_m2:,.0f} IDR/m²
  3-Year Projection:    {projection.estimated_future_value_per_m2:,.0f} IDR/m²
  Appreciation Rate:    {projection.appreciation_rate_annual:.1%} annually

DEVELOPMENT COSTS:
  Cost Index:           {projection.development_cost_index:.0f}/100 ({projection.terrain_difficulty})
  Estimated Cost:       {projection.estimated_dev_cost_per_m2:,.0f} IDR/m²

ROI PROJECTIONS:
  3-Year ROI:           {projection.projected_roi_3yr:.1%}
  5-Year ROI:           {projection.projected_roi_5yr:.1%}
  Break-Even:           {projection.break_even_years:.1f} years

INVESTMENT SIZING:
  Recommended Plot:     {projection.recommended_plot_size_m2:,.0f} m²
  Acquisition Cost:     {projection.total_acquisition_cost:,.0f} IDR ({projection.total_acquisition_cost / 1_000_000_000:.2f}B)
  Development Cost:     {projection.total_development_cost:,.0f} IDR ({projection.total_development_cost / 1_000_000:.0f}M)
  Projected Exit Value: {projection.projected_exit_value:,.0f} IDR ({projection.projected_exit_value / 1_000_000_000:.2f}B)
  Total Investment:     {(projection.total_acquisition_cost + projection.total_development_cost):,.0f} IDR
  Net Profit (3yr):     {(projection.projected_exit_value - projection.total_acquisition_cost - projection.total_development_cost):,.0f} IDR

RISK ASSESSMENT:
  Liquidity Risk:       {projection.liquidity_risk}
  Speculation Risk:     {projection.speculation_risk}
  Infrastructure Risk:  {projection.infrastructure_risk}
  
Projection Confidence:  {projection.projection_confidence:.0%}
Data Sources:           {', '.join(projection.data_sources)}
"""


# Standalone test function
def demo_financial_projection():
    """Demo the financial projection system"""
    engine = FinancialMetricsEngine()
    
    # Mock data
    from types import SimpleNamespace
    
    satellite_data = {
        'vegetation_loss_pixels': 5000,
        'total_pixels': 10000,
        'construction_activity_pct': 15
    }
    
    infrastructure_data = {
        'infrastructure_score': 72,
        'major_features': ['Highway A', 'Highway B'],
        'data_confidence': 0.85,
        'data_source': 'osm_live'
    }
    
    market_data = {
        'price_trend_30d': 10,  # 10% trend
        'market_heat': 'warming',
        'data_confidence': 0.75
    }
    
    scoring_result = SimpleNamespace(final_investment_score=68)
    
    projection = engine.calculate_financial_projection(
        'Sleman North',
        satellite_data,
        infrastructure_data,
        market_data,
        scoring_result
    )
    
    print(engine.format_financial_summary(projection))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    demo_financial_projection()
