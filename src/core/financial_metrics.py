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
    
    # Regional Context (NEW - v2.6-alpha)
    regional_tier: Optional[str] = None  # tier_1_metros, tier_2_secondary, tier_3_emerging, tier_4_frontier
    tier_benchmark_price: Optional[float] = None  # Expected price for tier
    peer_regions: Optional[List[str]] = None  # Other regions in same tier
    
    # Confidence
    projection_confidence: float = 0.0  # 0-1
    data_sources: Optional[List[str]] = None
    
    def __post_init__(self):
        """Ensure data_sources is initialized"""
        if self.data_sources is None:
            self.data_sources = []


class FinancialMetricsEngine:
    """
    Calculates financial projections and ROI estimates for land investment opportunities
    
    v2.7 CCAPI-27.0: Budget-Driven Investment Sizing
    - Calculates plot size from target budget (not tier-based hard-coded sizes)
    - Ensures investment recommendations align with small investor budgets ($50K-$150K USD)
    """
    
    def __init__(self, 
                 enable_web_scraping: bool = True, 
                 cache_expiry_hours: int = 24,
                 config: Optional[Any] = None):
        """
        Initialize with regional benchmarks and cost factors
        
        Args:
            enable_web_scraping: If True, attempt live scraping of land prices
            cache_expiry_hours: Hours before cached scrape data expires
            config: Optional AppConfig instance for budget-driven sizing (v2.7)
        """
        # Store config for budget-driven sizing (v2.7 CCAPI-27.0)
        self.config = config
        
        # Budget constraints (v2.7 CCAPI-27.0)
        if config and hasattr(config, 'financial_projections'):
            self.target_budget_idr = config.financial_projections.target_investment_budget_idr
            self.min_budget_idr = config.financial_projections.min_investment_budget_idr
            self.max_budget_idr = config.financial_projections.max_investment_budget_idr
            self.min_plot_size_m2 = config.financial_projections.min_plot_size_m2
            self.max_plot_size_m2 = config.financial_projections.max_plot_size_m2
            logger.info(f"✅ Budget-driven sizing enabled: Target Rp {self.target_budget_idr:,.0f} ({self.target_budget_idr/15000000:.0f}K USD)")
        else:
            # Fallback to defaults if config not provided
            self.target_budget_idr = 1500000000  # Rp 1.5B (~$100K USD)
            self.min_budget_idr = 750000000      # Rp 750M (~$50K USD)
            self.max_budget_idr = 2250000000     # Rp 2.25B (~$150K USD)
            self.min_plot_size_m2 = 500          # 500 m²
            self.max_plot_size_m2 = 50000        # 5 hectares
            logger.warning("⚠️ Config not provided, using default budget constraints")
        
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
        
        # v2.7 CCAPI-27.0: Removed hard-coded recommended_plot_sizes
        # Plot sizes now calculated dynamically from budget constraints
        # See _recommend_plot_size() method for budget-driven logic
    
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
        
        # Step 0: Get tier information (v2.6-alpha)
        tier_info = self._get_tier_info(region_name)
        
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
        
        # Step 6: Determine recommended investment size (v2.7 CCAPI-27.0: Budget-Driven)
        plot_size = self._recommend_plot_size(
            current_land_value_per_m2=current_value,
            dev_costs_per_m2=dev_costs['total_per_m2'],
            satellite_data=satellite_data,
            scoring_result=scoring_result
        )
        
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
            regional_tier=tier_info['tier'],
            tier_benchmark_price=tier_info['tier_benchmark_price'],
            peer_regions=tier_info['peer_regions'],
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
                            current_land_value_per_m2: float,
                            dev_costs_per_m2: float,
                            satellite_data: Dict[str, Any],
                            scoring_result: Any) -> float:
        """
        Recommend investment plot size based on TARGET BUDGET (v2.7 CCAPI-27.0)
        
        OLD BEHAVIOR (v2.6): Hard-coded tier-based sizes (5000/2000/1000 m²)
        NEW BEHAVIOR (v2.7): Calculate from budget = total_cost_per_m2 × plot_size
        
        Formula:
            total_cost_per_m2 = land_value_per_m2 + dev_costs_per_m2
            recommended_plot_size_m2 = TARGET_BUDGET_IDR / total_cost_per_m2
        
        Args:
            current_land_value_per_m2: Current land price per m²
            dev_costs_per_m2: Estimated development cost per m²
            satellite_data: Satellite data (for logging/context)
            scoring_result: Scoring result (for logging/context)
            
        Returns:
            Recommended plot size in m² that fits within target budget
        """
        # Calculate total cost per m² (land + development)
        total_cost_per_m2 = current_land_value_per_m2 + dev_costs_per_m2
        
        # Safety check: prevent division by zero
        if total_cost_per_m2 <= 0:
            logger.warning(f"⚠️ Invalid total cost per m² ({total_cost_per_m2:,.0f}), using minimum plot size")
            return self.min_plot_size_m2
        
        # Calculate plot size from budget
        budget_driven_plot_size = self.target_budget_idr / total_cost_per_m2
        
        # Apply min/max constraints
        constrained_plot_size = max(
            self.min_plot_size_m2,
            min(budget_driven_plot_size, self.max_plot_size_m2)
        )
        
        # Log the calculation for transparency
        logger.info(f"   💰 Budget-Driven Plot Sizing:")
        logger.info(f"      Target Budget: Rp {self.target_budget_idr:,.0f} (~${self.target_budget_idr/15000000:,.0f}K USD)")
        logger.info(f"      Land Price: Rp {current_land_value_per_m2:,.0f}/m²")
        logger.info(f"      Dev Costs: Rp {dev_costs_per_m2:,.0f}/m²")
        logger.info(f"      Total Cost: Rp {total_cost_per_m2:,.0f}/m²")
        logger.info(f"      Calculated Plot Size: {budget_driven_plot_size:,.0f} m²")
        
        if constrained_plot_size != budget_driven_plot_size:
            constraint = "minimum" if constrained_plot_size == self.min_plot_size_m2 else "maximum"
            logger.info(f"      ⚠️ Applied {constraint} constraint: {constrained_plot_size:,.0f} m²")
        else:
            logger.info(f"      ✅ Recommended Plot Size: {constrained_plot_size:,.0f} m² (within constraints)")
        
        return constrained_plot_size
    
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
        """
        Find benchmark data for a region using tier-based classification
        
        v2.6-alpha: Uses 4-tier regional hierarchy instead of 6 static benchmarks.
        Falls back to old system if market_config unavailable.
        """
        try:
            # Try tier-based lookup first (v2.6-alpha)
            from src.core.market_config import get_region_tier_info
            
            tier_info = get_region_tier_info(region_name)
            benchmarks = tier_info['benchmarks']
            
            # Convert tier benchmark format to financial metrics format
            return {
                'current_avg': benchmarks['avg_price_m2'],
                'historical_appreciation': benchmarks['expected_growth'],
                'market_liquidity': benchmarks['liquidity'],
                'tier': tier_info['tier'],
                'peer_regions': tier_info['peer_regions']
            }
            
        except (ImportError, KeyError) as e:
            # Fallback to old 6-benchmark system if tier classification unavailable
            logger.warning(f"Tier-based benchmark unavailable ({e}), using legacy system")
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
    
    def _get_tier_info(self, region_name: str) -> Dict[str, Any]:
        """
        Get tier classification information for a region
        
        Returns dict with: tier, tier_benchmark_price, peer_regions
        Returns None values if tier classification unavailable
        """
        try:
            from src.core.market_config import get_region_tier_info
            
            tier_info = get_region_tier_info(region_name)
            
            return {
                'tier': tier_info['tier'],
                'tier_benchmark_price': tier_info['benchmarks']['avg_price_m2'],
                'peer_regions': tier_info['peer_regions']
            }
        except (ImportError, KeyError) as e:
            logger.debug(f"Tier info unavailable for {region_name}: {e}")
            return {
                'tier': None,
                'tier_benchmark_price': None,
                'peer_regions': None
            }
    
    def calculate_relative_value_index(self,
                                       region_name: str,
                                       actual_price_m2: float,
                                       infrastructure_score: float,
                                       satellite_data: Dict[str, Any],
                                       tier_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate Relative Value Index (RVI) - v2.6-alpha
        
        RVI detects true undervaluation vs "just being cheap" by comparing actual price
        to expected price based on peer regions, infrastructure quality, and development momentum.
        
        Formula:
            Expected Price = Peer Region Avg × Infrastructure Premium × Momentum Premium
            RVI = Actual Price / Expected Price
        
        Interpretation:
            RVI < 0.80: Significantly undervalued (strong buy signal)
            RVI 0.80-0.95: Moderately undervalued (buy opportunity)
            RVI 0.95-1.05: Fairly valued (market equilibrium)
            RVI 1.05-1.20: Moderately overvalued (caution)
            RVI > 1.20: Significantly overvalued (speculation risk)
        
        Args:
            region_name: Region being analyzed
            actual_price_m2: Current land price per m² (IDR)
            infrastructure_score: Infrastructure quality score (0-100)
            satellite_data: Satellite change detection data
            tier_info: Optional tier classification info (will fetch if None)
        
        Returns:
            Dict with:
                - rvi: Relative value index (float)
                - expected_price_m2: Expected price based on fundamentals (float)
                - actual_price_m2: Actual market price (float)
                - peer_avg_price_m2: Average price of peer regions (float)
                - infrastructure_premium: Infrastructure adjustment factor (float)
                - momentum_premium: Development momentum adjustment (float)
                - interpretation: RVI interpretation string
                - confidence: Calculation confidence (0-1)
        """
        # Get tier info if not provided
        if tier_info is None:
            tier_info = self._get_tier_info(region_name)
        
        # If tier classification unavailable, return minimal RVI
        if tier_info['tier'] is None or tier_info['peer_regions'] is None:
            logger.warning(f"RVI calculation unavailable for {region_name} - no tier classification")
            return {
                'rvi': None,
                'expected_price_m2': None,
                'actual_price_m2': actual_price_m2,
                'peer_avg_price_m2': None,
                'infrastructure_premium': 1.0,
                'momentum_premium': 1.0,
                'interpretation': 'Insufficient peer data',
                'confidence': 0.0
            }
        
        # Step 1: Calculate peer region average price
        # For now, use tier benchmark as peer average (later can enhance with live scraping)
        peer_avg_price = tier_info.get('tier_benchmark_price', 3_000_000)
        
        # Step 2: Calculate infrastructure premium (Phase 2B.4: Tier-specific tolerance)
        # Compare region's infra score to tier baseline with tier-appropriate sensitivity
        try:
            from src.core.market_config import get_region_tier_info, get_infrastructure_tolerance
            tier_data = get_region_tier_info(region_name)
            tier_baseline_infra = tier_data['benchmarks'].get('infrastructure_baseline', 50)
            
            # Phase 2B.4: Get tier-specific tolerance (±15% Tier 1, ±20% Tier 2, ±25% Tier 3, ±30% Tier 4)
            infra_tolerance = get_infrastructure_tolerance(tier_info['tier'])
            max_premium_pct = infra_tolerance['tolerance_pct']  # e.g., 0.15 for Tier 1, 0.30 for Tier 4
        except (ImportError, KeyError):
            # Fallback to standard baselines and fixed ±20% tolerance
            tier_baseline_infra = {
                'tier_1_metros': 75,
                'tier_2_secondary': 60,
                'tier_3_emerging': 45,
                'tier_4_frontier': 30
            }.get(tier_info['tier'], 50)
            max_premium_pct = 0.20  # Fallback to fixed ±20%
        
        # Infrastructure premium: Tier-specific range based on deviation from tier baseline
        # Tier 1: ±15% (predictable infrastructure)
        # Tier 2: ±20% (standard variability)
        # Tier 3: ±25% (emerging uncertainty)
        # Tier 4: ±30% (frontier high variance)
        # Formula: +1% per point above baseline, -1% per point below baseline (capped at tier tolerance)
        infra_deviation = infrastructure_score - tier_baseline_infra
        infra_premium_pct = max(-max_premium_pct, min(max_premium_pct, infra_deviation / 100.0))
        infrastructure_premium = 1.0 + infra_premium_pct
        
        # Step 3: Calculate momentum premium
        # Based on satellite-detected development activity
        vegetation_loss = satellite_data.get('vegetation_loss_pixels', 0)
        construction_pct = satellite_data.get('construction_activity_pct', 0.0)
        
        # Momentum premium: ±15% based on development activity
        # High activity (construction > 15% or veg loss > 5000 pixels) = +10-15% premium
        # Low activity (construction < 5% and veg loss < 1000 pixels) = -5-10% discount
        if construction_pct > 0.15 or vegetation_loss > 5000:
            momentum_premium = 1.10  # Strong development momentum
        elif construction_pct > 0.10 or vegetation_loss > 3000:
            momentum_premium = 1.05  # Moderate development momentum
        elif construction_pct < 0.05 and vegetation_loss < 1000:
            momentum_premium = 0.95  # Low development momentum
        else:
            momentum_premium = 1.00  # Average development momentum
        
        # Step 3.5 (Phase 2B.2): Check for airport premium
        # Regions with airports opened in last 5 years get +25% benchmark premium
        try:
            from src.core.market_config import check_airport_premium
            airport_data = check_airport_premium(region_name)
            airport_premium = airport_data['premium_multiplier']
            
            if airport_data['has_premium']:
                logger.info(f"   ✈️ Airport premium: +25% for {airport_data['airport_name']} "
                           f"(opened {airport_data['opening_year']})")
        except (ImportError, Exception) as e:
            logger.debug(f"Airport premium check failed: {e}")
            airport_premium = 1.0
            airport_data = {'has_premium': False}
        
        # Step 4: Calculate expected price
        # Phase 2B.2: Include airport premium in expected price
        expected_price_m2 = peer_avg_price * infrastructure_premium * momentum_premium * airport_premium
        
        # Step 5: Calculate RVI
        rvi = actual_price_m2 / expected_price_m2 if expected_price_m2 > 0 else None
        
        # Step 6: Interpret RVI
        if rvi is None:
            interpretation = 'Calculation error'
            confidence = 0.0
        elif rvi < 0.80:
            interpretation = 'Significantly undervalued - Strong buy signal'
            confidence = 0.85
        elif rvi < 0.95:
            interpretation = 'Moderately undervalued - Buy opportunity'
            confidence = 0.85
        elif rvi < 1.05:
            interpretation = 'Fairly valued - Market equilibrium'
            confidence = 0.90
        elif rvi < 1.20:
            interpretation = 'Moderately overvalued - Exercise caution'
            confidence = 0.85
        else:
            interpretation = 'Significantly overvalued - Speculation risk'
            confidence = 0.80
        
        logger.info(f"RVI calculated for {region_name}: {rvi:.3f} ({interpretation})")
        
        return {
            'rvi': rvi,
            'expected_price_m2': expected_price_m2,
            'actual_price_m2': actual_price_m2,
            'peer_avg_price_m2': peer_avg_price,
            'infrastructure_premium': infrastructure_premium,
            'momentum_premium': momentum_premium,
            'airport_premium': airport_premium,  # Phase 2B.2
            'interpretation': interpretation,
            'confidence': confidence,
            'breakdown': {
                'peer_average': peer_avg_price,
                'infra_adjustment': infrastructure_premium,
                'infra_score_vs_baseline': f"{infrastructure_score:.0f} vs {tier_baseline_infra:.0f}",
                'momentum_adjustment': momentum_premium,
                'airport_adjustment': airport_premium,  # Phase 2B.2
                'airport_info': airport_data if airport_data['has_premium'] else None,  # Phase 2B.2
                'development_activity': f"{construction_pct:.1%} construction, {vegetation_loss:,} veg loss pixels",
                'expected_price': expected_price_m2,
                'actual_price': actual_price_m2,
                'value_gap': actual_price_m2 - expected_price_m2,
                'value_gap_pct': ((actual_price_m2 / expected_price_m2) - 1.0) if expected_price_m2 > 0 else 0.0
            }
        }
    
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
        data_sources_str = ', '.join(projection.data_sources) if projection.data_sources else 'N/A'
        
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
Data Sources:           {data_sources_str}
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
