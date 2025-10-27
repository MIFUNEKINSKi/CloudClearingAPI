# CRITICAL BUGS FOUND - MUST FIX

**Date:** October 18, 2025  
**Status:** 🔴 BLOCKING - Fix before next monitoring run

---

## Bug #1: Infrastructure/Market Scores Shown Despite API Failures

### Problem
When infrastructure or market APIs fail, the system uses fallback neutral scores (infrastructure=50, market=neutral) BUT the PDF displays these fallback scores as if they were real data.

**Example from report:**
- PDF shows: "Excellent infrastructure (Score: 100)" 
- Confidence breakdown shows: "Infrastructure API unavailable, neutral baseline used"
- **This is contradictory and misleading**

### Root Cause
**File:** `src/core/corrected_scoring.py`, lines 228-235

```python
except Exception as e:
    logger.warning(f"⚠️ Infrastructure data unavailable for {region_name}: {e}")
    infrastructure_data = {
        'infrastructure_score': 50.0,  # Neutral ← FALLBACK SCORE
        'major_features': [],
        'data_source': 'unavailable',  # ← Marked unavailable
        'data_confidence': 0.0
    }
    multiplier = 1.0  # Neutral multiplier when data unavailable
```

**File:** `src/core/pdf_report_generator.py`, lines 440-445

```python
# Infrastructure quality with specifics
if infrastructure_score >= 100:  # ← BUG: Using score without checking data_source!
    key_factors.append(f"<b>Excellent infrastructure</b> (Score: {infrastructure_score:.0f})")
elif infrastructure_score >= 80:
    key_factors.append(f"<b>Good connectivity</b> (Score: {infrastructure_score:.0f})")
elif infrastructure_score > 0:
    key_factors.append(f"<b>Developing infrastructure</b> (Score: {infrastructure_score:.0f})")
```

The PDF generator displays the infrastructure_score without checking if `data_source == 'unavailable'`.

### Fix Required

**In `pdf_report_generator.py` lines 435-450**, replace with:

```python
# Infrastructure quality with specifics - ONLY show if data available
infra_data_source = 'unknown'
if isinstance(data_sources, dict):
    # Check infrastructure_data structure
    if 'infrastructure_data' in data_sources:
        infra_info = data_sources['infrastructure_data']
        if isinstance(infra_info, dict):
            infra_data_source = infra_info.get('data_source', 'unknown')
        elif isinstance(infra_info, str):
            infra_data_source = infra_info

# Only show infrastructure score if data was actually available
if infra_data_source not in ['unavailable', 'fallback', 'unknown']:
    if infrastructure_score >= 100:
        key_factors.append(f"<b>Excellent infrastructure</b> (Score: {infrastructure_score:.0f})")
    elif infrastructure_score >= 80:
        key_factors.append(f"<b>Good connectivity</b> (Score: {infrastructure_score:.0f})")
    elif infrastructure_score > 0:
        key_factors.append(f"<b>Developing infrastructure</b> (Score: {infrastructure_score:.0f})")
else:
    # Show that infrastructure data was unavailable
    key_factors.append(f"<i>⚠️ Infrastructure data unavailable (neutral baseline used)</i>")
```

**Similarly for market data around lines 447-454:**

```python
# Market conditions - ONLY show if data available
market_data_source = 'unknown'
if isinstance(data_sources, dict):
    if 'market_data' in data_sources:
        market_info = data_sources['market_data']
        if isinstance(market_info, dict):
            market_data_source = market_info.get('data_source', 'unknown')
        elif isinstance(market_info, str):
            market_data_source = market_info

# Only show market analysis if data was actually available
if market_data_source not in ['unavailable', 'fallback', 'unknown', 'no_data']:
    if market_heat == 'hot':
        key_factors.append("<b>Hot market</b> - High demand")
    elif market_heat == 'warm':
        key_factors.append("<b>Warming market</b> - Growing interest")
    elif market_heat == 'cold':
        key_factors.append("<b>Buyer's market</b> - Good entry point")
else:
    key_factors.append(f"<i>⚠️ Market data unavailable (neutral baseline used)</i>")
```

---

## Bug #2: Inconsistent Recommendation Thresholds

### Problem
The scoring system defines recommendation thresholds in `corrected_scoring.py` as:
- **BUY**: ≥45 (with confidence ≥70%) OR ≥40 (with confidence ≥60%)
- **WATCH**: ≥25 (with confidence ≥40%)
- **PASS**: <25 OR low confidence

BUT the PDF generator uses different thresholds:
- **BUY**: ≥70
- **WATCH**: ≥50
- **PASS**: <50

**Example:** Solo Raya Expansion scored 41.3/100:
- According to scoring system: Should be **BUY** (41.3 ≥ 40)
- PDF shows: **PASS** (41.3 < 50)

### Root Cause

**File:** `src/core/corrected_scoring.py`, lines 368-390 (CORRECT)

```python
# Strong Buy
if final_score >= 45 and confidence >= 0.70:
    recommendation = 'BUY'
# Moderate Buy  
elif final_score >= 40 and confidence >= 0.60:
    recommendation = 'BUY'
# Watch
elif final_score >= 25 and confidence >= 0.40:
    recommendation = 'WATCH'
# Pass
else:
    recommendation = 'PASS'
```

**File:** `src/core/pdf_report_generator.py`, lines 763-771 (WRONG)

```python
# Determine recommendation label
recommendation = ""
if score >= 70:  # ← BUG: Wrong threshold!
    recommendation = "🟢 BUY"
elif score >= 50:  # ← BUG: Wrong threshold!
    recommendation = "🟡 WATCH"
else:
    recommendation = "⚪ PASS"
```

### Fix Required

**File:** `src/core/pdf_report_generator.py`, lines 763-771

**Replace with:**

```python
# Determine recommendation label - MUST match corrected_scoring.py thresholds!
recommendation = ""

# Use the recommendation from the scoring system if available
if 'recommendation' in investment_rec:
    rec_value = investment_rec['recommendation'].upper()
    if rec_value == 'BUY':
        recommendation = "🟢 BUY"
    elif rec_value == 'WATCH':
        recommendation = "🟡 WATCH"
    else:
        recommendation = "⚪ PASS"
else:
    # Fallback: Calculate based on CORRECT thresholds from corrected_scoring.py
    if score >= 45 and confidence >= 0.70:
        recommendation = "🟢 BUY"
    elif score >= 40 and confidence >= 0.60:
        recommendation = "🟢 BUY"
    elif score >= 25 and confidence >= 0.40:
        recommendation = "🟡 WATCH"
    else:
        recommendation = "⚪ PASS"
```

---

## Bug #3: Data Structure Inconsistency

### Problem
The `infrastructure_data` and `market_data` fields in the result dictionary are sometimes dicts with `data_source` keys, and sometimes just strings. This causes the PDF checks to fail.

### Root Cause
**File:** `src/core/corrected_scoring.py` 

The scoring system returns infrastructure_data and market_data as full dictionaries:
```python
infrastructure_data = {
    'infrastructure_score': 50.0,
    'major_features': [],
    'data_source': 'unavailable',  # ← dict with data_source key
    'data_confidence': 0.0
}
```

But somewhere in the data flow, these get flattened to just strings like `'unavailable'`.

### Fix Required

Need to ensure consistent data structure throughout. In `corrected_scoring.py`, when building the final result, preserve the full data structures:

```python
# In analyze_region() method, when building data_sources dict:
data_sources = {
    'satellite_data': 'sentinel_2',
    'infrastructure_data': infrastructure_data,  # Keep full dict, don't flatten
    'market_data': market_data,  # Keep full dict, don't flatten
    'availability': {
        'satellite_data': data_availability['satellite_data'],
        'infrastructure_data': data_availability.get('infrastructure_data', False),
        'market_data': data_availability.get('market_data', False)
    }
}
```

---

## Testing Checklist

After fixes, verify:

- [ ] When infrastructure API fails, PDF shows "Infrastructure data unavailable" NOT "Excellent infrastructure"
- [ ] When market API fails, PDF shows "Market data unavailable" NOT specific market heat
- [ ] Region with score 41.3 shows "🟢 BUY" or "🟡 WATCH" (depending on confidence), NOT "⚪ PASS"
- [ ] Region with score 70+ shows "🟢 BUY" consistently
- [ ] Region with score <25 shows "⚪ PASS" consistently
- [ ] Confidence breakdown matches "Investment Intelligence" section (no contradictions)

---

## Impact

**Critical:** These bugs make the PDF reports misleading and untrustworthy. Investors seeing "Excellent infrastructure (Score: 100)" when the API failed will make decisions based on false data.

**Priority:** FIX IMMEDIATELY before next monitoring run.

---

## Files to Edit

1. `src/core/pdf_report_generator.py` 
   - Lines 435-450 (infrastructure display logic)
   - Lines 447-454 (market display logic)  
   - Lines 763-771 (recommendation threshold logic)

2. `src/core/corrected_scoring.py`
   - Verify data_sources dict structure preservation (around line 150-180)

---

**Created:** October 18, 2025, 10:32 AM  
**Priority:** 🔴 P0 - Critical  
**Est. Fix Time:** 30 minutes
