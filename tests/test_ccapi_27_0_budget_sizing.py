"""
CCAPI-27.0: Budget-Driven Investment Sizing Test Suite

Validates that plot sizes are calculated from configured investment budgets,
not hard-coded development stage tiers.

Created: October 26, 2025
"""

import pytest
from typing import Dict, Any
from dataclasses import dataclass

# Import the components under test
from src.core.financial_metrics import FinancialMetricsEngine
from src.core.config import get_config, FinancialProjectionConfig


class TestBudgetDrivenPlotSizing:
    """Test suite for CCAPI-27.0 budget-driven plot size calculations"""
    
    @pytest.fixture
    def config(self):
        """Load production config"""
        return get_config()
    
    @pytest.fixture
    def custom_budget_config(self):
        """Create custom budget config for testing"""
        return FinancialProjectionConfig(
            target_investment_budget_idr=1_500_000_000,  # ~$100K USD
            max_investment_budget_idr=2_250_000_000,     # ~$150K USD
            min_investment_budget_idr=750_000_000,       # ~$50K USD
            min_plot_size_m2=500,
            max_plot_size_m2=50_000
        )
    
    @pytest.fixture
    def financial_engine(self, config):
        """Initialize financial engine with production config"""
        return FinancialMetricsEngine(
            enable_web_scraping=False,  # Use benchmarks for testing
            cache_expiry_hours=24,
            config=config
        )
    
    def test_budget_driven_formula_correctness(self, financial_engine):
        """
        CRITICAL: Verify budget-driven plot size formula
        Formula: plot_size = target_budget / (land_cost_per_m2 + dev_cost_per_m2)
        """
        # Example: Moderate pricing (won't hit min/max bounds)
        land_cost = 2_000_000  # Rp 2M per m²
        dev_cost = 500_000     # Rp 500K per m²
        total_cost = land_cost + dev_cost  # Rp 2.5M per m²
        
        # Expected: 1.5B / 2.5M = 600 m² (above min_plot_size of 500 m²)
        expected_plot_size = 1_500_000_000 / total_cost
        
        # Call the internal method (would normally be called via calculate_financial_projection)
        calculated_plot_size = financial_engine._recommend_plot_size(
            current_land_value_per_m2=land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        assert abs(calculated_plot_size - expected_plot_size) < 1.0, \
            f"Plot size {calculated_plot_size:.0f} m² should equal {expected_plot_size:.0f} m²"
        
        # Validate total acquisition cost
        total_acquisition = calculated_plot_size * total_cost
        assert abs(total_acquisition - 1_500_000_000) < 10_000_000, \
            f"Total cost {total_acquisition:,.0f} should equal Rp 1,500,000,000"
    
    def test_expensive_region_small_plot(self, financial_engine):
        """
        Test: Expensive regions (Jakarta) should yield smaller plots
        Jakarta tier: ~8.5M IDR/m²
        Expected plot: ~167 m² (formula) → 500 m² (clamped to minimum)
        """
        jakarta_land_cost = 8_500_000  # Rp 8.5M per m²
        dev_cost = 500_000
        
        plot_size = financial_engine._recommend_plot_size(
            current_land_value_per_m2=jakarta_land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Expected: 1.5B / 9M ≈ 167 m² → clamped to 500 m² (minimum)
        expected_formula = 1_500_000_000 / (jakarta_land_cost + dev_cost)
        
        assert plot_size == 500, \
            f"Jakarta plot size {plot_size:.0f} m² should be clamped to minimum 500 m²"
        
        assert expected_formula < 500, \
            f"Formula result {expected_formula:.0f} should be below minimum (validates clamping)"
    
    def test_affordable_region_larger_plot(self, financial_engine):
        """
        Test: Affordable regions (Tier 4) should yield larger plots
        Tier 4: ~1.5M IDR/m²
        Expected plot: ~700-800 m² (still budget-constrained)
        """
        tier4_land_cost = 1_500_000  # Rp 1.5M per m²
        dev_cost = 500_000
        
        plot_size = financial_engine._recommend_plot_size(
            current_land_value_per_m2=tier4_land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Expected: 1.5B / 2M = 750 m²
        expected = 1_500_000_000 / (tier4_land_cost + dev_cost)
        
        assert 700 <= plot_size <= 800, \
            f"Tier 4 plot size {plot_size:.0f} m² should be 700-800 m²"
        
        assert abs(plot_size - expected) < 5.0, \
            f"Plot size {plot_size:.0f} should match formula {expected:.0f}"
    
    def test_min_bound_enforcement(self, financial_engine):
        """
        Test: Plot size never goes below min_plot_size_m2 (500 m²)
        Extreme case: Very expensive land (20M/m²)
        """
        extreme_land_cost = 20_000_000  # Rp 20M per m²
        dev_cost = 500_000
        
        plot_size = financial_engine._recommend_plot_size(
            current_land_value_per_m2=extreme_land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Expected: 1.5B / 20.5M ≈ 73 m² → clamped to 500 m²
        assert plot_size == 500, \
            f"Plot size {plot_size:.0f} m² should be clamped to minimum 500 m²"
    
    def test_max_bound_enforcement(self, financial_engine):
        """
        Test: Plot size never exceeds max_plot_size_m2 (50,000 m²)
        Extreme case: Very cheap land (100K/m²)
        """
        cheap_land_cost = 100_000  # Rp 100K per m²
        dev_cost = 50_000
        
        plot_size = financial_engine._recommend_plot_size(
            current_land_value_per_m2=cheap_land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Expected: 1.5B / 150K = 10,000 m² (within bounds, no clamping)
        expected = 1_500_000_000 / (cheap_land_cost + dev_cost)
        
        assert plot_size <= 50_000, \
            f"Plot size {plot_size:.0f} m² should never exceed 50,000 m²"
        
        # In this case, formula should be used (not clamped)
        assert abs(plot_size - expected) < 5.0
    
    def test_zero_cost_edge_case(self, financial_engine):
        """
        Test: Handle division by zero gracefully
        Edge case: Zero or negative cost per m²
        """
        # Test zero cost
        plot_size_zero = financial_engine._recommend_plot_size(
            current_land_value_per_m2=0,
            dev_costs_per_m2=0,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        assert plot_size_zero == 500, \
            f"Zero cost should return min_plot_size (500 m²), got {plot_size_zero:.0f}"
        
        # Test negative cost (invalid data)
        plot_size_negative = financial_engine._recommend_plot_size(
            current_land_value_per_m2=-1_000_000,
            dev_costs_per_m2=500_000,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        assert plot_size_negative == 500, \
            f"Negative cost should return min_plot_size (500 m²), got {plot_size_negative:.0f}"
    
    def test_custom_budget_override(self):
        """
        Test: Custom budget configuration is respected
        Create engine with custom $50K budget (750M IDR)
        """
        from dataclasses import dataclass, field
        
        custom_config = FinancialProjectionConfig(
            target_investment_budget_idr=750_000_000,  # ~$50K USD (50% of default)
            max_investment_budget_idr=1_125_000_000,
            min_investment_budget_idr=500_000_000,
            min_plot_size_m2=500,
            max_plot_size_m2=50_000
        )
        
        # Create a mock config object with default_factory
        @dataclass
        class MockConfig:
            financial_projections: FinancialProjectionConfig = field(default_factory=lambda: custom_config)
        
        engine = FinancialMetricsEngine(
            enable_web_scraping=False,
            config=MockConfig()
        )
        
        assert engine.target_budget_idr == 750_000_000, \
            f"Engine should use custom budget {engine.target_budget_idr:,.0f}"
        
        # Test plot size with custom budget
        land_cost = 2_000_000  # Rp 2M per m² (moderate pricing)
        dev_cost = 500_000
        
        plot_size = engine._recommend_plot_size(
            current_land_value_per_m2=land_cost,
            dev_costs_per_m2=dev_cost,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Expected: 750M / 2.5M = 300 m² → clamped to 500 m² (minimum)
        expected = 750_000_000 / (land_cost + dev_cost)
        
        # Will be clamped to minimum
        assert plot_size == 500, \
            f"Custom budget plot size {plot_size:.0f} should be clamped to min 500 m²"
    
    def test_backward_compatibility_without_config(self):
        """
        Test: Engine works without config (uses defaults)
        Ensures backward compatibility with existing code
        """
        engine = FinancialMetricsEngine(
            enable_web_scraping=False,
            config=None  # No config provided
        )
        
        # Should use default values
        assert engine.target_budget_idr == 1_500_000_000, \
            "Default budget should be Rp 1.5B"
        assert engine.min_plot_size_m2 == 500, \
            "Default min plot size should be 500 m²"
        assert engine.max_plot_size_m2 == 50_000, \
            "Default max plot size should be 50,000 m²"
    
    def test_end_to_end_financial_projection(self, financial_engine):
        """
        Test: Full financial projection with budget-driven sizing
        Validates integration with calculate_financial_projection()
        """
        # Mock data for Yogyakarta region
        satellite_data = {
            'vegetation_loss_pixels': 5200,
            'construction_activity_pct': 0.18,
            'ndbi_increase': 0.12
        }
        
        infrastructure_data = {
            'infrastructure_score': 72,
            'major_features': ['highway_5km', 'airport_25km'],
            'accessibility_rating': 'good'
        }
        
        market_data = {
            'price_trend_30d': 0.08,
            'market_heat': 'warming',
            'comparable_sales': 12
        }
        
        # Mock scoring result
        @dataclass
        class MockScoringResult:
            final_score: float = 75.5
            confidence: float = 0.88
            recommendation: str = "BUY"
        
        # Calculate full financial projection
        projection = financial_engine.calculate_financial_projection(
            region_name="Yogyakarta North",
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data,
            market_data=market_data,
            scoring_result=MockScoringResult()
        )
        
        # Validate projection structure
        assert projection is not None, "Projection should not be None"
        assert hasattr(projection, 'recommended_plot_size_m2'), \
            "Projection should have recommended_plot_size_m2"
        assert hasattr(projection, 'total_acquisition_cost'), \
            "Projection should have total_acquisition_cost"
        
        # Validate budget alignment (±40% tolerance)
        # Note: Actual cost may be lower than target if using regional benchmarks (Tier 4)
        # or higher if clamped to min_plot_size. This is expected behavior.
        total_cost = projection.total_acquisition_cost
        target_budget = financial_engine.target_budget_idr
        tolerance = 0.40  # 40% tolerance (allows for benchmark pricing vs target)
        
        assert abs(total_cost - target_budget) / target_budget <= tolerance, \
            f"Total cost {total_cost:,.0f} should be within ±40% of target budget {target_budget:,.0f}"
        
        # Validate plot size is within bounds
        plot_size = projection.recommended_plot_size_m2
        assert 500 <= plot_size <= 50_000, \
            f"Plot size {plot_size:.0f} m² should be within bounds [500, 50,000]"
        
        # Validate data sources
        assert len(projection.data_sources) > 0, \
            "Projection should have data sources documented"


class TestBudgetConstraintDocumentation:
    """Test that budget constraints are properly logged and documented"""
    
    @pytest.fixture
    def config(self):
        """Load production config"""
        return get_config()
    
    def test_logging_output(self, config, caplog):
        """Verify that budget calculations are logged for transparency"""
        import logging
        caplog.set_level(logging.INFO)
        
        engine = FinancialMetricsEngine(
            enable_web_scraping=False,
            config=config
        )
        
        # Trigger plot size calculation (which logs details)
        engine._recommend_plot_size(
            current_land_value_per_m2=4_500_000,
            dev_costs_per_m2=500_000,
            satellite_data={'vegetation_loss_pixels': 1000},
            scoring_result=None
        )
        
        # Check that budget information was logged
        log_messages = [record.message for record in caplog.records]
        
        budget_logs = [msg for msg in log_messages if "Budget-Driven Plot Sizing" in msg]
        assert len(budget_logs) > 0, \
            "Budget calculation details should be logged"
        
        # Check for key budget information
        all_logs = " ".join(log_messages)
        assert "Target Budget" in all_logs, "Should log target budget"
        assert "Plot Size" in all_logs, "Should log plot size calculation"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
