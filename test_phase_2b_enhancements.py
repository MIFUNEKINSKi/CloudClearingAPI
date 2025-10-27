"""
Phase 2B Unit Tests - RVI-Aware Market Multiplier

Tests for v2.6-beta enhancements:
- Phase 2B.1: RVI-aware market multiplier
- Phase 2B.2: Airport premium override (pending)
- Phase 2B.3: Tier 1+ sub-classification (pending)
- Phase 2B.4: Tier-specific infrastructure ranges (pending)

Date: October 25, 2025
Version: 2.6-beta
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.core.corrected_scoring import CorrectedInvestmentScorer
from src.core.financial_metrics import FinancialMetricsEngine


class TestPhase2B1_RVIAwareMultiplier:
    """Test RVI-aware market multiplier (Phase 2B.1)"""
    
    def test_rvi_significantly_undervalued(self):
        """RVI < 0.7 should give 1.40x base multiplier"""
        # Setup mock engines
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        # Mock pricing data
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.05  # 5% trend
        pricing_data.avg_price_per_m2 = 3500000  # 3.5M IDR
        pricing_data.market_heat = 'warming'
        pricing_data.data_confidence = 0.85
        price_engine._get_pricing_data.return_value = pricing_data
        
        # Mock RVI calculation
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 0.65,  # Significantly undervalued
            'interpretation': 'Significantly Undervalued',
            'expected_price_m2': 5384615
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        # Test market multiplier calculation
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 1000, 'area_affected_m2': 50000}
        infrastructure_data = {'infrastructure_score': 65}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.40 × momentum (1 + 0.05 * 0.1) = 1.40 × 1.005 = 1.407
        assert 1.40 <= multiplier <= 1.41, f"Expected 1.40-1.41, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
        assert market_data['rvi'] == 0.65
    
    def test_rvi_undervalued(self):
        """RVI 0.7-0.9 should give 1.25x base multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.03  # 3% trend
        pricing_data.avg_price_per_m2 = 4200000
        pricing_data.market_heat = 'stable'
        pricing_data.data_confidence = 0.80
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 0.85,  # Undervalued
            'interpretation': 'Undervalued',
            'expected_price_m2': 4941176
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 800}
        infrastructure_data = {'infrastructure_score': 72}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.25 × momentum (1 + 0.03 * 0.1) = 1.25 × 1.003 = 1.254
        assert 1.25 <= multiplier <= 1.26, f"Expected 1.25-1.26, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_fair_value(self):
        """RVI 0.9-1.1 should give 1.0x base multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.0  # No trend
        pricing_data.avg_price_per_m2 = 5000000
        pricing_data.market_heat = 'stable'
        pricing_data.data_confidence = 0.85
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 1.0,  # Fair value
            'interpretation': 'Fair Value',
            'expected_price_m2': 5000000
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 1200}
        infrastructure_data = {'infrastructure_score': 78}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.0 × momentum (1 + 0.0 * 0.1) = 1.0
        assert multiplier == 1.0, f"Expected 1.0, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_overvalued(self):
        """RVI 1.1-1.3 should give 0.90x base multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.08  # 8% trend (still growing despite overvaluation)
        pricing_data.avg_price_per_m2 = 9200000
        pricing_data.market_heat = 'hot'
        pricing_data.data_confidence = 0.90
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 1.15,  # Overvalued
            'interpretation': 'Overvalued',
            'expected_price_m2': 8000000
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 500}
        infrastructure_data = {'infrastructure_score': 85}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 0.90 × momentum (1 + 0.08 * 0.1) = 0.90 × 1.008 = 0.907
        assert 0.90 <= multiplier <= 0.91, f"Expected 0.90-0.91, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_significantly_overvalued(self):
        """RVI >= 1.3 should give 0.85x base multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.15  # 15% trend (speculation bubble)
        pricing_data.avg_price_per_m2 = 12000000
        pricing_data.market_heat = 'overheated'
        pricing_data.data_confidence = 0.75
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 1.35,  # Significantly overvalued
            'interpretation': 'Significantly Overvalued',
            'expected_price_m2': 8888889
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 300}
        infrastructure_data = {'infrastructure_score': 90}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 0.85 × momentum (1 + 0.15 * 0.1) = 0.85 × 1.015 = 0.863
        # But clamped to minimum 0.85
        assert multiplier >= 0.85, f"Expected >= 0.85, got {multiplier}"
        assert multiplier <= 0.87, f"Expected <= 0.87, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_fallback_to_trend(self):
        """When RVI unavailable, fallback to trend-based multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = None  # No financial engine
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.12  # 12% trend
        pricing_data.avg_price_per_m2 = 5500000
        pricing_data.market_heat = 'warming'
        pricing_data.data_confidence = 0.80
        price_engine._get_pricing_data.return_value = pricing_data
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 1000}
        infrastructure_data = {'infrastructure_score': 70}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Should use trend-based: 12% → Strong (1.20x)
        assert multiplier == 1.20, f"Expected 1.20 (trend-based), got {multiplier}"
        assert market_data['multiplier_basis'] == 'trend_based'
    
    def test_rvi_exception_fallback(self):
        """When RVI calculation throws exception, fallback to trend-based"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.05  # 5% trend
        pricing_data.avg_price_per_m2 = 4800000
        pricing_data.market_heat = 'stable'
        pricing_data.data_confidence = 0.85
        price_engine._get_pricing_data.return_value = pricing_data
        
        # RVI calculation raises exception
        financial_engine.calculate_relative_value_index.side_effect = Exception("Tier not found")
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 900}
        infrastructure_data = {'infrastructure_score': 68}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Should fallback to trend-based: 5% → Stable (1.00x)
        assert multiplier == 1.00, f"Expected 1.00 (trend fallback), got {multiplier}"
        assert market_data['multiplier_basis'] == 'trend_based'
    
    def test_rvi_momentum_positive(self):
        """Positive momentum should slightly increase multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.10  # 10% positive trend
        pricing_data.avg_price_per_m2 = 4500000
        pricing_data.market_heat = 'warming'
        pricing_data.data_confidence = 0.85
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 0.95,  # Fair value
            'interpretation': 'Fair Value',
            'expected_price_m2': 4736842
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 1100}
        infrastructure_data = {'infrastructure_score': 75}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.0 × momentum (1 + 0.10 * 0.1) = 1.0 × 1.01 = 1.01
        assert 1.00 <= multiplier <= 1.02, f"Expected 1.00-1.02, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_momentum_negative(self):
        """Negative momentum should slightly decrease multiplier"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = -0.05  # -5% negative trend
        pricing_data.avg_price_per_m2 = 4600000
        pricing_data.market_heat = 'cooling'
        pricing_data.data_confidence = 0.80
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 1.05,  # Fair value
            'interpretation': 'Fair Value',
            'expected_price_m2': 4380952
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 700}
        infrastructure_data = {'infrastructure_score': 60}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.0 × momentum (1 + (-0.05) * 0.1) = 1.0 × 0.995 = 0.995
        assert 0.99 <= multiplier <= 1.00, f"Expected 0.99-1.00, got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_clamping_upper_bound(self):
        """Multiplier should be clamped to 1.40 maximum"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = 0.20  # 20% explosive trend
        pricing_data.avg_price_per_m2 = 3000000
        pricing_data.market_heat = 'booming'
        pricing_data.data_confidence = 0.70
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 0.60,  # Significantly undervalued
            'interpretation': 'Significantly Undervalued',
            'expected_price_m2': 5000000
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 2000}
        infrastructure_data = {'infrastructure_score': 55}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 1.40 × momentum (1 + 0.20 * 0.1) = 1.40 × 1.02 = 1.428
        # Clamped to 1.40
        assert multiplier == 1.40, f"Expected 1.40 (clamped), got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'
    
    def test_rvi_clamping_lower_bound(self):
        """Multiplier should be clamped to 0.85 minimum"""
        price_engine = Mock()
        infrastructure_engine = Mock()
        financial_engine = Mock()
        
        pricing_data = Mock()
        pricing_data.price_trend_3m = -0.10  # -10% declining trend
        pricing_data.avg_price_per_m2 = 11000000
        pricing_data.market_heat = 'declining'
        pricing_data.data_confidence = 0.65
        price_engine._get_pricing_data.return_value = pricing_data
        
        financial_engine.calculate_relative_value_index.return_value = {
            'rvi': 1.40,  # Significantly overvalued
            'interpretation': 'Significantly Overvalued',
            'expected_price_m2': 7857143
        }
        
        scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine, financial_engine)
        
        data_availability = {}
        satellite_data = {'vegetation_loss_pixels': 200}
        infrastructure_data = {'infrastructure_score': 92}
        
        market_data, multiplier = scorer._get_market_multiplier(
            region_name="test_region",
            coordinates={'lat': -7.7, 'lon': 110.4},
            data_availability=data_availability,
            satellite_data=satellite_data,
            infrastructure_data=infrastructure_data
        )
        
        # Base 0.85 × momentum (1 + (-0.10) * 0.1) = 0.85 × 0.99 = 0.842
        # Clamped to 0.85
        assert multiplier == 0.85, f"Expected 0.85 (clamped), got {multiplier}"
        assert market_data['multiplier_basis'] == 'rvi_aware'


class TestPhase2B2_AirportPremium:
    """Test airport premium override (Phase 2B.2)"""
    
    def test_airport_premium_recent_construction(self):
        """Regions with airports built in last 5 years should get +25% premium"""
        from src.core.market_config import check_airport_premium
        
        # Yogyakarta North - YIA opened 2020 (5 years ago in 2025)
        result = check_airport_premium('yogyakarta_north', current_year=2025)
        
        assert result['has_premium'] is True
        assert result['premium_multiplier'] == 1.25
        assert result['airport_name'] == 'Yogyakarta International Airport'
        assert result['opening_year'] == 2020
        assert result['years_since_opening'] == 5
    
    def test_airport_premium_sleman_north(self):
        """Sleman North should get YIA airport premium"""
        from src.core.market_config import check_airport_premium
        
        result = check_airport_premium('sleman_north', current_year=2025)
        
        assert result['has_premium'] is True
        assert result['premium_multiplier'] == 1.25
        assert result['airport_iata'] == 'YIA'
    
    def test_airport_premium_kulon_progo(self):
        """Kulon Progo should get YIA airport premium"""
        from src.core.market_config import check_airport_premium
        
        result = check_airport_premium('kulonprogo_west', current_year=2025)
        
        assert result['has_premium'] is True
        assert result['premium_multiplier'] == 1.25
    
    def test_airport_premium_banyuwangi(self):
        """Banyuwangi should get airport expansion premium (2021)"""
        from src.core.market_config import check_airport_premium
        
        result = check_airport_premium('banyuwangi_coastal', current_year=2025)
        
        assert result['has_premium'] is True
        assert result['premium_multiplier'] == 1.25
        assert result['airport_name'] == 'Banyuwangi Airport (Blimbingsari)'
        assert result['opening_year'] == 2021
        assert result['years_since_opening'] == 4
    
    def test_airport_premium_old_construction(self):
        """Regions with older airports should not get premium"""
        from src.core.market_config import check_airport_premium
        
        # Jakarta has old airports (Soekarno-Hatta opened 1985)
        result = check_airport_premium('jakarta_north_sprawl', current_year=2025)
        
        assert result['has_premium'] is False
        assert result['premium_multiplier'] == 1.0
        assert result['airport_name'] is None
    
    def test_airport_premium_no_airport(self):
        """Regions without airports should not get premium"""
        from src.core.market_config import check_airport_premium
        
        result = check_airport_premium('magelang_corridor', current_year=2025)
        
        assert result['has_premium'] is False
        assert result['premium_multiplier'] == 1.0
    
    def test_airport_premium_expires_after_5_years(self):
        """Airport premium should expire after 5 years"""
        from src.core.market_config import check_airport_premium
        
        # Test YIA in 2026 (6 years after opening)
        result = check_airport_premium('yogyakarta_north', current_year=2026)
        
        assert result['has_premium'] is False
        assert result['premium_multiplier'] == 1.0
    
    def test_rvi_with_airport_premium(self):
        """RVI calculation should include airport premium"""
        from src.core.financial_metrics import FinancialMetricsEngine
        from unittest.mock import patch
        
        engine = FinancialMetricsEngine(enable_web_scraping=False)
        
        # Mock the airport premium check at market_config level
        with patch('src.core.market_config.check_airport_premium') as mock_airport:
            mock_airport.return_value = {
                'has_premium': True,
                'premium_multiplier': 1.25,
                'airport_name': 'Yogyakarta International Airport',
                'airport_iata': 'YIA',
                'opening_year': 2020,
                'years_since_opening': 5,
                'justification': 'New international airport opened 2020'
            }
            
            # Calculate RVI for yogyakarta_urban_core (Tier 2) with airport premium
            result = engine.calculate_relative_value_index(
                region_name='yogyakarta_urban_core',
                actual_price_m2=5_000_000,  # Actual price
                infrastructure_score=75,
                satellite_data={'vegetation_loss_pixels': 2000, 'construction_activity_pct': 0.08}
            )
            
            # Expected price calculation:
            # Peer avg (5M tier 2) × infra (~1.15 for infra 75 vs baseline 60) × momentum (1.0) × airport (1.25) = ~7.2M
            # RVI = 5M / ~7.2M = ~0.69 (undervalued)
            assert result['airport_premium'] == 1.25
            assert 'airport_info' in result['breakdown']
            assert result['breakdown']['airport_adjustment'] == 1.25
            
            # RVI should reflect the airport premium adjustment (lower RVI with airport premium)
            # Without airport premium (1.0): RVI would be ~0.87
            # With airport premium (1.25): RVI is ~0.70 (more undervalued)
            assert 0.65 <= result['rvi'] <= 0.75, f"Expected RVI ~0.70, got {result['rvi']}"


class TestPhase2B3_Tier1Plus:
    """Test Tier 1+ sub-classification (Phase 2B.3)"""
    
    def test_tier1_plus_bsd_corridor(self):
        """BSD Corridor should use 9.5M benchmark (Tier 1+ ultra-premium)"""
        from src.core.market_config import get_tier_benchmark, classify_region_tier
        
        # Classify BSD corridor as Tier 1
        tier = classify_region_tier('tangerang_bsd_corridor')
        assert tier == 'tier_1_metros'
        
        # Get benchmark with region name (Tier 1+ override)
        tier1_plus_benchmark = get_tier_benchmark(tier, region_name='tangerang_bsd_corridor')
        
        assert tier1_plus_benchmark['avg_price_m2'] == 9_500_000
        assert tier1_plus_benchmark.get('tier_1_plus_override') is True
        assert tier1_plus_benchmark.get('description') == 'Tier 1+ Ultra-Premium'
    
    def test_tier1_plus_senopati(self):
        """Jakarta South Suburbs (Senopati) should use 9.5M benchmark"""
        from src.core.market_config import get_tier_benchmark, classify_region_tier
        
        tier = classify_region_tier('jakarta_south_suburbs')
        assert tier == 'tier_1_metros'
        
        # Get benchmark with Tier 1+ override
        tier1_plus_benchmark = get_tier_benchmark(tier, region_name='jakarta_south_suburbs')
        
        assert tier1_plus_benchmark['avg_price_m2'] == 9_500_000
        assert tier1_plus_benchmark.get('tier_1_plus_override') is True
    
    def test_tier1_standard_not_affected(self):
        """Regular Tier 1 regions without Tier 1+ status should use 8M benchmark"""
        from src.core.market_config import get_tier_benchmark, classify_region_tier
        
        tier = classify_region_tier('jakarta_north_sprawl')
        assert tier == 'tier_1_metros'
        
        # Get benchmark without Tier 1+ override
        standard_benchmark = get_tier_benchmark(tier, region_name='jakarta_north_sprawl')
        
        assert standard_benchmark['avg_price_m2'] == 8_000_000  # Standard Tier 1
        assert standard_benchmark.get('tier_1_plus_override') is not True
        assert standard_benchmark.get('description') != 'Tier 1+ Ultra-Premium'
    
    def test_tier1_plus_via_get_region_tier_info(self):
        """get_region_tier_info should automatically apply Tier 1+ benchmarks"""
        from src.core.market_config import get_region_tier_info
        
        # BSD Corridor should get Tier 1+ treatment
        info = get_region_tier_info('tangerang_bsd_corridor')
        
        assert info['tier'] == 'tier_1_metros'
        assert info['benchmarks']['avg_price_m2'] == 9_500_000
        assert info['benchmarks'].get('tier_1_plus_override') is True
        
        # Standard Tier 1 should remain at 8M
        standard_info = get_region_tier_info('surabaya_west_expansion')
        
        assert standard_info['tier'] == 'tier_1_metros'
        assert standard_info['benchmarks']['avg_price_m2'] == 8_000_000
        assert standard_info['benchmarks'].get('tier_1_plus_override') is not True
    
    def test_tier1_plus_all_regions(self):
        """All TIER_1_PLUS_REGIONS should get 9.5M benchmark"""
        from src.core.market_config import TIER_1_PLUS_REGIONS, get_tier_benchmark, classify_region_tier
        
        for region in TIER_1_PLUS_REGIONS:
            # Skip regions that might not exist in REGIONAL_HIERARCHY
            tier = classify_region_tier(region)
            
            if tier == 'tier_1_metros':
                benchmark = get_tier_benchmark(tier, region_name=region)
                assert benchmark['avg_price_m2'] == 9_500_000, \
                    f"Region {region} should have 9.5M benchmark, got {benchmark['avg_price_m2']}"
                assert benchmark.get('tier_1_plus_override') is True
    
    def test_rvi_with_tier1_plus_benchmark(self):
        """RVI calculation should use 9.5M benchmark for BSD Corridor"""
        from src.core.financial_metrics import FinancialMetricsEngine
        
        engine = FinancialMetricsEngine(enable_web_scraping=False)
        
        # Calculate RVI for BSD Corridor (Tier 1+ with 9.5M benchmark)
        result = engine.calculate_relative_value_index(
            region_name='tangerang_bsd_corridor',
            actual_price_m2=10_000_000,  # Actual price 10M
            infrastructure_score=80,
            satellite_data={'vegetation_loss_pixels': 1500, 'construction_activity_pct': 0.12}
        )
        
        # Expected price calculation:
        # Peer avg (9.5M tier 1+) × infra (~1.07 for infra 80 vs baseline 75) × momentum (1.0) = ~10.2M
        # RVI = 10M / ~10.2M = ~0.98 (fair value)
        assert 0.95 <= result['rvi'] <= 1.05, f"Expected RVI ~0.98-1.02 (fair value), got {result['rvi']}"
        
        # Compare to if BSD was treated as standard Tier 1 (8M):
        # Expected would be ~8.6M, RVI would be 10M/8.6M = 1.16 (overvalued)
        # With Tier 1+ (9.5M): Expected is ~10.2M, RVI is 10M/10.2M = 0.98 (fair)
        # This proves Tier 1+ correctly recognizes BSD's ultra-premium status
    
    def test_tier2_not_affected_by_tier1_plus(self):
        """Tier 2 regions should not be affected by Tier 1+ logic"""
        from src.core.market_config import get_tier_benchmark, classify_region_tier
        
        tier = classify_region_tier('bandung_north_expansion')
        assert tier == 'tier_2_secondary'
        
        # Get benchmark - should be standard Tier 2 (5M)
        benchmark = get_tier_benchmark(tier, region_name='bandung_north_expansion')
        
        assert benchmark['avg_price_m2'] == 5_000_000  # Standard Tier 2
        assert benchmark.get('tier_1_plus_override') is not True


class TestPhase2B4_TierSpecificInfraRanges:
    """Test tier-specific infrastructure ranges (Phase 2B.4)"""
    
    def test_tier1_narrow_range(self):
        """Tier 1 metros should use ±15% infrastructure tolerance"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tolerance = get_infrastructure_tolerance('tier_1_metros')
        
        assert tolerance['tolerance_pct'] == 0.15  # ±15%
        assert tolerance['baseline_score'] == 75
        assert 'Predictable' in tolerance['rationale'] or 'consistent' in tolerance['rationale'].lower()
    
    def test_tier2_standard_range(self):
        """Tier 2 secondary should use ±20% infrastructure tolerance"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tolerance = get_infrastructure_tolerance('tier_2_secondary')
        
        assert tolerance['tolerance_pct'] == 0.20  # ±20%
        assert tolerance['baseline_score'] == 60
    
    def test_tier3_wider_range(self):
        """Tier 3 emerging should use ±25% infrastructure tolerance"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tolerance = get_infrastructure_tolerance('tier_3_emerging')
        
        assert tolerance['tolerance_pct'] == 0.25  # ±25%
        assert tolerance['baseline_score'] == 45
    
    def test_tier4_wide_range(self):
        """Tier 4 frontier should use ±30% infrastructure tolerance (widest)"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tolerance = get_infrastructure_tolerance('tier_4_frontier')
        
        assert tolerance['tolerance_pct'] == 0.30  # ±30%
        assert tolerance['baseline_score'] == 30
        assert 'frontier' in tolerance['rationale'].lower() or 'unpredictable' in tolerance['rationale'].lower()
    
    def test_rvi_tier1_infrastructure_premium(self):
        """RVI for Tier 1 should use ±15% infrastructure premium range"""
        from src.core.financial_metrics import FinancialMetricsEngine
        
        engine = FinancialMetricsEngine(enable_web_scraping=False)
        
        # Test Jakarta North (Tier 1) with high infrastructure (90 vs baseline 75 = +15 points)
        result = engine.calculate_relative_value_index(
            region_name='jakarta_north_sprawl',
            actual_price_m2=9_000_000,
            infrastructure_score=90,  # +15 above baseline 75
            satellite_data={'vegetation_loss_pixels': 2000, 'construction_activity_pct': 0.08}
        )
        
        # Infrastructure premium calculation:
        # Deviation: 90 - 75 = +15 points
        # Premium pct: +15/100 = 0.15 (capped at ±15% for Tier 1)
        # Premium multiplier: 1.0 + 0.15 = 1.15x
        # Expected price: 8M × 1.15 = 9.2M
        # RVI: 9M / 9.2M = 0.978 (fair value)
        
        assert 'infrastructure_premium' in result
        # Infrastructure premium should be capped at 1.15 (Tier 1 max +15%)
        assert result['infrastructure_premium'] == 1.15, \
            f"Expected 1.15 (Tier 1 +15% cap), got {result['infrastructure_premium']}"
    
    def test_rvi_tier4_infrastructure_premium(self):
        """RVI for Tier 4 should use ±30% infrastructure premium range (widest)"""
        from src.core.financial_metrics import FinancialMetricsEngine
        
        engine = FinancialMetricsEngine(enable_web_scraping=False)
        
        # Test Pacitan (Tier 4) with high infrastructure (60 vs baseline 30 = +30 points)
        result = engine.calculate_relative_value_index(
            region_name='pacitan_coastal',
            actual_price_m2=3_000_000,
            infrastructure_score=60,  # +30 above baseline 30
            satellite_data={'vegetation_loss_pixels': 1000, 'construction_activity_pct': 0.05}
        )
        
        # Infrastructure premium calculation:
        # Deviation: 60 - 30 = +30 points
        # Premium pct: +30/100 = 0.30 (capped at ±30% for Tier 4)
        # Premium multiplier: 1.0 + 0.30 = 1.30x
        # Expected price: 2M × 1.30 = 2.6M
        # RVI: 3M / 2.6M = 1.15 (overvalued - but less than before)
        
        # With Phase 2B.4: Premium can reach 1.30 (±30% for Tier 4)
        # Before Phase 2B.4: Premium capped at 1.20 (fixed ±20%)
        assert result['infrastructure_premium'] == 1.30, \
            f"Expected 1.30 (Tier 4 +30% cap), got {result['infrastructure_premium']}"
    
    def test_rvi_pacitan_correction(self):
        """Tier 4 frontier RVI should reflect wider ±30% infrastructure tolerance"""
        from src.core.financial_metrics import FinancialMetricsEngine
        
        engine = FinancialMetricsEngine(enable_web_scraping=False)
        
        # Test Tegal Brebes Coastal (actual Tier 4 region) with good infrastructure
        # Scenario: Frontier region with surprisingly good infrastructure
        result = engine.calculate_relative_value_index(
            region_name='tegal_brebes_coastal',
            actual_price_m2=2_000_000,  # Actual price 2M
            infrastructure_score=60,  # Good for frontier (+30 above baseline 30)
            satellite_data={'vegetation_loss_pixels': 800, 'construction_activity_pct': 0.04}
        )
        
        # Expected price calculation:
        # Peer avg (Tier 4): 1.5M IDR/m²
        # Infrastructure: 60 vs baseline 30 = +30 points
        # Phase 2B.4: Premium pct: +30/100 = 0.30 (capped at ±30% for Tier 4)
        # Infrastructure premium: 1.30x
        # Momentum: Low activity → 0.95x
        # Expected: 1.5M × 1.30 × 0.95 = 1.85M
        # RVI: 2M / 1.85M = 1.08 (slightly overvalued)
        
        # Before Phase 2B.4 (fixed ±20%):
        # Premium: 1.20x (capped at ±20%)
        # Expected: 1.5M × 1.20 × 0.95 = 1.71M
        # RVI: 2M / 1.71M = 1.17 (more overvalued)
        
        # With Phase 2B.4, RVI should be LOWER (less overvalued) due to higher expected price
        # Infrastructure premium should reach 1.30 (not capped at 1.20)
        assert result['infrastructure_premium'] == 1.30, \
            f"Expected 1.30 (Tier 4 allows ±30%), got {result['infrastructure_premium']}"
        
        # RVI should be in reasonable range for frontier region
        assert 0.80 <= result['rvi'] <= 1.30, \
            f"Expected RVI 0.80-1.30 (frontier correction), got {result['rvi']}"
    
    def test_tier_tolerance_progressive(self):
        """Tolerance should progressively widen from Tier 1 to Tier 4"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tier1 = get_infrastructure_tolerance('tier_1_metros')
        tier2 = get_infrastructure_tolerance('tier_2_secondary')
        tier3 = get_infrastructure_tolerance('tier_3_emerging')
        tier4 = get_infrastructure_tolerance('tier_4_frontier')
        
        # Tolerance should increase progressively
        assert tier1['tolerance_pct'] < tier2['tolerance_pct']
        assert tier2['tolerance_pct'] < tier3['tolerance_pct']
        assert tier3['tolerance_pct'] < tier4['tolerance_pct']
        
        # Baseline scores should decrease progressively
        assert tier1['baseline_score'] > tier2['baseline_score']
        assert tier2['baseline_score'] > tier3['baseline_score']
        assert tier3['baseline_score'] > tier4['baseline_score']
    
    def test_fallback_unknown_tier(self):
        """Unknown tier should default to Tier 4 tolerance (most conservative)"""
        from src.core.market_config import get_infrastructure_tolerance
        
        tolerance = get_infrastructure_tolerance('unknown_tier_xyz')
        
        # Should default to tier_4_frontier (most conservative)
        assert tolerance['tolerance_pct'] == 0.30
        assert tolerance['baseline_score'] == 30


if __name__ == "__main__":
    # Run Phase 2B.1 tests only (implemented)
    pytest.main([__file__, "-v", "-k", "TestPhase2B1"])

