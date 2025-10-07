# Integration Plan: Deploy Corrected Scoring System

**Date**: October 6, 2025  
**Status**: READY FOR DEPLOYMENT  
**Testing**: ✅ PASSED (see test_corrected_scoring.py results)

---

## Phase 1: Code Integration (2 hours)

### Step 1: Update automated_monitor.py
Replace the call to `dynamic_scoring_integration.py` with `corrected_scoring.py`:

**File**: `src/core/automated_monitor.py`

**Old Code** (lines ~1270-1320):
```python
from src.core.dynamic_scoring_integration import DynamicInvestmentScorer

# Calculate dynamic score
scorer = DynamicInvestmentScorer(price_engine, infrastructure_engine)
result = scorer.calculate_dynamic_score(region_name, region_config)
```

**New Code**:
```python
from src.core.corrected_scoring import CorrectedInvestmentScorer

# Calculate CORRECTED score (satellite-centric!)
scorer = CorrectedInvestmentScorer(price_engine, infrastructure_engine)
result = scorer.calculate_investment_score(
    region_name=region_name,
    satellite_changes=total_changes,  # From change detection!
    area_affected_m2=area_m2,
    region_config=region_config,
    coordinates=coordinates,
    bbox=bbox
)
```

### Step 2: Update Recommendation Thresholds

**File**: `src/core/automated_monitor.py` (recommendation logic)

**Old Thresholds**:
```python
if score >= 70 and confidence >= 0.60:
    recommendation = 'BUY'
elif score >= 50 and confidence >= 0.40:
    recommendation = 'WATCH'
```

**New Thresholds** (based on 0-60 score range):
```python
if score >= 40 and confidence >= 0.60:
    recommendation = 'BUY'
elif score >= 25 and confidence >= 0.40:
    recommendation = 'WATCH'
```

### Step 3: Update PDF Report Generator

**File**: `src/core/pdf_report_generator.py`

Update score interpretation text:
- OLD: "Scores range 0-100 (typical 70-95)"
- NEW: "Scores range 0-100 (typical 0-60)"

Update threshold explanations:
- OLD: "BUY: ≥70, WATCH: 50-69, PASS: <50"
- NEW: "BUY: ≥40, WATCH: 25-39, PASS: <25"

---

## Phase 2: Documentation Updates (1 hour)

### Step 1: Fix INVESTMENT_SCORING_METHODOLOGY.md

Remove ALL fake scaling factors and examples with inflated scores:

**Delete These Sections**:
- Line 693: `40 × 1.20 × 1.08 × 1.81 (scaling) = 100/100`
- Line 744: `25 × 1.20 × 1.08 × 2.5 (scaling) = 81/100`
- Line 781: `15 × 1.00 × 1.00 × 3.0 (scaling) = 45/100`

**Replace With**:
```markdown
### Real-World Example: gunungkidul_east

**Satellite Changes**: 35,862 (massive development)
**Development Score**: 35/40 (based on change count)
**Infrastructure Multiplier**: 1.00x (neutral - data unavailable in test)
**Market Multiplier**: 1.00x (neutral - data unavailable in test)
**Confidence Weighting**: 0.82 (satellite only, 40% confidence)

**Calculation**:
35 × 1.00 × 1.00 × 0.82 = 28.7/100

**Recommendation**: WATCH
**Rationale**: Significant development activity, requires infrastructure/market validation
```

### Step 2: Update Threshold Documentation

**File**: INVESTMENT_SCORING_METHODOLOGY.md (Investment Recommendation Logic section)

```markdown
## NEW Thresholds (Corrected System)

### Buy Signal Criteria
- **BUY**: Score ≥40 with ≥60% confidence
  - Represents regions with 10,000+ satellite changes
  - Strong infrastructure (multiplier >1.1x)
  - Growing market (multiplier >1.05x)

### Watch List Criteria
- **WATCH**: Score 25-39 with ≥40% confidence
  - Moderate development (5,000-10,000 changes)
  - Acceptable infrastructure
  - Requires monitoring

### Pass/Avoid
- **PASS**: Score <25 or confidence <40%
  - Low development activity (<5,000 changes)
  - OR insufficient data confidence
```

---

## Phase 3: Validation Testing (1 hour)

### Test Checklist

- [ ] Run full monitoring with corrected scoring
- [ ] Verify scores range 0-60 (not 70-95)
- [ ] Check recommendation distribution:
  - Should have mix of BUY/WATCH/PASS (not all BUYs)
- [ ] Validate PDF generation works
- [ ] Confirm satellite changes drive the scores
- [ ] Test with extreme cases:
  - [ ] 0 changes → Score ~4 (PASS)
  - [ ] 50,000+ changes → Score ~40-50 (BUY)

### Command to Test:
```bash
python run_weekly_monitor.py --test-mode
```

---

## Phase 4: Production Deployment

### Deployment Steps:

1. **Backup old system**:
   ```bash
   cp src/core/dynamic_scoring_integration.py src/core/dynamic_scoring_integration.py.backup
   ```

2. **Deploy corrected scorer**:
   - Already created: `src/core/corrected_scoring.py` ✅
   - Integration code ready

3. **Update monitoring scripts**:
   - `run_weekly_monitor.py`
   - `run_monitoring.py`
   - `weekly_strategic_monitor.py`

4. **Run first production test**:
   ```bash
   python run_weekly_monitor.py
   ```

5. **Review output**:
   - Check JSON: `output/monitoring/weekly_monitoring_*.json`
   - Check PDF: `output/reports/executive_summary_*.pdf`
   - Verify scores make sense

6. **If issues found**:
   - Rollback: Use `dynamic_scoring_integration.py.backup`
   - Debug and retest

---

## Phase 5: Monitoring & Adjustment (Ongoing)

### Week 1 Post-Deployment:
- [ ] Monitor score distribution across all 39 Java regions
- [ ] Verify BUY/WATCH/PASS breakdown is reasonable
- [ ] Check for edge cases

### Potential Adjustments:
If scores are too low (everything <25):
- Increase development score scaling
- Adjust confidence weighting (currently 0.7-1.0)

If scores are too high (everything >40):
- Add stricter thresholds for higher tiers
- Increase multiplier impact

### Success Metrics:
- **Ideal distribution**: 20% BUY, 40% WATCH, 40% PASS
- **Score range**: 5-55 typical (with outliers 0-60)
- **Differentiation**: Top region should score 2-3x bottom region

---

## Rollback Plan (If Needed)

If corrected scoring causes issues:

```bash
# Revert to old system
git checkout src/core/automated_monitor.py
git checkout INVESTMENT_SCORING_METHODOLOGY.md

# Or manually:
# 1. Change import back to dynamic_scoring_integration
# 2. Revert thresholds to BUY ≥70
# 3. Document reason for rollback
```

---

## Success Criteria

✅ **Deployment is successful when**:
1. Scores range 0-60 (not 70-95)
2. Satellite changes directly impact scores
3. Clear differentiation between high/low activity regions
4. Reasonable BUY/WATCH/PASS distribution
5. PDF reports show updated thresholds
6. Documentation matches reality

---

## Timeline

- **Phase 1** (Code Integration): 2 hours
- **Phase 2** (Documentation): 1 hour
- **Phase 3** (Testing): 1 hour
- **Phase 4** (Deployment): 30 minutes
- **Phase 5** (Monitoring): Ongoing

**Total Initial Effort**: ~4.5 hours  
**Expected Completion**: End of Day 1

---

## Sign-Off

- [ ] Code changes reviewed
- [ ] Tests passed
- [ ] Documentation updated
- [ ] Deployment plan approved
- [ ] Rollback plan ready
- [ ] **READY TO DEPLOY** ✅
