# API Failure Root Cause Analysis

## Executive Summary

**Problem**: All regions showing exactly 71% confidence instead of expected 95%

**Root Cause Found**: Both Market and Infrastructure APIs are missing critical metadata fields

---

## Detailed Findings

### 1. Market Price API - **PARTIALLY BROKEN** ⚠️

**File**: `src/core/price_intelligence.py`

**Issue**: Market API returns data, but missing key field

**Evidence**:
```json
{
  "market": "live",  // ✅ API is working
  "price_trend_30d": 2.7,  // ✅ Has data
  "current_price_per_m2": 0,  // ❌ WRONG! Should have actual price
  "data_confidence": 0.75  // ✅ This field exists in code
}
```

**Status**: API is functional but data quality is suspect

**Line 251** in `price_intelligence.py`:
```python
return PropertyPricing(
    region_name=region_name,
    avg_price_per_m2=current_price,  # ✅ This is populated
    price_trend_3m=price_trend_3m,  # ✅ This is populated  
    ...
    data_confidence=0.75  # ✅ THIS IS SET!
)
```

**But in JSON output**:
```json
"current_price_per_m2": 0  // ❌ Why is this 0 if avg_price_per_m2 has value?
```

**Conclusion**: The market API is working and returning `data_confidence=0.75`, but something is not being passed through correctly to the final output.

---

### 2. Infrastructure API - **COMPLETELY BROKEN** ❌

**File**: `src/core/infrastructure_analyzer.py`

**Issue**: Missing TWO critical fields in return value

**Evidence**:
```json
{
  "infrastructure": "unavailable",  // ❌ Should be "osm" or "live"
  "infrastructure_score": 100,  // ✅ This works
  "infrastructure_details": {}  // ❌ Empty!
}
```

**Root Cause**: Lines 428-434 in `infrastructure_analyzer.py` returns:
```python
return {
    'infrastructure_score': round(final_score, 1),
    'major_features': major_roads + airports + railways,
    'construction_projects': construction_roads,
    'accessibility_score': round(road_analysis['score'], 1),
    'logistics_score': round((road_analysis['score'] + railway_analysis['score']) / 2, 1),
    'reasoning': reasoning
    # ❌ MISSING: 'data_source' field
    # ❌ MISSING: 'data_confidence' field
}
```

**What corrected_scoring.py expects** (line 139):
```python
'infrastructure': infrastructure_data.get('data_source', 'unavailable'),  // ❌ Gets 'unavailable'!
```

**And for confidence** (line 333):
```python
infra_confidence = infrastructure_data.get('data_confidence', 0.0)  // ❌ Gets 0.0!
```

---

## Why This Causes 71% Confidence

**Confidence Calculation** (lines 314-339 in `corrected_scoring.py`):

```python
# Step 1: Base confidence with all 3 sources
base_confidence = 0.75  # ✅ All data available

# Step 2: Check market data quality
market_confidence = market_data.get('data_confidence', 0.0)  # Gets 0.0 ❌
if market_confidence < 0.7:
    base_confidence *= 0.95  # 0.75 × 0.95 = 0.7125

# Step 3: Check infrastructure data quality  
infra_confidence = infrastructure_data.get('data_confidence', 0.0)  # Gets 0.0 ❌
if infra_confidence < 0.7:
    base_confidence *= 0.95  # 0.7125 × 0.95 = 0.676875

# Result: 0.676875 ≈ 0.71 (71%)
```

**Wait, that should be ~68%, but we're seeing 71%...**

Let me recalculate:
- Base: 75%
- Market fails (0.0 < 0.7): 75% × 0.95 = **71.25%**
- Infrastructure fails (0.0 < 0.7): 71.25% × 0.95 = 67.69%

**Actually seeing 71%** means only **ONE** API is failing the confidence check, not both!

Let me check the actual logic again...

---

## Re-Analysis: Which API is Actually Failing?

Looking at the JSON output again:
```json
"data_sources": {
  "satellite": "google_earth_engine",  // ✅
  "infrastructure": "unavailable",  // ❌ FAILS
  "market": "live"  // ✅ WORKS!
}
```

So the calculation is:
1. Base = 75% (3 sources available)
2. Market has data_confidence = 0.75 (✅ passes the 0.7 threshold!)
3. Infrastructure has data_confidence = 0.0 (❌ fails < 0.7)
4. Result: 75% × 1.0 × 0.95 = **71.25%**

**CONCLUSION**: 
- ✅ **Market API is working correctly** (confidence = 0.75)
- ❌ **Infrastructure API is broken** (missing `data_confidence` field)

---

## OSM API Failures - Secondary Issue

**Evidence from logs**:
```
2025-10-12 12:49:48 - WARNING - OSM railway query failed: Expecting value: line 1 column 1 (char 0)
2025-10-12 12:50:02 - WARNING - OSM airport query failed: Expecting value: line 1 column 1 (char 0)
2025-10-12 12:50:32 - WARNING - OSM road query failed: Expecting value: line 1 column 1 (char 0)
```

**Root Cause**: Lines 161, 172, 197 in `infrastructure_analyzer.py`:
```python
response = requests.post(self.osm_base_url, data=overpass_query, timeout=30)
return response.json().get('elements', [])  // ❌ Fails here
```

**Why it fails**:
- `response.json()` expects valid JSON
- OSM API might be returning HTML error page or empty response
- "Expecting value: line 1 column 1 (char 0)" = empty or non-JSON response

**Possible causes**:
1. Rate limiting (too many requests)
2. Invalid query syntax
3. OSM API timeout/error
4. Network issues

**Current behavior**:
- Exceptions are caught (lines 156, 176, 196)
- Returns empty list `[]`
- Infrastructure analysis continues with no OSM data
- Falls back to regional knowledge (line 125)

**Result**:
- Infrastructure scores are calculated from fallback data
- But `data_source` and `data_confidence` are still not added to return value
- So even when OSM works, confidence would still be 0.0!

---

## Fixes Required

### Fix 1: Add data_source and data_confidence to infrastructure_analyzer.py

**Location**: Line 428-434 in `src/core/infrastructure_analyzer.py`

**Current code**:
```python
return {
    'infrastructure_score': round(final_score, 1),
    'major_features': major_roads + airports + railways,
    'construction_projects': construction_roads,
    'accessibility_score': round(road_analysis['score'], 1),
    'logistics_score': round((road_analysis['score'] + railway_analysis['score']) / 2, 1),
    'reasoning': reasoning
}
```

**Fixed code**:
```python
# Determine data source and confidence based on what data we got
has_osm_data = bool(major_roads or airports or railways)
data_source = 'osm_live' if has_osm_data else 'regional_fallback'
data_confidence = 0.85 if has_osm_data else 0.50

return {
    'infrastructure_score': round(final_score, 1),
    'major_features': major_roads + airports + railways,
    'construction_projects': construction_roads,
    'accessibility_score': round(road_analysis['score'], 1),
    'logistics_score': round((road_analysis['score'] + railway_analysis['score']) / 2, 1),
    'reasoning': reasoning,
    'data_source': data_source,  # ✅ ADD THIS
    'data_confidence': data_confidence  # ✅ ADD THIS
}
```

**Expected Result**: Confidence jumps to 95%+ when OSM data is available

---

### Fix 2: Improve OSM API error handling

**Location**: Lines 155-198 in `src/core/infrastructure_analyzer.py`

**Current issue**: Silent failures, no debugging info

**Add better error handling**:
```python
try:
    response = requests.post(self.osm_base_url, data=overpass_query, timeout=30)
    response.raise_for_status()  # ✅ Check HTTP status
    
    # ✅ Check if response is JSON before parsing
    content_type = response.headers.get('Content-Type', '')
    if 'json' not in content_type:
        logger.error(f"OSM API returned non-JSON response: {content_type}")
        logger.debug(f"Response body: {response.text[:500]}")  # First 500 chars
        return []
    
    return response.json().get('elements', [])
except requests.exceptions.Timeout:
    logger.warning(f"OSM road query timed out after 30s")
    return []
except requests.exceptions.RequestException as e:
    logger.warning(f"OSM road query network error: {e}")
    return []
except json.JSONDecodeError as e:
    logger.error(f"OSM road query returned invalid JSON: {e}")
    logger.debug(f"Response body: {response.text[:500]}")
    return []
except Exception as e:
    logger.warning(f"OSM road query failed: {e}")
    return []
```

---

### Fix 3: Also fix fallback function

**Location**: Lines 435-469 in `infrastructure_analyzer.py`

The `_get_regional_infrastructure_fallback()` function also needs to return `data_source` and `data_confidence`:

```python
def _get_regional_infrastructure_fallback(self, region_name: str) -> Dict[str, Any]:
    """Fallback infrastructure scoring based on regional knowledge"""
    
    regional_scores = {...}  # existing code
    
    if region_name in regional_scores:
        result = regional_scores[region_name].copy()
        result['data_source'] = 'regional_fallback'  # ✅ ADD THIS
        result['data_confidence'] = 0.50  # ✅ ADD THIS - lower confidence for fallback
        return result
    else:
        # Default fallback
        return {
            'infrastructure_score': 50,
            'reasoning': ['⚠️ No infrastructure data available - using neutral baseline'],
            'data_source': 'unavailable',  # ✅ ADD THIS
            'data_confidence': 0.0  # ✅ ADD THIS
        }
```

---

## Expected Results After Fixes

### Scenario 1: OSM API Works (Best Case)
```json
{
  "infrastructure_score": 100,
  "data_source": "osm_live",
  "data_confidence": 0.85
}
```
**Confidence Calculation**:
- Base: 75%
- Market: 0.75 (passes 0.7 threshold) × 1.0
- Infrastructure: 0.85 (passes 0.7 threshold) × 1.0
- **Result: 75% confidence**

Wait, that's still only 75%! We need to check the base confidence logic...

Let me re-read the confidence calculation:

```python
# Base confidence by source count
if available_sources == 3:
    base_confidence = 0.75  # All data available
elif available_sources == 2:
    base_confidence = 0.60  # 2/3 sources
else:
    base_confidence = 0.40  # Satellite only

# Adjust for data quality
if data_availability['market_data'] and market_confidence < 0.7:
    base_confidence *= 0.95

if data_availability['infrastructure_data'] and infra_confidence < 0.7:
    base_confidence *= 0.95
```

So with all APIs working:
- Base: 75%
- Market confidence 0.75 ≥ 0.7 → NO penalty
- Infrastructure confidence 0.85 ≥ 0.7 → NO penalty
- **Result: 75%**

**To get 95% confidence**, we need to boost the base OR add quality bonuses!

**Better approach**:
```python
# Base confidence by source count
if available_sources == 3:
    base_confidence = 0.75
elif available_sources == 2:
    base_confidence = 0.60
else:
    base_confidence = 0.40

# ✅ ADD: Bonus for high-quality data
if data_availability['market_data'] and market_confidence >= 0.8:
    base_confidence *= 1.05  # 5% bonus for excellent market data

if data_availability['infrastructure_data'] and infra_confidence >= 0.8:
    base_confidence *= 1.05  # 5% bonus for excellent infrastructure data

# Penalty for low-quality data
if data_availability['market_data'] and market_confidence < 0.7:
    base_confidence *= 0.95

if data_availability['infrastructure_data'] and infra_confidence < 0.7:
    base_confidence *= 0.95

# Cap at 0.95
return max(0.20, min(0.95, base_confidence))
```

With this:
- Base: 75%
- Market bonus (0.75 < 0.8): No bonus
- Infrastructure bonus (0.85 ≥ 0.8): 75% × 1.05 = 78.75%
- **Result: ~79%**

OR set base confidence higher when all 3 sources are excellent:
```python
if available_sources == 3:
    if market_confidence >= 0.7 and infra_confidence >= 0.7:
        base_confidence = 0.90  # High confidence with quality data
    else:
        base_confidence = 0.75  # All sources but lower quality
```

---

## Implementation Priority

1. **CRITICAL**: Fix infrastructure_analyzer.py to add `data_source` and `data_confidence` fields
2. **HIGH**: Improve OSM API error handling and logging
3. **MEDIUM**: Adjust confidence calculation to reward high-quality data
4. **LOW**: Investigate why `current_price_per_m2` is 0 in JSON output

---

## Testing After Fixes

Run single region test:
```bash
python test_scoring_fix.py
```

Expected output:
```
Region: jakarta_north_sprawl
Score: 34.5/100 (WATCH)
Confidence: 79% (up from 71%)

Data Sources:
✅ Satellite: google_earth_engine
✅ Market: live (confidence: 0.75)
✅ Infrastructure: osm_live (confidence: 0.85)
```

Then run full monitoring:
```bash
python run_weekly_java_monitor.py
```

Should see confidence levels of 79-90% instead of 71%.
