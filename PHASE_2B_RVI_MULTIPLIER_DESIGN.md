# Phase 2B: RVI-Aware Market Multiplier Design

**Date:** October 25, 2025  
**Version:** 2.6-beta  
**Status:** Implementation Phase

---

## Executive Summary

Phase 2B integrates the Relative Value Index (RVI) into the scoring engine's market multiplier, replacing the simple trend-based system with context-aware valuation intelligence validated in Phase 2A.11.

**Key Change**: Market multiplier transitions from measuring "market momentum" to measuring "relative value opportunity."

---

## Current System (v2.6-alpha) - Trend-Based

### Implementation Location
File: `src/core/corrected_scoring.py`, method: `_get_market_multiplier()`

### Current Logic
```python
def _get_market_multiplier(self, region_name, coordinates, data_availability):
    """Convert market trend to tiered multiplier (0.85-1.4x)"""
    
    price_trend_pct = pricing_data.price_trend_3m * 100
    
    # Trend-based tiers
    if price_trend_pct >= 15:
        multiplier = 1.40  # Booming - exceptional growth
    elif price_trend_pct >= 8:
        multiplier = 1.20  # Strong - very strong market
    elif price_trend_pct >= 2:
        multiplier = 1.00  # Stable - healthy growth
    elif price_trend_pct >= 0:
        multiplier = 0.95  # Stagnant - slow growth
    else:
        multiplier = 0.85  # Declining - market decline
    
    return market_data, multiplier
```

### Problems with Current System

1. **No Context**: A 15% price increase in a Tier 4 frontier region (speculation?) gets same 1.40x multiplier as Tier 1 metro (genuine growth)

2. **Ignores Valuation**: Doesn't distinguish between:
   - Region becoming expensive (rising prices, high RVI) → Should reduce multiplier
   - Region catching up to fair value (rising prices, normalizing RVI) → Current multiplier OK

3. **Momentum Bias**: Rewards recent trends without considering if region is already overvalued

4. **Phase 2A.11 Validation Showed**: 
   - Semarang (undervalued, RVI 0.89) deserves STRONG BUY → Current system gives same multiplier as overvalued region
   - System can't differentiate between "expensive and hot" vs "undervalued and heating up"

---

## Proposed System (v2.6-beta) - RVI-Aware

### Core Principle

**Market multiplier should reward undervalued regions and penalize overvalued ones, with momentum as a minor adjustment.**

### Design Formula

```python
# Primary: RVI-based multiplier (reflects valuation opportunity)
if rvi < 0.7: 
    base_multiplier = 1.40       # Significantly undervalued - strong buy
elif rvi < 0.9: 
    base_multiplier = 1.25       # Undervalued - buy opportunity
elif rvi < 1.1: 
    base_multiplier = 1.0        # Fair value - neutral
elif rvi < 1.3: 
    base_multiplier = 0.90       # Overvalued - caution
else: 
    base_multiplier = 0.85       # Significantly overvalued - speculation risk

# Secondary: Momentum adjustment (±10% based on market trend)
# Positive trend adds small boost, negative trend small penalty
momentum_factor = 1.0 + (price_trend_pct / 100.0) * 0.1

# Final multiplier
final_multiplier = base_multiplier * momentum_factor

# Clamp to preserve existing bounds
final_multiplier = max(0.85, min(1.40, final_multiplier))
```

### Rationale for RVI Thresholds

Based on Phase 2A.11 validation results:

| RVI Range | Interpretation | Multiplier | Rationale |
|-----------|---------------|------------|-----------|
| < 0.70 | Significantly Undervalued | 1.40x | No test regions this low, but theoretical strong buy |
| 0.70-0.89 | Undervalued | 1.25x | Semarang (0.89), Magelang (0.89), Solo (0.88) - upgrade to STRONG BUY appropriate |
| 0.90-1.09 | Fair Value | 1.0x | Majority of regions (8/12), neutral stance correct |
| 1.10-1.29 | Overvalued | 0.90x | None in validation, but expected in ultra-premium areas |
| ≥ 1.30 | Significantly Overvalued | 0.85x | Speculation risk, reduce investment attractiveness |

### Momentum Factor Explanation

**Why keep momentum at all?**
- Rising prices in undervalued region → catching up to fair value (good)
- Falling prices in overvalued region → correction (also signals change)

**Why only ±10%?**
- RVI is the primary signal (valuation)
- Momentum is secondary (confirmation/timing)
- Example: RVI 0.85 (undervalued) × 1.25 base × 1.05 momentum (5% trend) = 1.31x final
- Prevents momentum from overwhelming valuation signal

---

## Implementation Plan

### Step 1: Modify `_get_market_multiplier()` Method

**File**: `src/core/corrected_scoring.py`

**Changes**:
1. Add RVI calculation by calling `financial_engine.calculate_relative_value_index()`
2. Apply RVI-based multiplier logic
3. Add momentum adjustment
4. Preserve fallback to trend-based system if RVI unavailable (backward compatibility)

### Step 2: Update Method Signature

**Current**:
```python
def _get_market_multiplier(self, region_name, coordinates, data_availability):
    return market_data, multiplier
```

**Proposed** (with RVI support):
```python
def _get_market_multiplier(self, 
                           region_name, 
                           coordinates, 
                           data_availability,
                           satellite_data=None,
                           infrastructure_data=None):
    # satellite_data and infrastructure_data needed for RVI calculation
    return market_data, multiplier
```

### Step 3: Integration Point

**Current scoring flow**:
```python
# Line ~119 in calculate_investment_score()
market_data, market_multiplier = self._get_market_multiplier(
    region_name, coordinates, data_availability
)
```

**Proposed**:
```python
market_data, market_multiplier = self._get_market_multiplier(
    region_name, 
    coordinates, 
    data_availability,
    satellite_data={'vegetation_loss_pixels': satellite_changes, ...},
    infrastructure_data={'infrastructure_score': infra_score, ...}
)
```

---

## Backward Compatibility

### Fallback Strategy

If RVI calculation fails (missing data, tier classification unavailable, etc.):

```python
try:
    rvi_data = self.financial_engine.calculate_relative_value_index(
        region_name=region_name,
        satellite_data=satellite_data,
        infrastructure_data=infrastructure_data,
        market_data=market_data
    )
    rvi = rvi_data['rvi']
    
    if rvi is not None:
        # Use RVI-aware multiplier
        multiplier = self._calculate_rvi_multiplier(rvi, price_trend_pct)
    else:
        # Fallback to trend-based multiplier
        multiplier = self._calculate_trend_multiplier(price_trend_pct)
        
except Exception as e:
    logger.warning(f"RVI calculation failed: {e}, using trend-based fallback")
    multiplier = self._calculate_trend_multiplier(price_trend_pct)
```

### Preserves Existing Behavior

- If `financial_engine` is None → trend-based multiplier
- If tier classification unavailable → trend-based multiplier
- If RVI calculation throws exception → trend-based multiplier

**This ensures no regressions in regions without tier classification.**

---

## Expected Impact (Based on Phase 2A.11 Validation)

### Semarang North Coast (Tier 2)

**Before (v2.6-alpha)**:
- Market trend: 10% (hypothetical)
- Multiplier: 1.20x (strong market)
- Recommendation: BUY

**After (v2.6-beta)**:
- RVI: 0.893 (undervalued)
- Base multiplier: 1.25x (undervalued)
- Momentum adjustment: 1.0 + 0.10 * 0.1 = 1.01x
- Final multiplier: 1.25 × 1.01 = **1.26x**
- Recommendation: **STRONG BUY** ✅

**Improvement**: Correctly identifies undervalued industrial zone for stronger recommendation.

---

### Tangerang BSD Corridor (Tier 1) - After Phase 2B.3 Tier 1+ Fix

**Before (v2.6-alpha)**:
- Market trend: 12% (hypothetical)
- Multiplier: 1.20x (strong market)
- Recommendation: BUY

**After (v2.6-beta with Tier 1+ fix)**:
- RVI: 1.10 (slightly overvalued after 9.5M benchmark adjustment)
- Base multiplier: 0.90x (overvalued caution)
- Momentum adjustment: 1.0 + 0.12 * 0.1 = 1.012x
- Final multiplier: 0.90 × 1.012 = **0.91x**
- Recommendation: **WATCH** ⚠️

**Improvement**: Prevents overinvestment in expensive growth corridor (already priced in).

---

### Pacitan Coastal (Tier 4)

**Before (v2.6-alpha)**:
- Market trend: 2% (hypothetical)
- Multiplier: 1.00x (stable)
- Recommendation: BUY

**After (v2.6-beta with Tier 4 infra range fix)**:
- RVI: 0.85 (moderately undervalued after wider infra discount)
- Base multiplier: 1.25x (undervalued)
- Momentum adjustment: 1.0 + 0.02 * 0.1 = 1.002x
- Final multiplier: 1.25 × 1.002 = **1.25x**
- Recommendation: **BUY** ✅

**BUT**: With low infrastructure (38), confidence multiplier likely reduces final score below BUY threshold → **WATCH**

**Improvement**: More nuanced assessment of frontier regions.

---

## Testing Strategy

### Unit Tests

**File**: `test_phase_2b_enhancements.py`

```python
def test_rvi_aware_multiplier_significantly_undervalued():
    """RVI < 0.7 should give 1.40x base multiplier"""
    scorer = CorrectedInvestmentScorer(...)
    rvi = 0.65
    price_trend_pct = 5.0
    
    multiplier = scorer._calculate_rvi_multiplier(rvi, price_trend_pct)
    
    # Base 1.40 × momentum 1.005 = 1.407
    assert 1.40 <= multiplier <= 1.41

def test_rvi_aware_multiplier_undervalued():
    """RVI 0.7-0.9 should give 1.25x base multiplier"""
    rvi = 0.85
    price_trend_pct = 3.0
    
    multiplier = scorer._calculate_rvi_multiplier(rvi, price_trend_pct)
    
    # Base 1.25 × momentum 1.003 = 1.254
    assert 1.25 <= multiplier <= 1.26

def test_rvi_aware_multiplier_fair_value():
    """RVI 0.9-1.1 should give 1.0x base multiplier"""
    rvi = 1.0
    price_trend_pct = 0.0
    
    multiplier = scorer._calculate_rvi_multiplier(rvi, price_trend_pct)
    
    assert multiplier == 1.0

def test_rvi_aware_multiplier_overvalued():
    """RVI 1.1-1.3 should give 0.90x base multiplier"""
    rvi = 1.15
    price_trend_pct = 8.0
    
    multiplier = scorer._calculate_rvi_multiplier(rvi, price_trend_pct)
    
    # Base 0.90 × momentum 1.008 = 0.907
    assert 0.90 <= multiplier <= 0.91

def test_rvi_aware_multiplier_significantly_overvalued():
    """RVI >= 1.3 should give 0.85x base multiplier"""
    rvi = 1.35
    price_trend_pct = 15.0
    
    multiplier = scorer._calculate_rvi_multiplier(rvi, price_trend_pct)
    
    # Base 0.85 × momentum 1.015 = 0.863
    assert 0.85 <= multiplier <= 0.87

def test_rvi_fallback_to_trend():
    """When RVI unavailable, fallback to trend-based multiplier"""
    rvi = None
    price_trend_pct = 12.0
    
    multiplier = scorer._get_market_multiplier_with_fallback(rvi, price_trend_pct)
    
    # Should use trend-based: 12% → 1.20x
    assert multiplier == 1.20
```

### Integration Tests

**Re-run**: `test_v25_vs_v26_validation.py` with Phase 2B enhancements

**Expected Improvements**:
- Average improvement score: 86.7 → **>90.0** ✅
- RVI sensibility: 66.7% → **>75%** ✅
- Tier 2 perfect score: Maintained at 100/100 ✅

---

## Logging & Debugging

### Enhanced Logging

```python
logger.info(f"   💰 Market Multiplier Calculation:")
logger.info(f"      RVI: {rvi:.3f} ({rvi_interpretation})")
logger.info(f"      Base multiplier (RVI): {base_multiplier:.2f}x")
logger.info(f"      Price trend: {price_trend_pct:.1f}%")
logger.info(f"      Momentum factor: {momentum_factor:.3f}x")
logger.info(f"      Final multiplier: {final_multiplier:.2f}x")
```

### Debug Output Example

```
💰 Market Multiplier Calculation:
   RVI: 0.893 (Undervalued)
   Base multiplier (RVI): 1.25x
   Price trend: 10.2%
   Momentum factor: 1.010x
   Final multiplier: 1.26x
```

---

## Documentation Updates

### Files to Update

1. **TECHNICAL_SCORING_DOCUMENTATION.md**:
   - Add Phase 2B section
   - Document RVI-aware multiplier formula
   - Explain momentum adjustment logic

2. **README.md**:
   - Update "What's New in v2.6-beta"
   - Add Phase 2B features
   - Update status to Phase 2B complete

3. **copilot-instructions.md**:
   - Update scoring pipeline diagram
   - Add Phase 2B multiplier logic to key patterns

---

## Success Criteria

✅ **Implementation Complete When**:
1. RVI-aware multiplier implemented in `corrected_scoring.py`
2. Backward compatibility fallback working
3. Unit tests passing (6+ tests)
4. Integration test improvement score ≥90/100
5. RVI sensibility rate ≥75%
6. No regressions in Tier 2 perfect score
7. Logging enhanced with RVI details
8. Documentation updated

---

## Next Steps (Phase 2B.2-2B.6)

After completing Phase 2B.1 (this design + implementation):

1. **Phase 2B.2**: Implement airport premium override (Yogyakarta fix)
2. **Phase 2B.3**: Create Tier 1+ sub-classification (Tangerang BSD fix)
3. **Phase 2B.4**: Tier-specific infrastructure ranges (Tier 4 frontier fix)
4. **Phase 2B.5**: Integration testing & validation
5. **Phase 2B.6**: Documentation & v2.6-beta release

---

**Design Complete:** October 25, 2025  
**Implementation Target:** Week of October 28, 2025  
**Release Target:** v2.6-beta (Phase 2B complete)
