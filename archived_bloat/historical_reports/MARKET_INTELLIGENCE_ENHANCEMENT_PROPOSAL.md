# Market Intelligence Enhancement Proposal

**Date:** October 25, 2025  
**Version:** 2.6 Proposed  
**Status:** ANALYSIS & DESIGN PHASE

---

## Problem Statement

### Current Limitations

1. **Simplistic Price Ratio Logic**
   - Currently: Region cheaper than Jakarta = "undervalued" = higher score
   - Reality: Cheaper prices often reflect lower demand, fewer amenities, or limited growth potential
   - Example: Remote rural Java is 70% cheaper than Jakarta, but this doesn't make it a better investment

2. **Limited Reference Markets**
   - Only 6 benchmarks: Jakarta, Bali, Yogyakarta, Surabaya, Bandung, Semarang
   - Missing: Regional secondary cities, coastal vs inland distinctions, industrial vs tourism zones
   - Problem: 29 Java regions forced into 6 buckets → poor fit

3. **Context-Blind Market Multiplier**
   - Current tiered system: Booming (>15%) = 1.40x, Declining (<0%) = 0.85x
   - Doesn't account for:
     - **Starting price level** (10% growth on Rp 1M/m² vs Rp 10M/m²)
     - **Infrastructure quality** (growth without roads is speculative)
     - **Regional economic drivers** (tourism vs manufacturing vs agriculture)
     - **Proximity to development catalysts** (new airports, ports, toll roads)

4. **Missing Relative Value Analysis**
   - No comparison to similar regions (peer group analysis)
   - No adjustment for geographic/economic context
   - Example: Bandung East should be compared to other periurban tech corridors, not Jakarta or Bali

---

## Proposed Improvements

### 1. Multi-Tier Regional Classification System

**Replace:** Simple 6-benchmark lookup  
**With:** 4-tier hierarchical classification

```python
REGIONAL_HIERARCHY = {
    'tier_1_metros': {
        'jakarta_metro': ['jakarta_north', 'jakarta_south', 'tangerang', 'bekasi'],
        'surabaya_metro': ['surabaya_east', 'surabaya_west', 'gresik', 'sidoarjo'],
        'benchmarks': {
            'avg_price_m2': 8_000_000,
            'expected_growth': 0.12,  # 12% annual
            'liquidity': 'very_high'
        }
    },
    'tier_2_secondary_cities': {
        'regions': ['bandung_north', 'semarang_port', 'solo_raya', 'yogyakarta_urban_core'],
        'benchmarks': {
            'avg_price_m2': 5_000_000,
            'expected_growth': 0.10,
            'liquidity': 'high'
        }
    },
    'tier_3_emerging_corridors': {
        'industrial': ['cikarang', 'cirebon_port', 'subang_patimban'],
        'tourism': ['yogyakarta_borobudur', 'magelang_corridor', 'malang_highland'],
        'periurban': ['bandung_east', 'semarang_south', 'solo_expansion'],
        'benchmarks': {
            'avg_price_m2': 3_000_000,
            'expected_growth': 0.08,
            'liquidity': 'moderate'
        }
    },
    'tier_4_frontier': {
        'regions': ['gunungkidul_east', 'banyuwangi_ferry', 'jember_southern'],
        'benchmarks': {
            'avg_price_m2': 1_500_000,
            'expected_growth': 0.06,
            'liquidity': 'low'
        }
    }
}
```

**Benefits:**
- ✅ More accurate peer comparisons (compare periurban to periurban, not to Jakarta)
- ✅ Realistic price expectations per tier
- ✅ Context-aware growth benchmarks

---

### 2. Relative Value Index (RVI)

**Replace:** Simple `price_ratio = region_price / jakarta_price`  
**With:** Context-aware relative value calculation

```python
def calculate_relative_value_index(region_data, peer_group_data):
    """
    Calculate RVI: How does this region compare to similar regions?
    
    RVI > 1.2 = Overvalued (expensive for its tier)
    RVI 0.8-1.2 = Fairly valued
    RVI < 0.8 = Undervalued (cheap for its tier)
    """
    # Step 1: Determine peer group
    peer_tier = get_regional_tier(region_data['name'])
    peer_avg_price = REGIONAL_HIERARCHY[peer_tier]['benchmarks']['avg_price_m2']
    
    # Step 2: Adjust for infrastructure quality
    # Better infrastructure should command premium, not penalty
    infra_score = region_data['infrastructure_score']  # 0-100
    infra_premium = 1.0 + ((infra_score - 50) / 100) * 0.3  # ±30% adjustment
    
    # Step 3: Adjust for development momentum
    # High satellite activity = justified premium (future-looking)
    dev_score = region_data['development_score']  # 0-40
    momentum_premium = 1.0 + (dev_score / 40) * 0.2  # Up to +20%
    
    # Step 4: Calculate expected price
    expected_price = peer_avg_price * infra_premium * momentum_premium
    
    # Step 5: Compare actual to expected
    actual_price = region_data['current_price_m2']
    rvi = actual_price / expected_price
    
    return rvi, expected_price, {
        'peer_tier': peer_tier,
        'peer_avg': peer_avg_price,
        'infra_premium': infra_premium,
        'momentum_premium': momentum_premium,
        'expected_price': expected_price,
        'actual_price': actual_price
    }
```

**Example Scenarios:**

| Region | Actual Price | Peer Avg | Infra Score | Dev Score | Expected Price | RVI | Interpretation |
|--------|--------------|----------|-------------|-----------|----------------|-----|----------------|
| Cikarang Industrial | Rp 4.5M | Rp 3M (Tier 3) | 75/100 | 35/40 | Rp 4.2M | 1.07 | Fairly valued |
| Gunungkidul East | Rp 1.2M | Rp 1.5M (Tier 4) | 30/100 | 8/40 | Rp 1.0M | 1.20 | Overvalued |
| Bandung East | Rp 3.8M | Rp 3M (Tier 3) | 68/100 | 28/40 | Rp 3.9M | 0.97 | Undervalued ✅ |

**Benefits:**
- ✅ Contextual pricing (compares apples to apples)
- ✅ Rewards infrastructure quality with justified premiums
- ✅ Accounts for development momentum (satellite activity)
- ✅ Identifies true undervaluation vs just being cheap

---

### 3. Enhanced Market Multiplier with Context

**Current System:**
```python
# Simple trend-based multiplier
if price_trend >= 15%: multiplier = 1.40
elif price_trend >= 8%: multiplier = 1.20
# ... etc
```

**Proposed System:**
```python
def calculate_market_multiplier_v3(region_data, market_data, rvi_data):
    """
    Context-aware market multiplier incorporating:
    - Price trend (current system)
    - Relative value position (RVI)
    - Regional economic drivers
    - Infrastructure support
    """
    # Component 1: Base trend multiplier (current system)
    trend_pct = market_data['price_trend_3m'] * 100
    if trend_pct >= 15:
        base_mult = 1.30  # Reduced from 1.40
    elif trend_pct >= 8:
        base_mult = 1.15  # Reduced from 1.20
    elif trend_pct >= 2:
        base_mult = 1.00
    elif trend_pct >= 0:
        base_mult = 0.95
    else:
        base_mult = 0.85
    
    # Component 2: Value position adjustment (NEW)
    rvi = rvi_data['rvi']
    if rvi < 0.75:
        value_adj = 1.10  # Significantly undervalued → boost
    elif rvi < 0.85:
        value_adj = 1.05  # Moderately undervalued → small boost
    elif rvi < 1.15:
        value_adj = 1.00  # Fairly valued → neutral
    elif rvi < 1.25:
        value_adj = 0.95  # Moderately overvalued → small penalty
    else:
        value_adj = 0.90  # Significantly overvalued → penalty
    
    # Component 3: Economic driver alignment (NEW)
    driver_strength = assess_economic_drivers(region_data)
    # driver_strength: 0.9-1.1 based on how well infrastructure matches regional focus
    
    # Component 4: Infrastructure-growth correlation (NEW)
    # Penalize high growth without infrastructure support (speculative bubble risk)
    infra_score = region_data['infrastructure_score']
    if trend_pct > 10 and infra_score < 40:
        speculation_penalty = 0.90  # High growth + poor infra = risky
    elif trend_pct > 15 and infra_score < 50:
        speculation_penalty = 0.95
    else:
        speculation_penalty = 1.00  # Growth supported by infrastructure
    
    # Final multiplier (range: ~0.70 - 1.50)
    final_mult = base_mult * value_adj * driver_strength * speculation_penalty
    
    # Clamp to reasonable range
    final_mult = max(0.70, min(1.50, final_mult))
    
    return final_mult, {
        'base_trend': base_mult,
        'value_adjustment': value_adj,
        'driver_strength': driver_strength,
        'speculation_penalty': speculation_penalty,
        'final': final_mult
    }
```

**Benefits:**
- ✅ Penalizes unsupported growth (speculation bubbles)
- ✅ Rewards undervalued regions with strong fundamentals
- ✅ Accounts for regional economic context
- ✅ More nuanced than simple trend-based system

---

### 4. Regional Economic Driver Analysis (NEW)

**Concept:** Different regions need different infrastructure to succeed

```python
REGIONAL_ECONOMIC_DRIVERS = {
    'industrial_corridor': {
        'critical_infrastructure': ['highways', 'ports', 'railways', 'construction_activity'],
        'importance_weights': {'highways': 0.35, 'ports': 0.25, 'railways': 0.25, 'construction': 0.15},
        'examples': ['cikarang', 'bekasi', 'cirebon_port', 'gresik']
    },
    'tourism_gateway': {
        'critical_infrastructure': ['airports', 'highways', 'planning_quality'],
        'importance_weights': {'airports': 0.40, 'highways': 0.35, 'planning': 0.25},
        'examples': ['yogyakarta_borobudur', 'magelang', 'banyuwangi']
    },
    'periurban_residential': {
        'critical_infrastructure': ['highways', 'construction_activity', 'planning_quality'],
        'importance_weights': {'highways': 0.40, 'construction': 0.30, 'planning': 0.30},
        'examples': ['bandung_east', 'semarang_south', 'solo_expansion']
    },
    'metro_expansion': {
        'critical_infrastructure': ['highways', 'railways', 'construction_activity'],
        'importance_weights': {'highways': 0.30, 'railways': 0.30, 'construction': 0.40},
        'examples': ['tangerang_bsd', 'jakarta_south', 'surabaya_west']
    }
}

def assess_economic_drivers(region_data):
    """
    Score how well a region's infrastructure aligns with its economic driver
    
    Returns: 0.9 - 1.1 multiplier
    """
    driver_type = classify_region_driver(region_data['name'])
    driver_config = REGIONAL_ECONOMIC_DRIVERS[driver_type]
    
    alignment_score = 0
    for infra_type, weight in driver_config['importance_weights'].items():
        infra_quality = region_data['infrastructure_components'].get(infra_type, 0) / 100
        alignment_score += infra_quality * weight
    
    # Convert 0-1 alignment to 0.9-1.1 multiplier
    driver_multiplier = 0.9 + (alignment_score * 0.2)
    
    return driver_multiplier
```

**Example:**
- **Cikarang (Industrial):** Has excellent highways (95/100), ports (80/100), railways (70/100)
  - Alignment score: 0.35×0.95 + 0.25×0.80 + 0.25×0.70 = 0.84
  - Driver multiplier: 0.9 + (0.84 × 0.2) = **1.07x** ✅ Good alignment
  
- **Yogyakarta Borobudur (Tourism):** Has decent airport (65/100), poor highways (40/100)
  - Alignment score: 0.40×0.65 + 0.35×0.40 = 0.40
  - Driver multiplier: 0.9 + (0.40 × 0.2) = **0.98x** ⚠️ Missing critical infrastructure

---

## Implementation Strategy

### Phase 1: Regional Classification (Low Risk)
**Files:** `src/core/financial_metrics.py`

1. Add `REGIONAL_HIERARCHY` dict with 4-tier system
2. Create `classify_region_tier()` function
3. Update `_get_regional_benchmark()` to use tier-based lookup
4. **Impact:** More accurate baseline expectations per region type

**Estimated Effort:** 2-3 hours  
**Risk:** Low (additive, doesn't change existing logic)

### Phase 2: Relative Value Index (Medium Risk)
**Files:** `src/core/corrected_scoring.py`, `src/core/financial_metrics.py`

1. Create `calculate_relative_value_index()` function
2. Integrate RVI into market multiplier calculation
3. Add RVI to `CorrectedScoringResult` dataclass
4. Update PDF reports to show RVI analysis

**Estimated Effort:** 4-6 hours  
**Risk:** Medium (changes market multiplier calculation, needs testing)

### Phase 3: Economic Driver Analysis (Medium Risk)
**Files:** `src/core/corrected_scoring.py`

1. Add `REGIONAL_ECONOMIC_DRIVERS` configuration
2. Create `assess_economic_drivers()` function
3. Integrate driver alignment into market multiplier
4. Add driver type to region config

**Estimated Effort:** 3-4 hours  
**Risk:** Medium (requires region classification, subjective judgments)

### Phase 4: Context-Aware Market Multiplier (High Risk)
**Files:** `src/core/corrected_scoring.py`

1. Replace `_get_market_multiplier()` with v3 implementation
2. Integrate RVI, drivers, infrastructure-growth correlation
3. Expand multiplier range (0.70-1.50 vs current 0.85-1.40)
4. Add detailed breakdown to scoring result

**Estimated Effort:** 6-8 hours  
**Risk:** High (fundamental change to scoring, requires extensive testing)

---

## Testing Requirements

### 1. Regression Testing
- Run v2.5 and v2.6 side-by-side on same 29 Java regions
- Compare final scores (expect ±10 point shifts)
- Identify any regions with >20 point changes (investigate why)

### 2. Scenario Validation
Test cases:
- **Remote region with high growth but no infrastructure** → Should get speculation penalty
- **Periurban region with strong highways** → Should get driver alignment boost
- **Overvalued region (RVI > 1.2) with stable growth** → Should get value position penalty
- **Undervalued region (RVI < 0.8) with moderate growth** → Should get value position boost

### 3. Economic Logic Checks
- Tier 1 metros should not score higher than Tier 3 corridors (satellite activity still primary)
- Infrastructure-poor regions should not get high multipliers from price trends alone
- Regions with aligned economic drivers should outperform misaligned peers

---

## Expected Impact on Scoring

### Current System (v2.5)
```
Final Score = Development (0-40) × Infrastructure (0.8-1.3) × Market (0.85-1.4) × Confidence (0.7-1.0)
Range: 0-73 theoretical, 15-55 typical
```

### Proposed System (v2.6)
```
Final Score = Development (0-40) × Infrastructure (0.8-1.3) × Market_v3 (0.70-1.50) × Confidence (0.7-1.0)

Market_v3 = Base_Trend × RVI_Adjustment × Driver_Alignment × Speculation_Penalty
Range: 0-78 theoretical, 12-60 typical
```

**Key Differences:**
- Wider market multiplier range (0.70-1.50 vs 0.85-1.40)
- Speculation penalties can reduce scores for unsupported growth
- Value position adjustments reward true undervaluation
- Driver alignment rewards contextually appropriate infrastructure

---

## Open Questions for Discussion

1. **Regional Tier Classification**
   - Should we use rule-based (if/elif) or data-driven clustering?
   - How do we handle edge cases (e.g., Solo = Tier 2 or Tier 3)?
   - Should tier be stored in `indonesia_expansion_regions.py`?

2. **RVI Thresholds**
   - Is 0.8-1.2 the right "fairly valued" range?
   - Should thresholds vary by tier (Tier 1 tighter range than Tier 4)?
   - How do we handle regions with no price data (use expected price only)?

3. **Economic Driver Classification**
   - Manual classification in config vs automatic detection?
   - Should regions have multiple drivers (e.g., industrial + tourism)?
   - How specific should we be (4 types vs 10+ subtypes)?

4. **Multiplier Range Expansion**
   - Is 0.70-1.50 too wide (increases score variance)?
   - Should we keep conservative 0.85-1.40 and add RVI as separate component?
   - What's the right balance between differentiation and stability?

5. **Backward Compatibility**
   - Run v2.5 and v2.6 in parallel for 4 weeks before full switch?
   - Provide "v2.5 equivalent score" in reports for comparison?
   - How do we explain score changes to stakeholders?

---

## Recommendation

**Proposed Approach:** Incremental rollout in 2 phases

### Phase A: Foundation (Low Risk, High Value)
**Implement:** Regional classification + RVI calculation  
**Timeline:** 1 week  
**Benefit:** Better peer comparisons, identifies true undervaluation  
**Risk:** Low (doesn't change scoring, adds information)

### Phase B: Enhanced Multiplier (Medium Risk, High Value)
**Implement:** Context-aware market multiplier with RVI, drivers, speculation penalty  
**Timeline:** 2 weeks (includes testing)  
**Benefit:** More accurate investment signals, reduces false positives  
**Risk:** Medium (requires validation against historical data)

**Not Recommended (Yet):** Economic driver analysis  
**Reason:** Requires subjective regional classification, should wait for Phase A/B data to validate approach

---

## Next Steps

1. **User Feedback:** Which phases/components are highest priority?
2. **Design Decisions:** Answer open questions on thresholds, classifications
3. **Implementation Order:** Phase A first, or full v2.6 in one release?
4. **Testing Strategy:** What validation would give you confidence in v2.6?

**Ready to discuss and refine approach based on your priorities.**
