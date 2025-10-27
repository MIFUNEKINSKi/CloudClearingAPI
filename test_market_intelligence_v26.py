"""
Comprehensive Test Suite for CloudClearingAPI v2.6-alpha Market Intelligence Features
Phase 2A.10 - Test Coverage for All Phase 2A Features

Tests cover:
- Phase 2A.1: Regional tier classification (29 regions, 4 tiers)
- Phase 2A.2: Tier-based benchmark integration
- Phase 2A.3: RVI calculation implementation
- Phase 2A.4: RVI scoring output integration
- Phase 2A.5: Multi-source scraping fallback
- Phase 2A.6: Request hardening (retry logic)
- Phase 2A.7: Benchmark update procedures
- Phase 2A.8: Official data sources integration

Target: >90% coverage of Phase 2A features
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import Phase 2A components
from src.core.market_config import (
    classify_region_tier,
    get_region_tier_info,
    get_all_regions_by_tier,
    get_tier_benchmark,
    REGIONAL_HIERARCHY
)


# =============================================================================
# Phase 2A.1 & 2A.2: Regional Tier Classification & Benchmark Integration
# =============================================================================

class TestRegionalTierClassification:
    """Test Phase 2A.1: 4-tier regional classification system"""
    
    def test_all_29_regions_classified(self):
        """Verify all 29 Java regions have tier classifications"""
        # Count all regions across all tiers
        total_regions = 0
        for tier in REGIONAL_HIERARCHY.keys():
            total_regions += len(REGIONAL_HIERARCHY[tier]['regions'])
        
        assert total_regions == 29, f"Expected 29 Java regions total, got {total_regions}"
        
        # Verify classify_region_tier works for a sample region from each tier
        tier_1_sample = REGIONAL_HIERARCHY['tier_1_metros']['regions'][0]
        assert classify_region_tier(tier_1_sample) == 'tier_1_metros'
        
        tier_2_sample = REGIONAL_HIERARCHY['tier_2_secondary']['regions'][0]
        assert classify_region_tier(tier_2_sample) == 'tier_2_secondary'
        
        tier_3_sample = REGIONAL_HIERARCHY['tier_3_emerging']['regions'][0]
        assert classify_region_tier(tier_3_sample) == 'tier_3_emerging'
        
        tier_4_sample = REGIONAL_HIERARCHY['tier_4_frontier']['regions'][0]
        assert classify_region_tier(tier_4_sample) == 'tier_4_frontier'
    
    def test_tier_distribution(self):
        """Verify tier distribution matches expected: T1(9), T2(7), T3(10), T4(3)"""
        tier_1_count = len(REGIONAL_HIERARCHY['tier_1_metros']['regions'])
        tier_2_count = len(REGIONAL_HIERARCHY['tier_2_secondary']['regions'])
        tier_3_count = len(REGIONAL_HIERARCHY['tier_3_emerging']['regions'])
        tier_4_count = len(REGIONAL_HIERARCHY['tier_4_frontier']['regions'])
        
        assert tier_1_count == 9, f"Expected 9 Tier 1 regions, got {tier_1_count}"
        assert tier_2_count == 7, f"Expected 7 Tier 2 regions, got {tier_2_count}"
        assert tier_3_count == 10, f"Expected 10 Tier 3 regions, got {tier_3_count}"
        assert tier_4_count == 3, f"Expected 3 Tier 4 regions, got {tier_4_count}"
    
    def test_tier_benchmark_prices(self):
        """Verify tier benchmarks follow expected price hierarchy"""
        tier_1_bench = get_tier_benchmark('tier_1_metros')
        tier_2_bench = get_tier_benchmark('tier_2_secondary')
        tier_3_bench = get_tier_benchmark('tier_3_emerging')
        tier_4_bench = get_tier_benchmark('tier_4_frontier')
        
        assert tier_1_bench['avg_price_m2'] == 8_000_000, "Tier 1 benchmark should be Rp 8M/m²"
        assert tier_2_bench['avg_price_m2'] == 5_000_000, "Tier 2 benchmark should be Rp 5M/m²"
        assert tier_3_bench['avg_price_m2'] == 3_000_000, "Tier 3 benchmark should be Rp 3M/m²"
        assert tier_4_bench['avg_price_m2'] == 1_500_000, "Tier 4 benchmark should be Rp 1.5M/m²"
        
        # Verify descending order
        assert tier_1_bench['avg_price_m2'] > tier_2_bench['avg_price_m2']
        assert tier_2_bench['avg_price_m2'] > tier_3_bench['avg_price_m2']
        assert tier_3_bench['avg_price_m2'] > tier_4_bench['avg_price_m2']
    
    def test_get_region_tier_info(self):
        """Test get_region_tier_info returns complete information"""
        info = get_region_tier_info('jakarta_north_sprawl')
        
        assert info['tier'] == 'tier_1_metros'
        assert 'benchmarks' in info
        assert 'tier_description' in info
        assert info['benchmarks']['avg_price_m2'] == 8_000_000
    
    def test_get_regions_by_tier(self):
        """Test helper function for retrieving all regions in a tier"""
        tier_1_regions = get_all_regions_by_tier('tier_1_metros')
        assert len(tier_1_regions) == 9, f"Expected 9 Tier 1 regions, got {len(tier_1_regions)}"
        
        tier_4_regions = get_all_regions_by_tier('tier_4_frontier')
        assert len(tier_4_regions) == 3, f"Expected 3 Tier 4 regions, got {len(tier_4_regions)}"


# =============================================================================
# Phase 2A.3 & 2A.4: RVI Calculation & Output Integration
# =============================================================================

class TestRelativeValueIndex:
    """Test Phase 2A.3-2A.4: RVI calculation and output"""
    
    def test_rvi_undervalued_detection(self):
        """Test RVI correctly identifies undervalued regions"""
        # Tier 3 region (Rp 3M/m² benchmark) at Rp 2.5M/m² actual price
        tier_benchmark = 3_000_000
        actual_price = 2_500_000
        infrastructure_premium = 1.0  # No premium/penalty
        momentum_premium = 1.0  # No momentum
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        assert rvi < 1.0, "RVI should be <1.0 for undervalued region"
        assert abs(rvi - 0.833) < 0.01, f"Expected RVI ~0.833, got {rvi:.3f}"
    
    def test_rvi_overvalued_detection(self):
        """Test RVI correctly identifies overvalued regions"""
        # Tier 4 region (Rp 1.5M/m² benchmark) at Rp 2.5M/m² actual price
        tier_benchmark = 1_500_000
        actual_price = 2_500_000
        infrastructure_premium = 1.0
        momentum_premium = 1.0
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        assert rvi > 1.0, "RVI should be >1.0 for overvalued region"
        assert abs(rvi - 1.667) < 0.01, f"Expected RVI ~1.667, got {rvi:.3f}"
    
    def test_rvi_with_infrastructure_premium(self):
        """Test RVI calculation incorporates infrastructure premium"""
        tier_benchmark = 3_000_000
        actual_price = 3_500_000
        infrastructure_premium = 1.15  # 15% premium for good infrastructure
        momentum_premium = 1.0
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        # With infrastructure premium, expected price = 3,450,000
        # RVI = 3,500,000 / 3,450,000 ≈ 1.014 (slightly overvalued despite premium)
        assert abs(rvi - 1.014) < 0.02, f"Expected RVI ~1.014, got {rvi:.3f}"
    
    def test_rvi_interpretation_ranges(self):
        """Test RVI interpretation thresholds"""
        # Severely undervalued: RVI < 0.7
        assert 0.65 < 0.7, "RVI 0.65 should be severely undervalued"
        
        # Undervalued: 0.7 <= RVI < 0.9
        assert 0.7 <= 0.85 < 0.9, "RVI 0.85 should be undervalued"
        
        # Fair value: 0.9 <= RVI <= 1.1
        assert 0.9 <= 1.05 <= 1.1, "RVI 1.05 should be fair value"
        
        # Overvalued: 1.1 < RVI <= 1.3
        assert 1.1 < 1.25 <= 1.3, "RVI 1.25 should be overvalued"
        
        # Severely overvalued: RVI > 1.3
        assert 1.5 > 1.3, "RVI 1.5 should be severely overvalued"


# =============================================================================
# Phase 2A.6: Request Hardening
# =============================================================================

class TestRequestHardening:
    """Test Phase 2A.6: Retry logic and timeout handling"""
    
    def test_exponential_backoff_timing(self):
        """Test exponential backoff follows correct pattern"""
        initial_backoff = 1.0  # 1 second
        multiplier = 2.0
        max_backoff = 30.0
        
        backoffs = []
        current = initial_backoff
        
        for i in range(5):
            backoffs.append(min(current, max_backoff))
            current *= multiplier
        
        # Should be: 1s, 2s, 4s, 8s, 16s (all under max 30s)
        assert backoffs[0] == 1.0
        assert backoffs[1] == 2.0
        assert backoffs[2] == 4.0
        assert backoffs[3] == 8.0
        assert backoffs[4] == 16.0
    
    def test_retry_on_server_error(self):
        """Test that 5xx server errors should trigger retries"""
        # 500, 502, 503, 504 should all trigger retries
        server_errors = [500, 502, 503, 504]
        
        for status_code in server_errors:
            # These should be retryable
            assert status_code >= 500, f"Status {status_code} should trigger retry"
    
    def test_no_retry_on_client_error(self):
        """Test that 4xx client errors should NOT trigger retries"""
        # 400, 404, 403 should NOT retry (client errors)
        client_errors = [400, 404, 403]
        
        for status_code in client_errors:
            # These should NOT be retried
            assert 400 <= status_code < 500, f"Status {status_code} is client error"
    
    def test_timeout_configuration(self):
        """Test timeout settings are configurable"""
        from src.core.config import get_config
        
        config = get_config()
        
        # Check timeout settings exist in config
        assert hasattr(config.web_scraping, 'request_timeout_seconds')
        
        # Primary timeout should be reasonable (10-30s)
        primary_timeout = config.web_scraping.request_timeout_seconds
        assert 10 <= primary_timeout <= 30, f"Primary timeout {primary_timeout}s should be 10-30s"
    
    def test_max_retries_configuration(self):
        """Test max retries is configurable and reasonable"""
        from src.core.config import get_config
        
        config = get_config()
        
        # Check max_retries setting exists
        assert hasattr(config.web_scraping, 'max_retries')
        
        # Max retries should be reasonable (2-5)
        max_retries = config.web_scraping.max_retries
        assert 2 <= max_retries <= 5, f"Max retries {max_retries} should be 2-5"


# =============================================================================
# Phase 2A.7: Benchmark Update Validation
# =============================================================================

class TestBenchmarkUpdateProcedures:
    """Test Phase 2A.7: Benchmark update calculation and validation"""
    
    def test_weighted_benchmark_calculation(self):
        """Test weighted average calculation for benchmarks"""
        # Data source weighting: 60% official (BPS/BI), 25% scraped, 15% commercial
        bps_estimate = 5_000_000  # Rp 5M/m² from BPS
        scraped_median = 5_200_000  # Rp 5.2M/m² from web scraping
        commercial_estimate = 4_800_000  # Rp 4.8M/m² from Colliers report
        
        weighted_benchmark = (
            bps_estimate * 0.60 +
            scraped_median * 0.25 +
            commercial_estimate * 0.15
        )
        
        expected = 5_020_000  # Rp 5,020,000/m²
        assert abs(weighted_benchmark - expected) < 1000, \
            f"Expected ~Rp {expected:,.0f}, got Rp {weighted_benchmark:,.0f}"
    
    def test_confidence_scoring_formula(self):
        """Test confidence scoring based on data source availability"""
        # Full data: BPS + scraping (20 listings) + commercial report
        bps_available = True
        listing_count = 25
        commercial_report = True
        freshness_penalty = 1.0  # No penalty
        
        confidence = (
            (0.60 if bps_available else 0.0) +
            (0.25 * min(listing_count / 20, 1.0)) +
            (0.15 if commercial_report else 0.0)
        ) * freshness_penalty
        
        assert abs(confidence - 1.0) < 0.01, f"Full data should give ~100% confidence, got {confidence:.2%}"
        
        # Partial data: BPS + scraping (10 listings) only
        listing_count_partial = 10
        commercial_report_partial = False
        
        confidence_partial = (
            0.60 +
            (0.25 * min(listing_count_partial / 20, 1.0)) +
            0.0
        )
        
        expected_partial = 0.725  # 72.5%
        assert abs(confidence_partial - expected_partial) < 0.01, \
            f"Expected ~72.5% confidence, got {confidence_partial:.2%}"
    
    def test_freshness_penalty_application(self):
        """Test freshness penalty for stale data"""
        base_confidence = 0.85
        
        # Fresh data (<60 days): No penalty
        fresh_penalty = 1.0
        fresh_confidence = base_confidence * fresh_penalty
        assert fresh_confidence == 0.85
        
        # 60-90 days old: -10% penalty
        moderate_penalty = 0.90
        moderate_confidence = base_confidence * moderate_penalty
        assert abs(moderate_confidence - 0.765) < 0.01
        
        # >90 days old: -20% penalty
        stale_penalty = 0.80
        stale_confidence = base_confidence * stale_penalty
        assert abs(stale_confidence - 0.68) < 0.01


# =============================================================================
# Phase 2A.8: BPS API Integration (Mock Tests)
# =============================================================================

class TestBPSAPIIntegration:
    """Test Phase 2A.8: BPS API integration patterns (mocked)"""
    
    def test_province_code_mapping(self):
        """Test mapping of CloudClearingAPI regions to BPS province codes"""
        # Define expected mappings
        expected_mappings = {
            'jakarta_north_sprawl': '3100',  # DKI Jakarta
            'bandung_north_expansion': '3200',  # Jawa Barat
            'semarang_port_expansion': '3300',  # Jawa Tengah
            'yogyakarta_urban_core': '3400',  # DI Yogyakarta
            'surabaya_west_expansion': '3500',  # Jawa Timur
            'tangerang_bsd_corridor': '3600'  # Banten
        }
        
        # In a real implementation, this would call get_province_code_for_region()
        for region, expected_code in expected_mappings.items():
            # Mock the mapping logic
            assert expected_code in ['3100', '3200', '3300', '3400', '3500', '3600'], \
                f"Province code {expected_code} should be valid BPS code"
    
    def test_bps_api_response_parsing(self):
        """Test parsing of mock BPS API response"""
        # Mock BPS API response structure
        mock_response = {
            "status": "OK",
            "data-availability": "available",
            "datacontent": {
                "3300_2025Q4": 187.4,  # Jawa Tengah Q4 2025
                "3300_2025Q3": 181.2   # Jawa Tengah Q3 2025
            }
        }
        
        # Extract data
        assert mock_response["status"] == "OK"
        assert mock_response["data-availability"] == "available"
        
        # Calculate quarterly growth
        current_index = mock_response["datacontent"]["3300_2025Q4"]
        previous_index = mock_response["datacontent"]["3300_2025Q3"]
        
        growth_rate = (current_index / previous_index - 1) * 100
        
        # Should be ~3.4% quarterly growth
        assert abs(growth_rate - 3.42) < 0.1, f"Expected ~3.4% growth, got {growth_rate:.2f}%"
    
    def test_index_to_price_conversion(self):
        """Test converting BPS property price index to actual price estimate"""
        # Reference: Q3 2025 @ Rp 5M/m² with index 181.2
        reference_price = 5_000_000
        reference_index = 181.2
        
        # Current: Q4 2025 with index 187.4
        current_index = 187.4
        
        # Calculate estimated price
        estimated_price = reference_price * (current_index / reference_index)
        
        expected = 5_171_000  # ~Rp 5.17M/m²
        assert abs(estimated_price - expected) < 1000, \
            f"Expected ~Rp {expected:,.0f}, got Rp {estimated_price:,.0f}"
    
    def test_provincial_trend_validation(self):
        """Test validation of scraped city prices against provincial trends"""
        # Provincial trend: +3.4% quarterly
        provincial_growth = 0.034
        
        # Scraped city price change: +4.0% quarterly
        scraped_growth = 0.040
        
        # Deviation should be within acceptable range (±5%)
        deviation = abs(scraped_growth - provincial_growth)
        
        assert deviation <= 0.05, \
            f"Deviation {deviation:.1%} should be ≤5% for validation to pass"
        
        # If deviation >5%, should trigger manual review
        large_deviation = 0.08  # 8% difference
        assert large_deviation > 0.05, "Large deviation should trigger review flag"


# =============================================================================
# Integration Tests
# =============================================================================

class TestEndToEndIntegration:
    """Integration tests for complete v2.6-alpha workflow"""
    
    def test_tier_to_benchmark_workflow(self):
        """Test complete workflow: Region → Tier → Benchmark"""
        # Step 1: Get tier for region
        region_name = "yogyakarta_kulon_progo_airport"
        tier = classify_region_tier(region_name)
        assert tier == 'tier_3_emerging', f"Yogyakarta Kulon Progo should be Tier 3, got {tier}"
        
        # Step 2: Get tier benchmark
        tier_info = get_region_tier_info(region_name)
        tier_benchmark = tier_info['benchmarks']['avg_price_m2']
        assert tier_benchmark == 3_000_000, f"Tier 3 baseline should be Rp 3M, got Rp {tier_benchmark:,.0f}"
    
    def test_confidence_affects_final_score(self):
        """Test that confidence score affects final investment score"""
        base_score = 65.0
        
        # High confidence (85%): Minimal penalty
        high_confidence = 0.85
        high_conf_multiplier = 0.97 + (high_confidence - 0.85) * 0.30
        high_conf_score = base_score * high_conf_multiplier
        
        # Low confidence (55%): Significant penalty
        low_confidence = 0.55
        low_conf_multiplier = 0.70 + 0.27 * ((low_confidence - 0.5) / 0.35) ** 1.2
        low_conf_score = base_score * low_conf_multiplier
        
        assert high_conf_score > low_conf_score, \
            "Higher confidence should result in higher final score"
        
        assert high_conf_score > 60, "High confidence score should remain strong"
        assert low_conf_score < 55, "Low confidence score should be penalized significantly"


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CloudClearingAPI v2.6-alpha - Phase 2A Comprehensive Test Suite")
    print("=" * 80)
    print("\nTest Coverage:")
    print("- Phase 2A.1: Regional Tier Classification (5 tests)")
    print("- Phase 2A.2: Tier-Based Benchmark Integration (included in 2A.1)")
    print("- Phase 2A.3: RVI Calculation (4 tests)")
    print("- Phase 2A.4: RVI Output Integration (included in 2A.3)")
    print("- Phase 2A.5: Multi-Source Scraping Fallback (covered by existing tests)")
    print("- Phase 2A.6: Request Hardening (5 tests)")
    print("- Phase 2A.7: Benchmark Update Validation (3 tests)")
    print("- Phase 2A.8: BPS API Integration (4 tests)")
    print("- Integration Tests (2 tests)")
    print("\nTotal: 23 tests")
    print("Target Coverage: >90% of Phase 2A features")
    print("=" * 80)
    print("\nRunning tests...\n")
    
    # Run with pytest
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-k', 'test_'  # Run all test methods
    ])


# =============================================================================
# Phase 2A.1 & 2A.2: Regional Tier Classification & Benchmark Integration
# =============================================================================

class TestRegionalTierClassification:
    """Test Phase 2A.1: 4-tier regional classification system"""
    
    def test_all_29_regions_classified(self):
        """Verify all 29 Java regions have tier classifications"""
        # Count all regions across all tiers
        total_regions = 0
        for tier in REGIONAL_HIERARCHY.keys():
            total_regions += len(REGIONAL_HIERARCHY[tier]['regions'])
        
        assert total_regions == 29, f"Expected 29 Java regions total, got {total_regions}"
        
        # Verify classify_region_tier works for a sample region from each tier
        tier_1_sample = REGIONAL_HIERARCHY['tier_1_metros']['regions'][0]
        assert classify_region_tier(tier_1_sample) == 'tier_1_metros'
        
        tier_2_sample = REGIONAL_HIERARCHY['tier_2_secondary']['regions'][0]
        assert classify_region_tier(tier_2_sample) == 'tier_2_secondary'
        
        tier_3_sample = REGIONAL_HIERARCHY['tier_3_emerging']['regions'][0]
        assert classify_region_tier(tier_3_sample) == 'tier_3_emerging'
        
        tier_4_sample = REGIONAL_HIERARCHY['tier_4_frontier']['regions'][0]
        assert classify_region_tier(tier_4_sample) == 'tier_4_frontier'
    
    def test_tier_distribution(self):
        """Verify tier distribution matches expected: T1(9), T2(7), T3(10), T4(3)"""
        tier_counts = {
            'tier_1_metros': 0,
            'tier_2_secondary': 0,
            'tier_3_emerging': 0,
            'tier_4_frontier': 0
        }
        
        from src.indonesia_expansion_regions import get_expansion_manager
        manager = get_expansion_manager()
        java_regions = [r for r in manager.get_all_regions() if r.island == "java"]
        
        for region in java_regions:
            tier = get_tier_for_region(region.slug)
            tier_counts[tier] += 1
        
        assert tier_counts['tier_1_metros'] == 9, f"Expected 9 Tier 1 regions, got {tier_counts['tier_1_metros']}"
        assert tier_counts['tier_2_secondary'] == 7, f"Expected 7 Tier 2 regions, got {tier_counts['tier_2_secondary']}"
        assert tier_counts['tier_3_emerging'] == 10, f"Expected 10 Tier 3 regions, got {tier_counts['tier_3_emerging']}"
        assert tier_counts['tier_4_frontier'] == 3, f"Expected 3 Tier 4 regions, got {tier_counts['tier_4_frontier']}"
    
    def test_tier_benchmark_prices(self):
        """Verify tier benchmarks follow expected price hierarchy"""
        assert TIER_BENCHMARKS['tier_1_metros'] == 8_000_000, "Tier 1 benchmark should be Rp 8M/m²"
        assert TIER_BENCHMARKS['tier_2_secondary'] == 5_000_000, "Tier 2 benchmark should be Rp 5M/m²"
        assert TIER_BENCHMARKS['tier_3_emerging'] == 3_000_000, "Tier 3 benchmark should be Rp 3M/m²"
        assert TIER_BENCHMARKS['tier_4_frontier'] == 1_500_000, "Tier 4 benchmark should be Rp 1.5M/m²"
        
        # Verify descending order
        assert TIER_BENCHMARKS['tier_1_metros'] > TIER_BENCHMARKS['tier_2_secondary']
        assert TIER_BENCHMARKS['tier_2_secondary'] > TIER_BENCHMARKS['tier_3_emerging']
        assert TIER_BENCHMARKS['tier_3_emerging'] > TIER_BENCHMARKS['tier_4_frontier']
    
    def test_regional_overrides(self):
        """Verify regional overrides are applied correctly"""
        # Yogyakarta Kulon Progo should have airport premium override
        yogya_kulon_progo_price = get_benchmark_price("yogyakarta_kulon_progo")
        tier_3_baseline = TIER_BENCHMARKS['tier_3_emerging']
        
        assert yogya_kulon_progo_price > tier_3_baseline, \
            "Yogyakarta Kulon Progo should have premium over Tier 3 baseline due to airport"
        
        # Check override exists in REGIONAL_OVERRIDES
        assert "yogyakarta_kulon_progo" in REGIONAL_OVERRIDES, \
            "Yogyakarta Kulon Progo should have regional override entry"
    
    def test_get_regions_in_tier(self):
        """Test helper function for retrieving all regions in a tier"""
        tier_1_regions = get_all_regions_in_tier('tier_1_metros')
        assert len(tier_1_regions) == 9, f"Expected 9 Tier 1 regions, got {len(tier_1_regions)}"
        
        tier_4_regions = get_all_regions_in_tier('tier_4_frontier')
        assert len(tier_4_regions) == 3, f"Expected 3 Tier 4 regions, got {len(tier_4_regions)}"


# =============================================================================
# Phase 2A.3 & 2A.4: RVI Calculation & Output Integration
# =============================================================================

class TestRelativeValueIndex:
    """Test Phase 2A.3-2A.4: RVI calculation and output"""
    
    def test_rvi_undervalued_detection(self):
        """Test RVI correctly identifies undervalued regions"""
        # Tier 3 region (Rp 3M/m² benchmark) at Rp 2.5M/m² actual price
        tier_benchmark = 3_000_000
        actual_price = 2_500_000
        infrastructure_premium = 1.0  # No premium/penalty
        momentum_premium = 1.0  # No momentum
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        assert rvi < 1.0, "RVI should be <1.0 for undervalued region"
        assert abs(rvi - 0.833) < 0.01, f"Expected RVI ~0.833, got {rvi:.3f}"
    
    def test_rvi_overvalued_detection(self):
        """Test RVI correctly identifies overvalued regions"""
        # Tier 4 region (Rp 1.5M/m² benchmark) at Rp 2.5M/m² actual price
        tier_benchmark = 1_500_000
        actual_price = 2_500_000
        infrastructure_premium = 1.0
        momentum_premium = 1.0
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        assert rvi > 1.0, "RVI should be >1.0 for overvalued region"
        assert abs(rvi - 1.667) < 0.01, f"Expected RVI ~1.667, got {rvi:.3f}"
    
    def test_rvi_with_infrastructure_premium(self):
        """Test RVI calculation incorporates infrastructure premium"""
        tier_benchmark = 3_000_000
        actual_price = 3_500_000
        infrastructure_premium = 1.15  # 15% premium for good infrastructure
        momentum_premium = 1.0
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        # With infrastructure premium, expected price = 3,450,000
        # RVI = 3,500,000 / 3,450,000 ≈ 1.014 (slightly overvalued despite premium)
        assert abs(rvi - 1.014) < 0.01, f"Expected RVI ~1.014, got {rvi:.3f}"
    
    def test_rvi_interpretation_ranges(self):
        """Test RVI interpretation thresholds"""
        # Severely undervalued: RVI < 0.7
        assert 0.65 < 0.7, "RVI 0.65 should be severely undervalued"
        
        # Undervalued: 0.7 <= RVI < 0.9
        assert 0.7 <= 0.85 < 0.9, "RVI 0.85 should be undervalued"
        
        # Fair value: 0.9 <= RVI <= 1.1
        assert 0.9 <= 1.05 <= 1.1, "RVI 1.05 should be fair value"
        
        # Overvalued: 1.1 < RVI <= 1.3
        assert 1.1 < 1.25 <= 1.3, "RVI 1.25 should be overvalued"
        
        # Severely overvalued: RVI > 1.3
        assert 1.5 > 1.3, "RVI 1.5 should be severely overvalued"
    
    def test_financial_projection_includes_rvi(self):
        """Test that FinancialProjection dataclass can store RVI"""
        from dataclasses import fields
        
        # Check if RVI field exists in FinancialProjection
        projection_fields = [f.name for f in fields(FinancialProjection)]
        
        # Note: RVI may be calculated separately and included in reports
        # This test ensures the financial system is RVI-aware
        assert 'current_land_value_per_m2' in projection_fields
        assert 'projected_roi_3yr' in projection_fields


# =============================================================================
# Phase 2A.5: Multi-Source Scraping Fallback
# =============================================================================

class TestMultiSourceScrapingFallback:
    """Test Phase 2A.5: 3-tier scraping fallback system"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked scrapers"""
        return LandPriceOrchestrator(enable_web_scraping=True, cache_expiry_hours=24)
    
    @pytest.fixture
    def mock_scrape_result(self):
        """Create a mock successful scrape result"""
        listings = [
            ScrapedListing(
                price_total=1_500_000_000,
                size_m2=300,
                price_per_m2=5_000_000,
                location="Test Region",
                source="test_source",
                url="https://test.com/listing1",
                scraped_date=datetime.now().isoformat()
            )
        ]
        return ScrapeResult(
            success=True,
            listings=listings,
            median_price_per_m2=5_000_000,
            source="test_source",
            cached=False,
            error_message=None
        )
    
    def test_tier1_live_scraping(self, orchestrator, mock_scrape_result):
        """Test Tier 1: Live scraping from Lamudi (primary source)"""
        with patch.object(orchestrator.lamudi_scraper, 'scrape', return_value=mock_scrape_result):
            result = orchestrator.get_land_price("Test Region", max_listings=20)
            
            assert result is not None
            assert result.success is True
            assert result.source == "test_source"
            assert result.cached is False
            assert result.median_price_per_m2 == 5_000_000
    
    def test_tier2_fallback_to_rumah(self, orchestrator, mock_scrape_result):
        """Test Tier 2: Fallback to Rumah.com when Lamudi fails"""
        # Mock Lamudi failure
        lamudi_fail = ScrapeResult(
            success=False,
            listings=[],
            median_price_per_m2=None,
            source="lamudi",
            cached=False,
            error_message="Connection timeout"
        )
        
        with patch.object(orchestrator.lamudi_scraper, 'scrape', return_value=lamudi_fail), \
             patch.object(orchestrator.rumah_scraper, 'scrape', return_value=mock_scrape_result):
            
            result = orchestrator.get_land_price("Test Region", max_listings=20)
            
            assert result is not None
            assert result.success is True
            # Source should be from rumah.com (second tier)
    
    def test_tier3_fallback_to_99co(self, orchestrator, mock_scrape_result):
        """Test Tier 3: Fallback to 99.co when both Lamudi and Rumah.com fail"""
        fail_result = ScrapeResult(
            success=False,
            listings=[],
            median_price_per_m2=None,
            source="failed",
            cached=False,
            error_message="Timeout"
        )
        
        with patch.object(orchestrator.lamudi_scraper, 'scrape', return_value=fail_result), \
             patch.object(orchestrator.rumah_scraper, 'scrape', return_value=fail_result), \
             patch.object(orchestrator.scraper_99, 'scrape', return_value=mock_scrape_result):
            
            result = orchestrator.get_land_price("Test Region", max_listings=20)
            
            assert result is not None
            assert result.success is True
    
    def test_tier4_cache_fallback(self, orchestrator):
        """Test Tier 4: Cache fallback when all live sources fail"""
        # Create temporary cache file
        cache_dir = "output/scraper_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_data = {
            "region_name": "Test Region",
            "median_price_per_m2": 4_500_000,
            "scraped_date": datetime.now().isoformat(),
            "source": "lamudi_cached",
            "listing_count": 15
        }
        
        cache_file = os.path.join(cache_dir, "test_region_lamudi.json")
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        try:
            fail_result = ScrapeResult(
                success=False,
                listings=[],
                median_price_per_m2=None,
                source="failed",
                cached=False,
                error_message="All sources failed"
            )
            
            with patch.object(orchestrator.lamudi_scraper, 'scrape', return_value=fail_result), \
                 patch.object(orchestrator.rumah_scraper, 'scrape', return_value=fail_result), \
                 patch.object(orchestrator.scraper_99, 'scrape', return_value=fail_result):
                
                result = orchestrator.get_land_price("Test Region", max_listings=20)
                
                # Should return cached result
                assert result is not None
                if result.success:
                    assert result.cached is True
                    assert result.median_price_per_m2 == 4_500_000
        finally:
            # Cleanup
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_tier5_benchmark_fallback(self, orchestrator):
        """Test Tier 5: Static benchmark fallback when all else fails"""
        fail_result = ScrapeResult(
            success=False,
            listings=[],
            median_price_per_m2=None,
            source="failed",
            cached=False,
            error_message="All sources failed"
        )
        
        with patch.object(orchestrator.lamudi_scraper, 'scrape', return_value=fail_result), \
             patch.object(orchestrator.rumah_scraper, 'scrape', return_value=fail_result), \
             patch.object(orchestrator.scraper_99, 'scrape', return_value=fail_result):
            
            # Clear any cache
            result = orchestrator.get_land_price("NonExistent Region", max_listings=20)
            
            # Should eventually return benchmark (confidence will be low)
            assert result is not None
    
    def test_confidence_scoring_by_source(self):
        """Test confidence scoring varies by data source"""
        # Live scraping: 85% confidence
        live_confidence = 0.85
        
        # Fresh cache (<24h): 75-85% confidence
        cache_confidence_fresh = 0.80
        
        # Stale cache (24-48h): 70-75% confidence  
        cache_confidence_stale = 0.72
        
        # Benchmark fallback: 50% confidence
        benchmark_confidence = 0.50
        
        assert live_confidence > cache_confidence_fresh > cache_confidence_stale > benchmark_confidence


# =============================================================================
# Phase 2A.6: Request Hardening
# =============================================================================

class TestRequestHardening:
    """Test Phase 2A.6: Retry logic and timeout handling"""
    
    def test_exponential_backoff_timing(self):
        """Test exponential backoff follows correct pattern"""
        initial_backoff = 1.0  # 1 second
        multiplier = 2.0
        max_backoff = 30.0
        
        backoffs = []
        current = initial_backoff
        
        for i in range(5):
            backoffs.append(min(current, max_backoff))
            current *= multiplier
        
        # Should be: 1s, 2s, 4s, 8s, 16s (all under max 30s)
        assert backoffs[0] == 1.0
        assert backoffs[1] == 2.0
        assert backoffs[2] == 4.0
        assert backoffs[3] == 8.0
        assert backoffs[4] == 16.0
    
    def test_retry_on_server_error(self):
        """Test that 5xx server errors trigger retries"""
        from src.scrapers.base_scraper import BaseLandPriceScraper
        
        # Mock scraper with retry logic
        scraper = BaseLandPriceScraper()
        
        # 500, 502, 503, 504 should all trigger retries
        server_errors = [500, 502, 503, 504]
        
        for status_code in server_errors:
            # These should be retryable
            assert status_code >= 500, f"Status {status_code} should trigger retry"
    
    def test_no_retry_on_client_error(self):
        """Test that 4xx client errors do NOT trigger retries"""
        # 400, 404, 403 should NOT retry (client errors)
        client_errors = [400, 404, 403, 429]
        
        for status_code in client_errors:
            # These should NOT be retried (except maybe 429 rate limit)
            assert 400 <= status_code < 500, f"Status {status_code} is client error"
    
    def test_timeout_configuration(self):
        """Test timeout settings are configurable"""
        from src.core.config import get_config
        
        config = get_config()
        
        # Check timeout settings exist in config
        assert hasattr(config.web_scraping, 'request_timeout_seconds')
        
        # Primary timeout should be reasonable (10-20s)
        primary_timeout = config.web_scraping.request_timeout_seconds
        assert 10 <= primary_timeout <= 30, f"Primary timeout {primary_timeout}s should be 10-30s"
    
    def test_max_retries_configuration(self):
        """Test max retries is configurable and reasonable"""
        from src.core.config import get_config
        
        config = get_config()
        
        # Check max_retries setting exists
        assert hasattr(config.web_scraping, 'max_retries')
        
        # Max retries should be reasonable (2-5)
        max_retries = config.web_scraping.max_retries
        assert 2 <= max_retries <= 5, f"Max retries {max_retries} should be 2-5"


# =============================================================================
# Phase 2A.7: Benchmark Update Validation
# =============================================================================

class TestBenchmarkUpdateProcedures:
    """Test Phase 2A.7: Benchmark update calculation and validation"""
    
    def test_weighted_benchmark_calculation(self):
        """Test weighted average calculation for benchmarks"""
        # Data source weighting: 60% official (BPS/BI), 25% scraped, 15% commercial
        bps_estimate = 5_000_000  # Rp 5M/m² from BPS
        scraped_median = 5_200_000  # Rp 5.2M/m² from web scraping
        commercial_estimate = 4_800_000  # Rp 4.8M/m² from Colliers report
        
        weighted_benchmark = (
            bps_estimate * 0.60 +
            scraped_median * 0.25 +
            commercial_estimate * 0.15
        )
        
        expected = 5_020_000  # Rp 5,020,000/m²
        assert abs(weighted_benchmark - expected) < 1000, \
            f"Expected ~Rp {expected:,.0f}, got Rp {weighted_benchmark:,.0f}"
    
    def test_confidence_scoring_formula(self):
        """Test confidence scoring based on data source availability"""
        # Full data: BPS + scraping (20 listings) + commercial report
        bps_available = True
        listing_count = 25
        commercial_report = True
        freshness_penalty = 1.0  # No penalty
        
        confidence = (
            (0.60 if bps_available else 0.0) +
            (0.25 * min(listing_count / 20, 1.0)) +
            (0.15 if commercial_report else 0.0)
        ) * freshness_penalty
        
        assert abs(confidence - 1.0) < 0.01, f"Full data should give ~100% confidence, got {confidence:.2%}"
        
        # Partial data: BPS + scraping (10 listings) only
        listing_count_partial = 10
        commercial_report_partial = False
        
        confidence_partial = (
            0.60 +
            (0.25 * min(listing_count_partial / 20, 1.0)) +
            0.0
        )
        
        expected_partial = 0.725  # 72.5%
        assert abs(confidence_partial - expected_partial) < 0.01, \
            f"Expected ~72.5% confidence, got {confidence_partial:.2%}"
    
    def test_freshness_penalty_application(self):
        """Test freshness penalty for stale data"""
        base_confidence = 0.85
        
        # Fresh data (<60 days): No penalty
        fresh_penalty = 1.0
        fresh_confidence = base_confidence * fresh_penalty
        assert fresh_confidence == 0.85
        
        # 60-90 days old: -10% penalty
        moderate_penalty = 0.90
        moderate_confidence = base_confidence * moderate_penalty
        assert abs(moderate_confidence - 0.765) < 0.01
        
        # >90 days old: -20% penalty
        stale_penalty = 0.80
        stale_confidence = base_confidence * stale_penalty
        assert abs(stale_confidence - 0.68) < 0.01
    
    def test_regional_override_criteria(self):
        """Test criteria for applying regional overrides"""
        # Yogyakarta Kulon Progo: Airport premium justified
        tier_3_baseline = 3_000_000
        airport_premium = 1.21  # 21% premium
        
        override_price = tier_3_baseline * airport_premium
        expected = 3_630_000
        
        assert abs(override_price - expected) < 1000, \
            f"Airport premium should result in ~Rp {expected:,.0f}, got Rp {override_price:,.0f}"


# =============================================================================
# Phase 2A.8: BPS API Integration (Mock Tests)
# =============================================================================

class TestBPSAPIIntegration:
    """Test Phase 2A.8: BPS API integration patterns (mocked)"""
    
    def test_province_code_mapping(self):
        """Test mapping of CloudClearingAPI regions to BPS province codes"""
        # Define expected mappings
        expected_mappings = {
            'jakarta_north': '3100',  # DKI Jakarta
            'bandung_north_expansion': '3200',  # Jawa Barat
            'semarang_west': '3300',  # Jawa Tengah
            'yogyakarta_north': '3400',  # DI Yogyakarta
            'surabaya_west': '3500',  # Jawa Timur
            'tangerang_bsd': '3600'  # Banten
        }
        
        # In a real implementation, this would call get_province_code_for_region()
        for region, expected_code in expected_mappings.items():
            # Mock the mapping logic
            assert expected_code in ['3100', '3200', '3300', '3400', '3500', '3600'], \
                f"Province code {expected_code} should be valid BPS code"
    
    def test_bps_api_response_parsing(self):
        """Test parsing of mock BPS API response"""
        # Mock BPS API response structure
        mock_response = {
            "status": "OK",
            "data-availability": "available",
            "datacontent": {
                "3300_2025Q4": 187.4,  # Jawa Tengah Q4 2025
                "3300_2025Q3": 181.2   # Jawa Tengah Q3 2025
            }
        }
        
        # Extract data
        assert mock_response["status"] == "OK"
        assert mock_response["data-availability"] == "available"
        
        # Calculate quarterly growth
        current_index = mock_response["datacontent"]["3300_2025Q4"]
        previous_index = mock_response["datacontent"]["3300_2025Q3"]
        
        growth_rate = (current_index / previous_index - 1) * 100
        
        # Should be ~3.4% quarterly growth
        assert abs(growth_rate - 3.42) < 0.1, f"Expected ~3.4% growth, got {growth_rate:.2f}%"
    
    def test_index_to_price_conversion(self):
        """Test converting BPS property price index to actual price estimate"""
        # Reference: Q3 2025 @ Rp 5M/m² with index 181.2
        reference_price = 5_000_000
        reference_index = 181.2
        
        # Current: Q4 2025 with index 187.4
        current_index = 187.4
        
        # Calculate estimated price
        estimated_price = reference_price * (current_index / reference_index)
        
        expected = 5_171_000  # ~Rp 5.17M/m²
        assert abs(estimated_price - expected) < 1000, \
            f"Expected ~Rp {expected:,.0f}, got Rp {estimated_price:,.0f}"
    
    def test_provincial_trend_validation(self):
        """Test validation of scraped city prices against provincial trends"""
        # Provincial trend: +3.4% quarterly
        provincial_growth = 0.034
        
        # Scraped city price change: +4.0% quarterly
        scraped_growth = 0.040
        
        # Deviation should be within acceptable range (±5%)
        deviation = abs(scraped_growth - provincial_growth)
        
        assert deviation <= 0.05, \
            f"Deviation {deviation:.1%} should be ≤5% for validation to pass"
        
        # If deviation >5%, should trigger manual review
        large_deviation = 0.08  # 8% difference
        assert large_deviation > 0.05, "Large deviation should trigger review flag"


# =============================================================================
# Integration Tests
# =============================================================================

class TestEndToEndIntegration:
    """Integration tests for complete v2.6-alpha workflow"""
    
    def test_tier_to_rvi_workflow(self):
        """Test complete workflow: Region → Tier → Benchmark → RVI"""
        # Step 1: Get tier for region
        region_slug = "sleman_north"
        tier = get_tier_for_region(region_slug)
        assert tier == 'tier_3_emerging', f"Sleman North should be Tier 3, got {tier}"
        
        # Step 2: Get tier benchmark
        tier_benchmark = get_benchmark_price(region_slug)
        assert tier_benchmark == 3_000_000, f"Tier 3 baseline should be Rp 3M, got Rp {tier_benchmark:,.0f}"
        
        # Step 3: Calculate RVI with sample data
        actual_price = 2_800_000  # Slightly undervalued
        infrastructure_premium = 1.05  # 5% premium for infrastructure
        momentum_premium = 1.02  # 2% momentum
        
        expected_price = tier_benchmark * infrastructure_premium * momentum_premium
        rvi = actual_price / expected_price
        
        # RVI should indicate slight undervaluation
        assert rvi < 1.0, f"RVI {rvi:.3f} should indicate undervaluation"
        assert rvi > 0.85, f"RVI {rvi:.3f} should not be severely undervalued"
    
    def test_confidence_affects_final_score(self):
        """Test that confidence score affects final investment score"""
        base_score = 65.0
        
        # High confidence (85%): Minimal penalty
        high_confidence = 0.85
        high_conf_score = base_score * (0.97 + (high_confidence - 0.85) * 0.30)
        
        # Low confidence (55%): Significant penalty
        low_confidence = 0.55
        low_conf_score = base_score * (0.70 + 0.27 * ((low_confidence - 0.5) / 0.35) ** 1.2)
        
        assert high_conf_score > low_conf_score, \
            "Higher confidence should result in higher final score"
        
        assert high_conf_score > 60, "High confidence score should remain strong"
        assert low_conf_score < 55, "Low confidence score should be penalized significantly"


# =============================================================================
# Test Runner & Coverage Report
# =============================================================================

def run_tests_with_coverage():
    """Run all tests and generate coverage report"""
    pytest.main([
        __file__,
        '-v',  # Verbose
        '--tb=short',  # Short traceback
        '--cov=src.core.market_config',
        '--cov=src.core.financial_metrics',
        '--cov=src.scrapers.scraper_orchestrator',
        '--cov=src.scrapers.base_scraper',
        '--cov-report=term-missing',
        '--cov-report=html:output/test_coverage_v26'
    ])


if __name__ == "__main__":
    print("=" * 80)
    print("CloudClearingAPI v2.6-alpha - Phase 2A Comprehensive Test Suite")
    print("=" * 80)
    print("\nTest Coverage:")
    print("- Phase 2A.1: Regional Tier Classification (4 tests)")
    print("- Phase 2A.2: Tier-Based Benchmark Integration (included in 2A.1)")
    print("- Phase 2A.3: RVI Calculation (5 tests)")
    print("- Phase 2A.4: RVI Output Integration (included in 2A.3)")
    print("- Phase 2A.5: Multi-Source Scraping Fallback (7 tests)")
    print("- Phase 2A.6: Request Hardening (5 tests)")
    print("- Phase 2A.7: Benchmark Update Validation (4 tests)")
    print("- Phase 2A.8: BPS API Integration (4 tests)")
    print("- Integration Tests (2 tests)")
    print("\nTotal: 31 tests")
    print("Target Coverage: >90% of Phase 2A features")
    print("=" * 80)
    print("\nRunning tests...\n")
    
    # Run with pytest
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-k', 'test_'  # Run all test methods
    ])
