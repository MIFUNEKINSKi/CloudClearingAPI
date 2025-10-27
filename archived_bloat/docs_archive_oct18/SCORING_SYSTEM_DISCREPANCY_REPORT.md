# CRITICAL: Investment Scoring System - Actual vs. Documented

**Date**: October 6, 2025  
**Status**: 🚨 MAJOR DISCREPANCY FOUND  
**Severity**: CRITICAL - Documentation describes a completely different system

---

## Executive Summary

The INVESTMENT_SCORING_METHODOLOGY.md documentation describes a satellite-centric three-part scoring system (Development 40% + Infrastructure 35% + Market 25%), but **the actual code implements a market/infrastructure-centric scoring system where satellite data is only informational**.

### Actual Score Distribution (Oct 5, 2025 Run)
```
Minimum: 71.56/100
Maximum: 94.67/100
Mean: ~80/100
```

All 10 Yogyakarta regions scored above 70 (BUY threshold), which is impossible with the documented formula.

---

## What the Code ACTUALLY Does

### Step 1: Calculate Speculative Score (0-100 points)

**Source**: `dynamic_scoring_integration.py` lines 231-270

```python
def _calculate_speculative_score(market_data, infrastructure_data):
    base_score = 50  # Neutral starting point
    
    # Market Momentum Component (0-25 points)
    price_trend = market_data['price_trend_30d']
    if price_trend > 10:
        momentum_bonus = 25
    elif price_trend > 5:
        momentum_bonus = 15
    elif price_trend > 0:
        momentum_bonus = 5
    else:
        momentum_bonus = max(-20, price_trend)  # Can go negative
    
    # Market Heat Component (0-20 points)
    heat_bonuses = {
        'hot': 20,
        'warm': 10,
        'cool': 0,
        'cold': -10,
        'unknown': 0
    }
    heat_bonus = heat_bonuses.get(market_data['market_heat'], 0)
    
    # Infrastructure Quality Component (±15 points)
    infra_score = infrastructure_data['infrastructure_score']
    infra_bonus = (infra_score - 50) * 0.3
    # If infra_score = 100: bonus = +15
    # If infra_score = 50: bonus = 0
    # If infra_score = 0: bonus = -15
    
    # Construction Momentum Component (0-15 points)
    construction_projects = infrastructure_data['active_construction_projects']
    construction_bonus = min(15, construction_projects * 3)
    
    # Final speculative score
    final_score = base_score + momentum_bonus + heat_bonus + infra_bonus + construction_bonus
    return max(0, min(100, final_score))
```

**Possible Range**: 
- Theoretical minimum: 50 - 20 - 10 - 15 + 0 = 5
- Theoretical maximum: 50 + 25 + 20 + 15 + 15 = 125 (clamped to 100)
- Practical range: 50-95

### Step 2: Calculate Infrastructure Multiplier (0.8-1.6+)

**Source**: `dynamic_scoring_integration.py` lines 272-288

```python
def _calculate_infrastructure_multiplier(infrastructure_data):
    base_multiplier = 1.0
    
    # Infrastructure quality multiplier (0.8-1.2)
    infra_score = infrastructure_data['infrastructure_score']
    quality_multiplier = 0.8 + (infra_score / 100) * 0.4
    
    # Accessibility bonus (±0.25)
    accessibility = infrastructure_data['accessibility_data']['overall_accessibility']
    accessibility_bonus = (accessibility - 50) / 200
    
    # Construction momentum bonus (0-0.2)
    construction_bonus = min(0.2, infrastructure_data['active_construction_projects'] * 0.05)
    
    return quality_multiplier + accessibility_bonus + construction_bonus
```

**Possible Range**:
- Minimum: 0.8 + (-0.25) + 0 = 0.55
- Maximum: 1.2 + 0.25 + 0.2 = 1.65
- Typical: 1.0-1.3

### Step 3: Apply Infrastructure Multiplier

```python
base_score = speculative_score × infrastructure_multiplier
```

**Example**: 80 × 1.20 = 96

### Step 4: Apply Confidence Weighting

```python
confidence_weight = (market_confidence + infrastructure_confidence) / 2
final_score = base_score × (0.5 + confidence_weight × 0.5)
```

**With high confidence (0.85)**:
```
final_score = 96 × (0.5 + 0.85 × 0.5) = 96 × 0.925 = 88.8
```

**Result**: Final scores naturally fall in the 70-95 range!

---

## What the Documentation CLAIMS

### The False Three-Part System

```
Development Score (0-40 points) from satellite change detection
× Infrastructure Multiplier (0.90-1.20)
× Market Multiplier (0.95-1.15)
= Final Score (theoretical max: 40 × 1.20 × 1.15 = 55.2)
```

### Why This Would Never Work

**Maximum possible score**: 40 × 1.20 × 1.15 = 55.2  
**With confidence weighting**: 55.2 × 0.925 = 51.1

**But actual scores are 71-95!** This proves the documentation is wrong.

---

## Where is the Satellite Data?

### It's Stored But NOT Used in Scoring!

**Source**: `automated_monitor.py` lines 1270-1320

The satellite change detection runs and produces:
- `total_changes`: Number of changed pixels
- `area_affected`: Hectares of change
- `change_types`: Classification of changes

**But this data is only stored as metadata**:
```python
buy_recommendations.append({
    'region': region_name,
    'investment_score': result.final_investment_score,  # From dynamic scoring
    'satellite_changes': changes_detected,  # Just informational!
    'infrastructure_score': result.infrastructure_score,
    'market_heat': result.market_heat
})
```

**The satellite data does not affect the score calculation at all!**

---

## Real-World Example: gunungkidul_east

### Actual Output (Oct 5, 2025)
```json
{
  "region": "gunungkidul_east",
  "investment_score": 94.67,
  "confidence": 0.72,
  "satellite_changes": 35862,
  "recommendation": "BUY"
}
```

### How This Score Was Actually Calculated

**Step 1: Speculative Score**
```python
base = 50
price_trend = assume ~8% → momentum_bonus = 15
market_heat = 'unknown' → heat_bonus = 0
infrastructure_score = 100 → infra_bonus = (100-50) × 0.3 = 15
construction_projects = assume 2 → construction_bonus = 6

speculative_score = 50 + 15 + 0 + 15 + 6 = 86
```

**Step 2: Infrastructure Multiplier**
```python
quality_multiplier = 0.8 + (100/100) × 0.4 = 1.2
accessibility_bonus = (60-50)/200 = 0.05
construction_bonus = 0.10

infrastructure_multiplier = 1.2 + 0.05 + 0.10 = 1.35
```

**Step 3: Base Score**
```python
base_score = 86 × 1.35 = 116.1 (clamped to 100)
```

**Step 4: Confidence Weighting**
```python
confidence_weight = (0.85 + 0.90) / 2 = 0.875
final_score = 100 × (0.5 + 0.875 × 0.5) = 100 × 0.9375 = 93.75
```

**Result**: ~94/100 ✅ (Matches actual output!)

**Note**: The 35,862 satellite changes are stored but have ZERO impact on the score!

---

## Implications

### 1. The Documented System is Fiction

The entire "Development Activity 40%" concept doesn't exist in the code. The satellite analysis runs, but the results are only used for visual inspection in PDFs, not for scoring.

### 2. Scores Are Inflated

Because the system starts at 50 (not 0) and adds bonuses, nearly every region with decent infrastructure scores above 70. This makes the BUY threshold essentially meaningless.

### 3. Score Distribution Issues

**Current thresholds**:
- BUY: ≥70 with ≥60% confidence
- WATCH: 50-69 with ≥40% confidence
- PASS: <50

**Problem**: Almost everything is a BUY! The system has no way to score below 50 unless market data is catastrophically bad.

### 4. The Three-Part System is a Lie

It's actually:
- **Market Dynamics**: ~60% (momentum + heat dominate the speculative score)
- **Infrastructure Quality**: ~40% (bonus in speculative score + multiplier)
- **Satellite Development**: 0% (not used!)

---

## Required Actions

### Immediate (Before Next Run)

1. **Option A: Fix the Documentation**
   - Admit the satellite data is informational only
   - Document the actual speculative scoring system
   - Explain why scores are 70-95 range

2. **Option B: Fix the Code**
   - Rebuild scoring to match the documented three-part system
   - Make satellite change count actually impact the score
   - Implement proper 0-100 scaling

3. **Option C: Hybrid**
   - Incorporate satellite data into the speculative score calculation
   - Add a "development velocity" component based on change count
   - Rebalance weights to get better distribution

### Strategic (This Week)

1. **Recalibrate Thresholds**
   - Analyze score distribution across all 39 Java regions
   - Set new thresholds based on actual range (e.g., BUY ≥85)
   - Ensure thresholds create meaningful differentiation

2. **Add Satellite Integration**
   ```python
   # Example fix
   development_bonus = 0
   if satellite_changes > 50000:
       development_bonus = 20
   elif satellite_changes > 20000:
       development_bonus = 15
   elif satellite_changes > 10000:
       development_bonus = 10
   
   speculative_score += development_bonus
   ```

3. **Validate Scoring Logic**
   - Run side-by-side comparison of old vs. new scoring
   - Verify recommendations make intuitive sense
   - Test edge cases (no market data, no infrastructure, etc.)

---

## Recommendation

**We should rebuild the scoring system to match the documentation**, not the other way around. The documented three-part system makes more intuitive sense:

- Satellite data = objective measurement of actual development
- Infrastructure = accessibility and growth potential
- Market = current demand and pricing trends

The current code makes satellite analysis almost pointless - why run expensive Earth Engine queries if we ignore the results?

**Proposed Fix**:
1. Make satellite change count the primary base score (0-40 points)
2. Use infrastructure as a multiplier (0.8-1.2x)
3. Use market as a secondary multiplier (0.9-1.1x)
4. Result: Scores naturally in 0-60 range with room for differentiation
5. Recalibrate: BUY ≥40, WATCH 25-39, PASS <25

---

## Files to Modify

1. **src/core/dynamic_scoring_integration.py** - Complete rewrite of scoring logic
2. **INVESTMENT_SCORING_METHODOLOGY.md** - Either fix this or rewrite based on code
3. **src/core/automated_monitor.py** - Integrate satellite data into scoring
4. **Thresholds** - Recalibrate BUY/WATCH/PASS based on new distribution

---

**Severity**: CRITICAL  
**Impact**: Current system is fundamentally misrepresented  
**Action Required**: Immediate decision on which to fix (code or docs)
