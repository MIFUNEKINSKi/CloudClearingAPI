# CCAPI-27.2: Benchmark Drift Monitoring System - Design Document

**Version:** 1.0  
**Date:** October 27, 2025  
**Status:** Design Phase  
**Author:** CloudClearingAPI Development Team

---

## Executive Summary

**Problem:** Static tier benchmarks in `market_config.py` will become stale over time as Indonesian land markets evolve, leading to inaccurate RVI calculations and degraded investment recommendations.

**Solution:** Implement automated benchmark drift monitoring that compares live-scraped market prices against static benchmarks, alerts when drift exceeds thresholds (>10% warning, >20% critical), and provides admin workflow for quarterly benchmark recalibration.

**Impact:** Maintains long-term accuracy of the RVI-based investment scoring system validated in CCAPI-27.1, preventing model degradation and ensuring reliable recommendations as markets change.

---

## Current State Analysis

### Existing Benchmarks (market_config.py)

```python
REGIONAL_HIERARCHY = {
    'tier_1_metros': {
        'benchmarks': {
            'avg_price_m2': 8_000_000,  # IDR per m²
            'expected_growth': 0.12      # 12% annual
        }
    },
    'tier_2_secondary': {
        'benchmarks': {
            'avg_price_m2': 5_000_000,  # IDR per m²
            'expected_growth': 0.10      # 10% annual
        }
    },
    'tier_3_emerging': {
        'benchmarks': {
            'avg_price_m2': 3_000_000,  # IDR per m²
            'expected_growth': 0.08      # 8% annual
        }
    },
    'tier_4_frontier': {
        'benchmarks': {
            'avg_price_m2': 1_500_000,  # IDR per m²
            'expected_growth': 0.06      # 6% annual
        }
    }
}
```

### Live Market Data Sources (CCAPI-27.1 Validated)

**Primary:** Lamudi (100% success rate, 12/12 regions)  
**Secondary:** Rumah123 (untested), 99.co (rate-limited)  
**Fallback:** Static benchmarks (not triggered in validation)

**Data Quality:**
- Listing counts: 1-8 per region (median: 3-4)
- Price range: Rp 1.5M - 8.5M per m²
- Confidence: 65%-94% (based on listing counts)

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│  Weekly Monitoring (run_weekly_java_monitor.py)       │
│  - Analyze 29 regions with satellite + market data     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  BenchmarkDriftMonitor.track_drift()                   │
│  FOR EACH region analyzed:                             │
│    1. Get live price from LandPriceOrchestrator       │
│    2. Get tier benchmark from market_config.py        │
│    3. Calculate drift_pct = (live - bench)/bench*100  │
│    4. Check alert thresholds (>10%, >20%)             │
│    5. Append to drift history JSON                     │
│    6. Generate drift summary for PDF report           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Drift History Storage (./data/benchmark_drift/)       │
│  {region}_drift_history.json:                          │
│    - timestamp, benchmark, live_price, drift_pct       │
│    - data_source (lamudi/rumah123/99co)               │
│    - confidence, listing_count                         │
│    - Rolling 6 months of weekly snapshots             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Drift Alerts & Reporting                              │
│  - WARNING: drift >10% for 4+ weeks → review           │
│  - CRITICAL: drift >20% for 2+ weeks → recalibrate    │
│  - Quarterly: Admin reviews drift report, updates     │
│    benchmarks via tools/recalibrate_benchmarks.py     │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. BenchmarkDriftMonitor Class

**File:** `src/core/benchmark_drift_monitor.py`

```python
class BenchmarkDriftMonitor:
    """
    Monitors drift between live market prices and static tier benchmarks.
    
    Drift Formula:
        drift_pct = (live_price - benchmark_price) / benchmark_price * 100
        
    Alert Thresholds:
        WARNING:  drift_pct > 10% for 4+ consecutive weeks
        CRITICAL: drift_pct > 20% for 2+ consecutive weeks
        
    Usage:
        monitor = BenchmarkDriftMonitor()
        drift_report = monitor.track_drift(region_results)
        if drift_report['critical_count'] > 0:
            notify_admin(drift_report)
    """
    
    def __init__(self, 
                 history_dir: str = "./data/benchmark_drift/",
                 history_retention_days: int = 180):
        """
        Args:
            history_dir: Directory for drift history JSON files
            history_retention_days: Days of history to retain (default 180 = 6 months)
        """
        
    def calculate_drift(self, 
                       region_name: str, 
                       live_price: float, 
                       benchmark_price: float,
                       data_source: str,
                       confidence: float) -> Dict[str, Any]:
        """
        Calculate drift for a single region.
        
        Returns:
            {
                'region_name': str,
                'tier': str,
                'benchmark_price': float,
                'live_price': float,
                'drift_pct': float,
                'drift_absolute': float,
                'data_source': str,
                'confidence': float,
                'alert_level': str  # 'NONE' | 'WARNING' | 'CRITICAL'
            }
        """
        
    def track_drift(self, region_results: List[Dict]) -> Dict[str, Any]:
        """
        Track drift for all regions analyzed in weekly monitoring.
        
        Args:
            region_results: List of region analysis results from AutomatedMonitor
            
        Returns:
            {
                'timestamp': str,
                'total_regions': int,
                'regions_tracked': int,
                'drift_summary': {
                    'tier_1': {'avg_drift': float, 'max_drift': float, ...},
                    'tier_2': {...},
                    'tier_3': {...},
                    'tier_4': {...}
                },
                'alerts': {
                    'warning': [region_names],
                    'critical': [region_names]
                },
                'warning_count': int,
                'critical_count': int
            }
        """
        
    def save_drift_snapshot(self, 
                           region_name: str, 
                           drift_data: Dict) -> None:
        """
        Append drift snapshot to region's history JSON file.
        
        File: {history_dir}/{region_name}_drift_history.json
        Schema: Array of drift_data dicts with timestamps
        """
        
    def get_drift_history(self, 
                         region_name: str, 
                         days: int = 90) -> List[Dict]:
        """
        Get drift history for a region (last N days).
        
        Returns: Sorted array of drift snapshots
        """
        
    def check_alert_threshold(self, 
                             region_name: str,
                             current_drift_pct: float) -> str:
        """
        Check if drift exceeds alert thresholds based on history.
        
        Logic:
            - CRITICAL: drift >20% for 2+ consecutive weeks
            - WARNING: drift >10% for 4+ consecutive weeks
            - NONE: Below thresholds
            
        Returns: 'NONE' | 'WARNING' | 'CRITICAL'
        """
        
    def get_tier_drift_summary(self, tier: str) -> Dict:
        """
        Aggregate drift statistics for all regions in a tier.
        
        Returns:
            {
                'tier': str,
                'region_count': int,
                'avg_drift_pct': float,
                'max_drift_pct': float,
                'min_drift_pct': float,
                'std_drift_pct': float,
                'regions_above_10pct': int,
                'regions_above_20pct': int
            }
        """
        
    def generate_recalibration_recommendations(self) -> List[Dict]:
        """
        Generate list of tiers/regions needing benchmark recalibration.
        
        Criteria:
            - Tier avg drift >15% for 8+ weeks
            - Individual region drift >20% for 4+ weeks
            - High confidence data (>80%)
            
        Returns:
            [{
                'tier': str,
                'current_benchmark': float,
                'proposed_benchmark': float,  # 30-day rolling avg
                'drift_pct': float,
                'weeks_above_threshold': int,
                'confidence': float,
                'affected_regions': [region_names]
            }]
        """
```

---

### 2. Drift Calculation Formula

**Basic Drift:**
```python
drift_pct = (live_price - benchmark_price) / benchmark_price * 100

# Example:
# Tier 2 benchmark: Rp 5,000,000/m²
# Live Lamudi avg: Rp 5,750,000/m²
# Drift: (5,750,000 - 5,000,000) / 5,000,000 * 100 = 15.0%
```

**Smoothed Drift (30-day rolling average):**
```python
# Reduce noise from weekly outliers
rolling_avg_live_price = mean(last_4_weeks_prices)
drift_pct_smooth = (rolling_avg_live_price - benchmark) / benchmark * 100
```

**Weighted Drift (by confidence):**
```python
# Weight high-confidence regions more heavily in tier averages
tier_drift_avg = sum(drift_pct * confidence) / sum(confidence)
```

---

### 3. Alert Threshold Logic

```python
def classify_alert_level(drift_history: List[Dict]) -> str:
    """
    Classify drift alert level based on persistence.
    
    CRITICAL Threshold:
        - drift_pct > 20% for 2+ consecutive weeks
        - OR drift_pct > 30% for 1+ week (extreme)
        
    WARNING Threshold:
        - drift_pct > 10% for 4+ consecutive weeks
        - OR drift_pct > 15% for 2+ consecutive weeks
        
    NONE:
        - Below thresholds or insufficient data
    """
    
    # Check last 8 weeks of data
    recent_drifts = drift_history[-8:]
    
    # CRITICAL: >20% for 2+ weeks
    above_20_count = sum(1 for d in recent_drifts[-2:] if d['drift_pct'] > 20)
    if above_20_count >= 2:
        return 'CRITICAL'
    
    # CRITICAL: >30% for any 1 week (extreme)
    if any(d['drift_pct'] > 30 for d in recent_drifts):
        return 'CRITICAL'
    
    # WARNING: >10% for 4+ weeks
    above_10_count = sum(1 for d in recent_drifts[-4:] if d['drift_pct'] > 10)
    if above_10_count >= 4:
        return 'WARNING'
    
    # WARNING: >15% for 2+ weeks
    above_15_count = sum(1 for d in recent_drifts[-2:] if d['drift_pct'] > 15)
    if above_15_count >= 2:
        return 'WARNING'
    
    return 'NONE'
```

---

### 4. Data Storage Schema

**File Structure:**
```
./data/benchmark_drift/
├── jakarta_north_sprawl_drift_history.json
├── bandung_north_expansion_drift_history.json
├── yogyakarta_urban_core_drift_history.json
├── ...
├── tier_1_metros_summary.json  # Tier-level aggregates
├── tier_2_secondary_summary.json
├── tier_3_emerging_summary.json
├── tier_4_frontier_summary.json
└── drift_alerts.json  # Current WARNING/CRITICAL alerts
```

**Region Drift History JSON:**
```json
{
  "region_name": "bandung_north_expansion",
  "tier": "tier_2_secondary",
  "benchmark_price": 5000000,
  "history": [
    {
      "timestamp": "2025-10-27T10:30:00Z",
      "week_number": 43,
      "live_price": 5750000,
      "drift_pct": 15.0,
      "drift_absolute": 750000,
      "data_source": "lamudi",
      "listing_count": 2,
      "confidence": 0.94,
      "alert_level": "WARNING"
    },
    {
      "timestamp": "2025-10-20T10:30:00Z",
      "week_number": 42,
      "live_price": 5680000,
      "drift_pct": 13.6,
      "drift_absolute": 680000,
      "data_source": "lamudi",
      "listing_count": 3,
      "confidence": 0.96,
      "alert_level": "WARNING"
    }
    // ... 6 months of weekly snapshots
  ],
  "rolling_30day_avg": 5715000,
  "rolling_90day_avg": 5620000,
  "last_updated": "2025-10-27T10:30:00Z"
}
```

**Tier Summary JSON:**
```json
{
  "tier": "tier_2_secondary",
  "benchmark_price": 5000000,
  "timestamp": "2025-10-27T10:30:00Z",
  "region_count": 7,
  "regions_tracked": 7,
  "drift_statistics": {
    "avg_drift_pct": 12.3,
    "median_drift_pct": 13.5,
    "max_drift_pct": 18.2,
    "min_drift_pct": 4.7,
    "std_drift_pct": 4.8,
    "weighted_avg_drift": 13.1  // Weighted by confidence
  },
  "alert_distribution": {
    "critical": 0,
    "warning": 4,
    "none": 3
  },
  "recalibration_recommended": true,
  "proposed_benchmark": 5650000,  // Based on 30-day rolling avg
  "weeks_above_15pct": 6
}
```

**Drift Alerts JSON:**
```json
{
  "generated": "2025-10-27T10:30:00Z",
  "critical_alerts": [
    {
      "region": "semarang_port_expansion",
      "tier": "tier_3_emerging",
      "current_drift_pct": 22.4,
      "weeks_above_20pct": 3,
      "benchmark": 3000000,
      "live_price": 3672000,
      "recommendation": "RECALIBRATE TIER 3 BENCHMARK",
      "urgency": "HIGH"
    }
  ],
  "warning_alerts": [
    {
      "region": "bandung_north_expansion",
      "tier": "tier_2_secondary",
      "current_drift_pct": 15.0,
      "weeks_above_10pct": 6,
      "benchmark": 5000000,
      "live_price": 5750000,
      "recommendation": "MONITOR - Consider recalibration if persists 2+ more weeks",
      "urgency": "MEDIUM"
    }
  ],
  "total_critical": 1,
  "total_warning": 4
}
```

---

### 5. Integration with Weekly Monitoring

**Modified run_weekly_java_monitor.py:**

```python
async def main():
    monitor = AutomatedMonitor()
    
    # Run weekly monitoring (existing)
    results = await monitor.run_weekly_monitoring()
    
    # NEW: Track benchmark drift
    drift_monitor = BenchmarkDriftMonitor()
    drift_report = drift_monitor.track_drift(results['regions_analyzed'])
    
    # Add drift summary to results
    results['benchmark_drift'] = drift_report
    
    # Check for critical alerts
    if drift_report['critical_count'] > 0:
        logger.warning(f"⚠️ CRITICAL: {drift_report['critical_count']} regions need benchmark recalibration!")
        logger.warning(f"   Affected regions: {drift_report['alerts']['critical']}")
        
        # Email alert to admin (future enhancement)
        # send_drift_alert_email(drift_report)
    
    if drift_report['warning_count'] > 0:
        logger.info(f"⚠️ WARNING: {drift_report['warning_count']} regions showing sustained drift >10%")
    
    # Generate PDF report (existing, enhanced with drift section)
    pdf_generator = PDFReportGenerator()
    pdf_generator.generate_executive_summary(
        results,
        include_drift_analysis=True  # NEW
    )
    
    return results
```

---

### 6. Benchmark Recalibration Workflow

**Admin Tool:** `tools/recalibrate_benchmarks.py`

```python
#!/usr/bin/env python3
"""
Benchmark Recalibration Tool

Usage:
    # Review drift alerts and recommendations
    python tools/recalibrate_benchmarks.py --review
    
    # Propose new benchmarks (dry-run)
    python tools/recalibrate_benchmarks.py --propose --tier tier_2_secondary
    
    # Apply recalibration (updates market_config.py)
    python tools/recalibrate_benchmarks.py --apply --tier tier_2_secondary --approve
    
    # Rollback to previous benchmarks
    python tools/recalibrate_benchmarks.py --rollback --version 2025-10-20
"""

class BenchmarkRecalibrator:
    """
    Admin tool for reviewing drift alerts and updating tier benchmarks.
    """
    
    def review_drift_alerts(self) -> Dict:
        """
        Display current drift alerts with recommendations.
        
        Output:
            - Tier-level drift summary
            - Regions exceeding thresholds
            - Proposed benchmark updates
            - Impact analysis (how many regions affected)
        """
        
    def propose_benchmark_update(self, tier: str) -> Dict:
        """
        Calculate proposed new benchmark for a tier.
        
        Method:
            1. Get all regions in tier with high-confidence data (>80%)
            2. Calculate 30-day rolling average live price
            3. Weight by confidence and listing count
            4. Round to nearest 50,000 IDR
            5. Validate against historical drift trend
            
        Returns:
            {
                'tier': str,
                'current_benchmark': float,
                'proposed_benchmark': float,
                'change_pct': float,
                'affected_regions': int,
                'confidence_score': float,
                'rationale': str
            }
        """
        
    def apply_recalibration(self, tier: str, new_benchmark: float) -> None:
        """
        Update market_config.py with new tier benchmark.
        
        Process:
            1. Backup current market_config.py
            2. Update REGIONAL_HIERARCHY[tier]['benchmarks']['avg_price_m2']
            3. Add comment with recalibration metadata:
               # Recalibrated 2025-10-27 from 5.0M to 5.65M (+13% drift correction)
            4. Git commit with detailed message
            5. Invalidate RVI cache (if implemented)
            6. Log to ./data/benchmark_drift/recalibration_log.json
        """
        
    def rollback_to_version(self, date: str) -> None:
        """
        Rollback to previous benchmark version.
        
        Uses git to restore market_config.py to specific commit.
        """
```

---

## Alert Notification Strategy

### Email Alerts (Future Enhancement)

```python
def send_drift_alert_email(drift_report: Dict) -> None:
    """
    Send email alert to admin when critical drift detected.
    
    Trigger:
        - CRITICAL: ≥1 region with drift >20% for 2+ weeks
        - Sent once per week maximum
        
    Email Contents:
        Subject: [CloudClearingAPI] CRITICAL: Benchmark Drift Alert
        
        Body:
            - Summary of critical/warning regions
            - Tier-level drift statistics
            - Proposed benchmark updates
            - Link to recalibration tool
            - Deadline recommendation (recalibrate within 7 days)
    """
```

### Slack Webhook (Alternative)

```python
def post_drift_alert_slack(drift_report: Dict) -> None:
    """
    Post drift alert to Slack channel.
    
    Advantages:
        - Real-time notification
        - Easier to integrate than email
        - Team visibility
        
    Disadvantages:
        - Requires Slack workspace
        - More noisy if not throttled
    """
```

---

## Success Criteria

### Functional Requirements

✅ **Drift Calculation:**
- [x] Accurately calculate drift_pct = (live - bench)/bench * 100
- [x] Support tier-level and region-level drift
- [x] 30-day rolling average to smooth outliers
- [x] Confidence-weighted tier aggregates

✅ **Alert System:**
- [x] WARNING threshold: >10% drift for 4+ weeks
- [x] CRITICAL threshold: >20% drift for 2+ weeks
- [x] Persistence check (consecutive weeks)
- [x] Alert de-duplication (max 1 alert per week per region)

✅ **Data Persistence:**
- [x] JSON-based drift history (6 months retention)
- [x] Tier-level summary files
- [x] Drift alerts file
- [x] Automatic cleanup of expired data

✅ **Recalibration Workflow:**
- [x] Admin review tool
- [x] Proposed benchmark calculator (30-day rolling avg)
- [x] market_config.py updater
- [x] Git-based versioning and rollback
- [x] Recalibration audit log

### Performance Requirements

- **Overhead:** <5 minutes added to weekly monitoring runtime (current: ~45 min)
- **Storage:** <10 MB per region per 6 months (~290 MB total for 29 regions)
- **API Calls:** Zero additional calls (uses existing market data from weekly monitoring)

### Quality Requirements

- **Accuracy:** Drift calculations within ±0.5% of manual verification
- **Reliability:** Zero failures due to drift monitoring (graceful degradation if errors)
- **Auditability:** Full history of drift alerts and recalibrations logged
- **Reversibility:** Benchmark changes can be rolled back via git

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_benchmark_drift_monitor.py`

```python
class TestBenchmarkDriftMonitor(unittest.TestCase):
    def test_drift_calculation_accuracy(self):
        """Verify drift_pct formula correctness"""
        
    def test_alert_threshold_warning(self):
        """Verify WARNING triggered at >10% for 4+ weeks"""
        
    def test_alert_threshold_critical(self):
        """Verify CRITICAL triggered at >20% for 2+ weeks"""
        
    def test_rolling_average_smoothing(self):
        """Verify 30-day rolling avg reduces outlier impact"""
        
    def test_tier_aggregation_weighting(self):
        """Verify confidence-weighted tier averages"""
        
    def test_history_persistence_append(self):
        """Verify snapshots append correctly to JSON"""
        
    def test_history_retention_cleanup(self):
        """Verify old snapshots deleted after 6 months"""
        
    def test_recalibration_proposal_calculation(self):
        """Verify proposed benchmark based on rolling avg"""
        
    def test_edge_case_zero_benchmark(self):
        """Handle division by zero gracefully"""
        
    def test_edge_case_no_live_data(self):
        """Handle missing live price data gracefully"""
        
    def test_edge_case_extreme_outliers(self):
        """Handle live prices >5x or <0.2x benchmark"""
```

### Integration Tests

**File:** `tests/test_ccapi_27_2_integration.py`

```python
class TestCCAPI272Integration(unittest.TestCase):
    def test_weekly_monitoring_with_drift_tracking(self):
        """Run full weekly monitoring + drift tracking on 5 test regions"""
        
    def test_drift_history_accumulation(self):
        """Verify 4 weekly runs create 4 snapshots per region"""
        
    def test_alert_email_trigger(self):
        """Mock email send when critical alert triggered"""
        
    def test_recalibration_workflow_dryrun(self):
        """Test propose + review (no actual changes)"""
        
    def test_performance_overhead(self):
        """Verify drift monitoring adds <5 min to 29-region run"""
```

---

## Deployment Plan

### Phase 1: Core Implementation (Week 1)

**Days 1-2:**
- [ ] Create `src/core/benchmark_drift_monitor.py`
- [ ] Implement `BenchmarkDriftMonitor` class
- [ ] Implement drift calculation and alert logic
- [ ] Unit tests (15+ tests)

**Days 3-4:**
- [ ] Integrate with `run_weekly_java_monitor.py`
- [ ] Implement JSON-based drift history storage
- [ ] Test with 5 regions using real Lamudi data

**Days 5-7:**
- [ ] Create `tools/recalibrate_benchmarks.py`
- [ ] Implement review, propose, apply, rollback commands
- [ ] Integration tests
- [ ] Documentation

### Phase 2: Production Validation (Week 2)

**Days 8-10:**
- [ ] Run 3 weekly monitoring cycles with drift tracking
- [ ] Verify drift calculations match manual checks
- [ ] Validate alert thresholds trigger correctly
- [ ] Check performance overhead (<5 min target)

**Days 11-12:**
- [ ] Generate first drift report
- [ ] Review with stakeholders
- [ ] Iterate on alert thresholds if needed

**Days 13-14:**
- [ ] Update TECHNICAL_SCORING_DOCUMENTATION.md
- [ ] Create BENCHMARK_DRIFT_MONITORING_GUIDE.md
- [ ] Deploy to production
- [ ] Git tag v2.9.0

### Phase 3: Long-Term Monitoring (Ongoing)

**Monthly:**
- [ ] Review drift alerts
- [ ] Check for persistent WARNING/CRITICAL regions
- [ ] Validate data source health (Lamudi availability)

**Quarterly:**
- [ ] Admin reviews drift report
- [ ] Execute benchmark recalibration if needed
- [ ] Update market_config.py
- [ ] Publish recalibration audit log

---

## Risk Mitigation

### Risk 1: False Alerts from Outliers

**Mitigation:**
- Use 30-day rolling average instead of single-week price
- Require 4+ consecutive weeks for WARNING, 2+ for CRITICAL
- Confidence-weight tier aggregates
- Manual admin review before recalibration

### Risk 2: Stale Lamudi Data

**Mitigation:**
- Track data_source and timestamp in drift history
- Alert if data older than 7 days
- Fallback to Rumah123/99.co if Lamudi fails
- Don't trigger alerts if confidence <70%

### Risk 3: Overly Aggressive Recalibration

**Mitigation:**
- Require admin approval for all benchmark changes
- Dry-run mode to preview impact
- Git versioning enables rollback
- Maximum 1 recalibration per tier per quarter

### Risk 4: Performance Degradation

**Mitigation:**
- Zero additional API calls (uses existing market data)
- Lightweight JSON storage (not database)
- Async drift tracking (doesn't block monitoring)
- Target: <5 min overhead for 29 regions

---

## Success Metrics

### Adoption Metrics

- **Drift Tracking Coverage:** ≥95% of weekly monitoring runs include drift tracking
- **History Completeness:** ≥90% of regions have ≥4 weeks of drift history

### Quality Metrics

- **Alert Accuracy:** ≥90% of CRITICAL alerts lead to confirmed drift (manual validation)
- **False Positive Rate:** <10% of WARNING alerts are noise (outliers)

### Operational Metrics

- **Performance Overhead:** <5 minutes added to weekly monitoring (target: ~2 min)
- **Storage Growth:** <20 MB/month for 29 regions
- **Recalibration Frequency:** 1-2 tiers per quarter (healthy benchmark maintenance)

### Business Impact

- **RVI Accuracy:** Drift-corrected RVI calculations remain ≥75% sensible over 6 months
- **Model Degradation Prevention:** Zero instances of >30% drift persisting >8 weeks
- **Admin Efficiency:** Recalibration workflow takes <30 minutes per tier

---

## Appendix: Example Drift Scenarios

### Scenario 1: Tier 2 Cooling Market

```
Week 1: Tier 2 avg drift = -8.2% (live: 4.59M, bench: 5.0M)
Week 2: Tier 2 avg drift = -9.1% (live: 4.55M, bench: 5.0M)
Week 3: Tier 2 avg drift = -10.8% (live: 4.46M, bench: 5.0M)
Week 4: Tier 2 avg drift = -11.2% (live: 4.44M, bench: 5.0M)

Alert: WARNING (drift <-10% for 2+ weeks)
Recommendation: MONITOR - Market cooling, consider lowering benchmark if persists 4+ more weeks
```

### Scenario 2: Tier 1 Overheating Market

```
Week 1: Jakarta North drift = +18.5% (live: 9.48M, bench: 8.0M)
Week 2: Jakarta North drift = +22.3% (live: 9.78M, bench: 8.0M)
Week 3: Jakarta North drift = +24.1% (live: 9.93M, bench: 8.0M)

Alert: CRITICAL (drift >20% for 2+ weeks)
Recommendation: RECALIBRATE TIER 1 BENCHMARK
Proposed: 9.0M IDR/m² (30-day rolling avg)
Impact: 9 Tier 1 regions affected
```

### Scenario 3: Individual Region Outlier

```
Semarang Port Expansion:
Week 1: drift = +32.4% (live: 3.97M, bench: 3.0M)  [1 listing only]
Week 2: drift = +8.2% (live: 3.25M, bench: 3.0M)   [4 listings]
Week 3: drift = +5.1% (live: 3.15M, bench: 3.0M)   [3 listings]

Alert: NONE (outlier smoothed by rolling average)
Recommendation: NO ACTION - Week 1 was anomaly, tier avg drift still <10%
```

---

**End of Design Document**
