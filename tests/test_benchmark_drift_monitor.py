"""
Unit Tests for BenchmarkDriftMonitor (CCAPI-27.2)

Tests cover:
- Drift calculation accuracy (positive/negative drift, edge cases)
- Alert threshold logic (WARNING/CRITICAL/NONE classification)
- Persistence checking (consecutive weeks counting)
- History persistence (append, cleanup, retention)
- Tier aggregation (weighted by confidence, smoothing)
- Edge cases (zero benchmark, no live data, extreme outliers, missing data)
- Helper method extraction (live_price, data_source, confidence)

Target: 95%+ code coverage
"""

import unittest
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.benchmark_drift_monitor import BenchmarkDriftMonitor


class TestBenchmarkDriftMonitorCore(unittest.TestCase):
    """Test core drift calculation and alert logic"""
    
    def setUp(self):
        """Create temporary directory for test history files"""
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir)
    
    def test_drift_calculation_positive(self):
        """Test drift calculation for price increase (positive drift)"""
        result = self.monitor.calculate_drift(
            region_name="jakarta_north_sprawl",  # Use real region
            live_price=11_000_000,  # Rp 11M/m²
            data_source="lamudi",
            confidence=0.85
        )
        
        # Expected drift: (11M - 8M) / 8M * 100 = +37.5% (Tier 1 benchmark = 8M)
        self.assertIsNotNone(result)
        self.assertEqual(result.region_name, "jakarta_north_sprawl")
        self.assertAlmostEqual(result.drift_pct, 37.5, places=1)
        self.assertEqual(result.data_source, "lamudi")
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.alert_level, "CRITICAL")  # >20% drift
    
    def test_drift_calculation_negative(self):
        """Test drift calculation for price decrease (negative drift)"""
        result = self.monitor.calculate_drift(
            region_name="tier_1_region",
            live_price=6_000_000,  # Rp 6M/m² (below 8M benchmark)
            data_source="lamudi",
            confidence=0.90
        )
        
        # Expected drift: (6M - 8M) / 8M * 100 = -25%
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['drift_pct'], -25.0, places=1)
        self.assertEqual(result['alert_level'], "CRITICAL")  # >20% drift
    
    def test_drift_calculation_minimal(self):
        """Test drift calculation for minimal price change (no alert)"""
        result = self.monitor.calculate_drift(
            region_name="stable_region",
            live_price=8_500_000,  # Rp 8.5M/m² (close to 8M benchmark)
            data_source="lamudi",
            confidence=0.80
        )
        
        # Expected drift: (8.5M - 8M) / 8M * 100 = +6.25%
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['drift_pct'], 6.25, places=1)
        self.assertEqual(result['alert_level'], "NONE")  # <10% drift
    
    def test_drift_calculation_tier_2_region(self):
        """Test drift calculation for Tier 2 region (5M benchmark)"""
        result = self.monitor.calculate_drift(
            region_name="semarang_port_expansion",  # Tier 2
            live_price=6_500_000,  # Rp 6.5M/m²
            data_source="lamudi",
            confidence=0.85
        )
        
        # Expected drift: (6.5M - 5M) / 5M * 100 = +30%
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['drift_pct'], 30.0, places=1)
        self.assertEqual(result['tier'], "tier_2_secondary")
        self.assertEqual(result['alert_level'], "CRITICAL")  # >20% drift
    
    def test_drift_calculation_zero_benchmark_fallback(self):
        """Test drift calculation handles zero benchmark gracefully"""
        # Mock a region with no tier classification (should use default)
        result = self.monitor.calculate_drift(
            region_name="unknown_region",
            live_price=5_000_000,
            data_source="lamudi",
            confidence=0.75
        )
        
        # Should still calculate using Tier 3 default (3M)
        self.assertIsNotNone(result)
        self.assertGreater(result['benchmark_price'], 0)
        self.assertIn('drift_pct', result)
    
    def test_no_live_price_returns_none(self):
        """Test that missing live price returns None"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=None,
            data_source="static_benchmark",
            confidence=0.50
        )
        
        self.assertIsNone(result)
    
    def test_extreme_outlier_positive(self):
        """Test extreme positive drift (1000%+ outlier)"""
        result = self.monitor.calculate_drift(
            region_name="outlier_region",
            live_price=100_000_000,  # Rp 100M/m² (absurdly high)
            data_source="lamudi",
            confidence=0.50  # Low confidence on outlier
        )
        
        # Expected drift: (100M - 8M) / 8M * 100 = +1150%
        self.assertIsNotNone(result)
        self.assertGreater(result['drift_pct'], 1000)
        self.assertEqual(result['alert_level'], "CRITICAL")
    
    def test_extreme_outlier_negative(self):
        """Test extreme negative drift (price near zero)"""
        result = self.monitor.calculate_drift(
            region_name="crash_region",
            live_price=100_000,  # Rp 100K/m² (near zero)
            data_source="lamudi",
            confidence=0.40
        )
        
        # Expected drift: (0.1M - 8M) / 8M * 100 ≈ -98.75%
        self.assertIsNotNone(result)
        self.assertLess(result['drift_pct'], -90)
        self.assertEqual(result['alert_level'], "CRITICAL")


class TestAlertThresholds(unittest.TestCase):
    """Test alert threshold logic and persistence checks"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_warning_threshold_exact(self):
        """Test WARNING threshold at exactly 10% drift"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=8_800_000,  # Exactly +10%
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertEqual(result['drift_pct'], 10.0)
        self.assertEqual(result['alert_level'], "WARNING")
    
    def test_critical_threshold_exact(self):
        """Test CRITICAL threshold at exactly 20% drift"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=9_600_000,  # Exactly +20%
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertEqual(result['drift_pct'], 20.0)
        self.assertEqual(result['alert_level'], "CRITICAL")
    
    def test_alert_threshold_boundary_below_warning(self):
        """Test boundary just below WARNING threshold"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=8_799_000,  # Just under +10%
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertLess(result['drift_pct'], 10.0)
        self.assertEqual(result['alert_level'], "NONE")
    
    def test_alert_threshold_boundary_above_warning(self):
        """Test boundary just above WARNING threshold"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=8_801_000,  # Just over +10%
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertGreater(result['drift_pct'], 10.0)
        self.assertEqual(result['alert_level'], "WARNING")
    
    def test_negative_drift_warning(self):
        """Test WARNING for negative drift (-10% to -20%)"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=7_200_000,  # -10% drift
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertEqual(result['drift_pct'], -10.0)
        self.assertEqual(result['alert_level'], "WARNING")
    
    def test_negative_drift_critical(self):
        """Test CRITICAL for negative drift (< -20%)"""
        result = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=6_400_000,  # -20% drift
            data_source="lamudi",
            confidence=0.85
        )
        
        self.assertEqual(result['drift_pct'], -20.0)
        self.assertEqual(result['alert_level'], "CRITICAL")


class TestHistoryPersistence(unittest.TestCase):
    """Test JSON persistence, append operations, and TTL cleanup"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=7,  # Short retention for testing
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_save_drift_snapshot(self):
        """Test snapshot saves to correct JSON file"""
        snapshot = self.monitor.calculate_drift(
            region_name="test_region",
            live_price=10_000_000,
            data_source="lamudi",
            confidence=0.85
        )
        
        # Manually save snapshot
        self.monitor._save_drift_snapshot(snapshot)
        
        # Check file exists
        history_file = Path(self.test_dir) / "test_region_drift_history.json"
        self.assertTrue(history_file.exists())
        
        # Check file contents
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['region_name'], "test_region")
        self.assertAlmostEqual(history[0]['drift_pct'], 25.0, places=1)
    
    def test_append_multiple_snapshots(self):
        """Test multiple snapshots append correctly"""
        for i in range(5):
            snapshot = self.monitor.calculate_drift(
                region_name="test_region",
                live_price=8_000_000 + (i * 500_000),  # Increasing prices
                data_source="lamudi",
                confidence=0.85
            )
            self.monitor._save_drift_snapshot(snapshot)
        
        # Check file has all 5 snapshots
        history_file = Path(self.test_dir) / "test_region_drift_history.json"
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        self.assertEqual(len(history), 5)
        
        # Verify drift increases with price
        drifts = [s['drift_pct'] for s in history]
        self.assertEqual(drifts, sorted(drifts))  # Monotonically increasing
    
    def test_ttl_cleanup_removes_old_snapshots(self):
        """Test TTL cleanup removes snapshots older than retention_days"""
        now = datetime.now()
        
        # Create 10 snapshots spanning 14 days
        for i in range(10):
            snapshot_time = now - timedelta(days=i)
            snapshot = {
                'timestamp': snapshot_time.isoformat(),
                'region_name': 'test_region',
                'tier': 'tier_1_metros',
                'benchmark_price': 8_000_000,
                'live_price': 9_000_000,
                'drift_pct': 12.5,
                'data_source': 'lamudi',
                'confidence': 0.85,
                'alert_level': 'WARNING'
            }
            self.monitor._save_drift_snapshot(snapshot)
        
        # Check file contents
        history_file = Path(self.test_dir) / "test_region_drift_history.json"
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Should only have 7 snapshots (retention_days=7)
        self.assertLessEqual(len(history), 8)  # Allow 1 day grace period
        
        # All remaining snapshots should be within retention window
        cutoff = now - timedelta(days=self.monitor.retention_days)
        for snapshot in history:
            snapshot_time = datetime.fromisoformat(snapshot['timestamp'])
            self.assertGreaterEqual(snapshot_time, cutoff)
    
    def test_get_drift_history(self):
        """Test get_drift_history retrieves correct time window"""
        now = datetime.now()
        
        # Create snapshots over 30 days
        for i in range(30):
            snapshot_time = now - timedelta(days=i)
            snapshot = {
                'timestamp': snapshot_time.isoformat(),
                'region_name': 'test_region',
                'tier': 'tier_1_metros',
                'benchmark_price': 8_000_000,
                'live_price': 8_000_000 + (i * 100_000),
                'drift_pct': (i * 100_000) / 8_000_000 * 100,
                'data_source': 'lamudi',
                'confidence': 0.85,
                'alert_level': 'NONE'
            }
            self.monitor._save_drift_snapshot(snapshot)
        
        # Get last 14 days
        history_14d = self.monitor.get_drift_history("test_region", days=14)
        
        # Should have ~14 snapshots (one per day)
        self.assertLessEqual(len(history_14d), 15)
        self.assertGreaterEqual(len(history_14d), 13)


class TestConsecutiveWeekDetection(unittest.TestCase):
    """Test consecutive week counting for persistence-based alerts"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_consecutive_weeks_warning_4_weeks(self):
        """Test WARNING requires 4+ consecutive weeks >10% drift"""
        now = datetime.now()
        
        # Create 4 weekly snapshots with >10% drift
        for i in range(4):
            snapshot_time = now - timedelta(weeks=i)
            snapshot = {
                'timestamp': snapshot_time.isoformat(),
                'region_name': 'test_region',
                'tier': 'tier_1_metros',
                'benchmark_price': 8_000_000,
                'live_price': 9_000_000,  # +12.5% drift
                'drift_pct': 12.5,
                'data_source': 'lamudi',
                'confidence': 0.85,
                'alert_level': 'WARNING'
            }
            self.monitor._save_drift_snapshot(snapshot)
        
        # Check alerts
        alerts = self.monitor._check_drift_alerts()
        
        # Should have 1 WARNING alert for test_region
        warning_alerts = [a for a in alerts if a['alert_level'] == 'WARNING']
        self.assertGreaterEqual(len(warning_alerts), 1)
        
        # Find test_region alert
        test_alert = next((a for a in warning_alerts if a['region'] == 'test_region'), None)
        self.assertIsNotNone(test_alert)
        self.assertGreaterEqual(test_alert['consecutive_weeks'], 4)
    
    def test_consecutive_weeks_critical_2_weeks(self):
        """Test CRITICAL requires 2+ consecutive weeks >20% drift"""
        now = datetime.now()
        
        # Create 2 weekly snapshots with >20% drift
        for i in range(2):
            snapshot_time = now - timedelta(weeks=i)
            snapshot = {
                'timestamp': snapshot_time.isoformat(),
                'region_name': 'critical_region',
                'tier': 'tier_1_metros',
                'benchmark_price': 8_000_000,
                'live_price': 10_000_000,  # +25% drift
                'drift_pct': 25.0,
                'data_source': 'lamudi',
                'confidence': 0.85,
                'alert_level': 'CRITICAL'
            }
            self.monitor._save_drift_snapshot(snapshot)
        
        # Check alerts
        alerts = self.monitor._check_drift_alerts()
        
        # Should have 1 CRITICAL alert
        critical_alerts = [a for a in alerts if a['alert_level'] == 'CRITICAL']
        self.assertGreaterEqual(len(critical_alerts), 1)
        
        # Find critical_region alert
        test_alert = next((a for a in critical_alerts if a['region'] == 'critical_region'), None)
        self.assertIsNotNone(test_alert)
        self.assertGreaterEqual(test_alert['consecutive_weeks'], 2)


class TestTierAggregation(unittest.TestCase):
    """Test tier-level drift aggregation with confidence weighting"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_tier_drift_summary_single_region(self):
        """Test tier summary with single region"""
        # Create snapshot for Tier 1 region
        snapshot = self.monitor.calculate_drift(
            region_name="jakarta_north_sprawl",
            live_price=10_000_000,
            data_source="lamudi",
            confidence=0.85
        )
        self.monitor._save_drift_snapshot(snapshot)
        
        # Get tier summary
        summary = self.monitor.get_tier_drift_summary("tier_1_metros", days=30)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['tier'], "tier_1_metros")
        self.assertAlmostEqual(summary['avg_drift_pct'], 25.0, places=1)
        self.assertEqual(summary['region_count'], 1)
    
    def test_tier_drift_summary_multiple_regions(self):
        """Test tier summary aggregates multiple regions correctly"""
        # Create snapshots for multiple Tier 1 regions
        regions = [
            ("jakarta_north_sprawl", 10_000_000, 0.85),  # +25% drift
            ("tangerang_bsd_corridor", 9_000_000, 0.90),  # +12.5% drift
            ("jakarta_south_suburbs", 8_500_000, 0.80)   # +6.25% drift
        ]
        
        for region_name, live_price, confidence in regions:
            snapshot = self.monitor.calculate_drift(
                region_name=region_name,
                live_price=live_price,
                data_source="lamudi",
                confidence=confidence
            )
            self.monitor._save_drift_snapshot(snapshot)
        
        # Get tier summary
        summary = self.monitor.get_tier_drift_summary("tier_1_metros", days=30)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['region_count'], 3)
        
        # Weighted average: (25*0.85 + 12.5*0.90 + 6.25*0.80) / (0.85+0.90+0.80)
        # = (21.25 + 11.25 + 5.0) / 2.55 = 37.5 / 2.55 ≈ 14.7%
        self.assertAlmostEqual(summary['avg_drift_pct'], 14.7, places=0)


class TestHelperMethods(unittest.TestCase):
    """Test helper methods for data extraction"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_extract_live_price_from_dict(self):
        """Test _extract_live_price handles dict input"""
        region_data = {
            'financial_projection': {
                'current_land_value_per_m2': 5_000_000
            }
        }
        
        live_price = self.monitor._extract_live_price(region_data)
        self.assertEqual(live_price, 5_000_000)
    
    def test_extract_live_price_direct_value(self):
        """Test _extract_live_price handles direct numeric input"""
        live_price = self.monitor._extract_live_price(7_500_000)
        self.assertEqual(live_price, 7_500_000)
    
    def test_extract_live_price_missing(self):
        """Test _extract_live_price returns None for missing data"""
        region_data = {'some_other_field': 123}
        live_price = self.monitor._extract_live_price(region_data)
        self.assertIsNone(live_price)
    
    def test_extract_data_source_from_dict(self):
        """Test _extract_data_source handles dict input"""
        region_data = {
            'financial_projection': {
                'data_sources': ['lamudi', 'cache']
            }
        }
        
        data_source = self.monitor._extract_data_source(region_data)
        self.assertEqual(data_source, "lamudi")
    
    def test_extract_data_source_string(self):
        """Test _extract_data_source handles string input"""
        data_source = self.monitor._extract_data_source("lamudi")
        self.assertEqual(data_source, "lamudi")
    
    def test_extract_data_source_default(self):
        """Test _extract_data_source returns default for missing data"""
        data_source = self.monitor._extract_data_source({})
        self.assertEqual(data_source, "unknown")
    
    def test_extract_confidence_from_dict(self):
        """Test _extract_confidence handles dict input"""
        region_data = {
            'scoring_result': {
                'confidence': 0.85
            }
        }
        
        confidence = self.monitor._extract_confidence(region_data)
        self.assertEqual(confidence, 0.85)
    
    def test_extract_confidence_direct_value(self):
        """Test _extract_confidence handles direct numeric input"""
        confidence = self.monitor._extract_confidence(0.92)
        self.assertEqual(confidence, 0.92)
    
    def test_extract_confidence_default(self):
        """Test _extract_confidence returns default for missing data"""
        confidence = self.monitor._extract_confidence({})
        self.assertEqual(confidence, 0.5)  # Default confidence


class TestBatchTracking(unittest.TestCase):
    """Test batch tracking of multiple regions (weekly monitoring integration)"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.monitor = BenchmarkDriftMonitor(
            history_dir=self.test_dir,
            retention_days=180,
            enable_alerts=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_track_drift_batch(self):
        """Test track_drift processes multiple regions correctly"""
        regions_data = [
            {
                'region_name': 'jakarta_north_sprawl',
                'financial_projection': {
                    'current_land_value_per_m2': 10_000_000,
                    'data_sources': ['lamudi']
                },
                'scoring_result': {'confidence': 0.85}
            },
            {
                'region_name': 'bandung_north_expansion',
                'financial_projection': {
                    'current_land_value_per_m2': 6_000_000,
                    'data_sources': ['lamudi']
                },
                'scoring_result': {'confidence': 0.90}
            },
            {
                'region_name': 'semarang_port_expansion',
                'financial_projection': None  # No financial data
            }
        ]
        
        summary = self.monitor.track_drift(regions_data)
        
        # Check summary structure
        self.assertIn('regions_tracked', summary)
        self.assertIn('avg_drift_pct', summary)
        self.assertIn('regions_above_10pct', summary)
        self.assertIn('regions_above_20pct', summary)
        self.assertIn('alerts', summary)
        
        # Should track 2 regions (3rd has no financial data)
        self.assertEqual(summary['regions_tracked'], 2)
        
        # Check history files created
        jakarta_file = Path(self.test_dir) / "jakarta_north_sprawl_drift_history.json"
        bandung_file = Path(self.test_dir) / "bandung_north_expansion_drift_history.json"
        
        self.assertTrue(jakarta_file.exists())
        self.assertTrue(bandung_file.exists())


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
