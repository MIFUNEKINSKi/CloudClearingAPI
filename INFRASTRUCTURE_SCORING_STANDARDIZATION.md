# Infrastructure Scoring Standardization Plan

**Date:** October 25, 2025  
**Issue:** Inconsistent infrastructure scoring approaches and documentation-code mismatch  
**Goal:** Standardize infrastructure scoring for consistency, maintainability, and clarity

---

## Problem Statement

### Issue 1: Two Different Scoring Philosophies

**Current State:**
1. **Standard Analyzer** (`infrastructure_analyzer.py`): Uses **square root compression**
2. **Enhanced Analyzer** (`enhanced_infrastructure_analyzer.py`): Uses **total caps per component**

**Problems:**
- Different algorithms make cross-analyzer comparison difficult
- Maintenance burden of keeping two approaches in sync
- Unclear when to use which analyzer
- Documentation justifies both but doesn't clarify practical differences

### Issue 2: Documentation vs. Implementation Mismatch

**Documentation Section: "Component Scoring"** (lines 608-693)
Shows simple threshold-based scoring:
```python
# Documented approach (NOT in code)
if major_roads >= 5:
    highway_score = 100
elif major_roads >= 3:
    highway_score = 75
```

**Actual Implementation** (both analyzers):
Uses weighted contributions with distance decay:
```python
# Actual code in both analyzers
for road in roads:
    base_weight = self.infrastructure_weights.get(road_type, 80)
    decay = np.exp(-distance_km / half_life)
    weighted_score += base_weight * decay
```

**Gap:**
- Documentation implies simple count-based scoring (>= 5 roads = 100 pts)
- Code uses sophisticated weighted distance-decay formula
- No explanation of how "raw scores" relate to "component scores"

---

## Current Implementation Analysis

### Standard Analyzer (infrastructure_analyzer.py)

**Method:** `_combine_infrastructure_analysis()` (lines ~520-600)

**Algorithm:**
1. **Distance-weighted accumulation** of raw scores per feature type
2. **Square root compression** to prevent inflation: `25 + sqrt((raw - 25) * scale)`
3. **Weighted combination** with tight caps: `min(50, road_score) * 0.5 + ...`
4. **Selective bonuses** for exceptional infrastructure (>300 raw points)
5. **Final cap** at 100 points

**Component Limits:**
- Roads: 0-25 points (base) + 0-12 (bonus) = 0-37 max
- Airports: 0-20 points (base) + 0-10 (bonus) = 0-30 max
- Railways: 0-16 points (base) + 0-8 (bonus) = 0-24 max
- **Total max:** ~91 points (realistic 30-85 range)

**Strengths:**
- ✅ Handles variable OSM feature counts well (compression prevents inflation)
- ✅ Smooth degradation with distance
- ✅ Proven to prevent 100/100 scores for average regions

**Weaknesses:**
- ❌ Complex math (sqrt compression hard to explain to non-technical users)
- ❌ Opaque relationship between "300 raw points" and "exceptional" designation

---

### Enhanced Analyzer (enhanced_infrastructure_analyzer.py)

**Method:** `_calculate_infrastructure_score()` (lines 431-525)

**Algorithm:**
1. **Direct count-based accumulation** per component type: `count * (weight / 10)`
2. **Total caps per component** (not per feature)
   - Roads: max 35 points total (all road types combined)
   - Railways: max 20 points
   - Aviation: max 20 points
   - Ports: max 15 points
   - Construction bonus: max 10 points
   - Planning bonus: max 5 points
3. **Accessibility adjustment:** ±10 points based on overall accessibility
4. **Final cap** at 100 points

**Component Limits:**
- Roads: 0-35 points (hard cap)
- Railways: 0-20 points (hard cap)
- Aviation: 0-20 points (hard cap)
- Ports: 0-15 points (hard cap)
- Construction: 0-10 points (hard cap)
- Planning: 0-5 points (hard cap)
- **Total max:** 105 points → capped at 100

**Strengths:**
- ✅ Simple to understand (count × weight, then cap)
- ✅ Predictable scoring (clear component allocations)
- ✅ Easy to audit and explain

**Weaknesses:**
- ❌ No distance decay (feature 50km away counts same as 5km away)
- ❌ Hit caps quickly in dense areas (Jakarta would max all components)
- ❌ Less nuanced than standard analyzer

---

##Recommended Solution: Unified Hybrid Approach

### Strategy: Adopt Total Caps with Distance Weighting

**Rationale:**
1. Total caps are easier to understand and audit
2. Distance weighting is essential for accurate assessment
3. Hybrid combines best of both approaches
4. Single algorithm reduces maintenance burden

### Proposed Unified Algorithm

```python
def calculate_infrastructure_score(self, region_features: Dict, bbox: Dict) -> float:
    """
    Unified infrastructure scoring with total caps and distance weighting.
    
    Philosophy: Each infrastructure component has a maximum point allocation.
    Features contribute proportionally based on distance and importance.
    """
    
    # Component point allocations (total across all features)
    MAX_ROAD_POINTS = 35
    MAX_RAILWAY_POINTS = 20
    MAX_AVIATION_POINTS = 20
    MAX_PORT_POINTS = 15
    MAX_CONSTRUCTION_POINTS = 10
    MAX_PLANNING_POINTS = 5
    
    # Distance decay parameters (half-life in km)
    DISTANCE_DECAY = {
        'highway': {'max_distance': 50, 'half_life': 15},
        'airport': {'max_distance': 100, 'half_life': 30},
        'railway': {'max_distance': 25, 'half_life': 8},
        'port': {'max_distance': 50, 'half_life': 15}
    }
    
    # Feature importance weights (base multipliers)
    FEATURE_WEIGHTS = {
        'motorway': 1.0,      # Highest priority
        'trunk': 0.9,
        'primary': 0.8,
        'secondary': 0.6,
        'tertiary': 0.4,
        'rail': 0.85,
        'subway': 0.9,
        'light_rail': 0.7,
        'airport': 1.0,
        'port': 0.9,
        'harbour': 0.8
    }
    
    # Calculate target center point
    target_center = Point(
        (bbox['west'] + bbox['east']) / 2,
        (bbox['south'] + bbox['north']) / 2
    )
    
    # === ROADS ===
    road_contribution = 0.0
    for road_type, roads in region_features['roads'].items():
        weight = FEATURE_WEIGHTS.get(road_type, 0.5)
        decay_params = DISTANCE_DECAY['highway']
        
        for road in roads:
            distance_km = calculate_distance(target_center, road)
            if distance_km <= decay_params['max_distance']:
                # Exponential distance decay
                decay = np.exp(-distance_km / decay_params['half_life'])
                # Contribution = base_weight × distance_decay × allocation_per_feature
                contribution = weight * decay * (MAX_ROAD_POINTS / 20)  # Assume ~20 roads is "full"
                road_contribution += contribution
    
    road_score = min(MAX_ROAD_POINTS, road_contribution)
    
    # === RAILWAYS ===
    railway_contribution = 0.0
    for rail_type, rails in region_features['railways'].items():
        weight = FEATURE_WEIGHTS.get(rail_type, 0.7)
        decay_params = DISTANCE_DECAY['railway']
        
        for rail in rails:
            distance_km = calculate_distance(target_center, rail)
            if distance_km <= decay_params['max_distance']:
                decay = np.exp(-distance_km / decay_params['half_life'])
                contribution = weight * decay * (MAX_RAILWAY_POINTS / 10)  # Assume ~10 lines is "full"
                railway_contribution += contribution
    
    railway_score = min(MAX_RAILWAY_POINTS, railway_contribution)
    
    # === AVIATION ===
    aviation_contribution = 0.0
    for airport in region_features['aviation']['airports']:
        distance_km = calculate_distance(target_center, airport)
        decay_params = DISTANCE_DECAY['airport']
        
        if distance_km <= decay_params['max_distance']:
            decay = np.exp(-distance_km / decay_params['half_life'])
            # Major airport contribution
            is_international = airport.get('international', False)
            base_contribution = 15 if is_international else 10
            contribution = base_contribution * decay
            aviation_contribution += contribution
    
    aviation_score = min(MAX_AVIATION_POINTS, aviation_contribution)
    
    # === PORTS ===
    port_contribution = 0.0
    for port in region_features['ports']['all']:
        distance_km = calculate_distance(target_center, port)
        decay_params = DISTANCE_DECAY['port']
        
        if distance_km <= decay_params['max_distance']:
            decay = np.exp(-distance_km / decay_params['half_life'])
            weight = FEATURE_WEIGHTS.get(port['type'], 0.8)
            contribution = weight * decay * (MAX_PORT_POINTS / 5)  # Assume ~5 ports is "full"
            port_contribution += contribution
    
    port_score = min(MAX_PORT_POINTS, port_contribution)
    
    # === CONSTRUCTION & PLANNING ===
    construction_count = len(region_features.get('construction_projects', []))
    construction_score = min(MAX_CONSTRUCTION_POINTS, construction_count * 2)
    
    planning_count = len(region_features.get('planned_projects', []))
    planning_score = min(MAX_PLANNING_POINTS, planning_count * 1)
    
    # === FINAL SCORE ===
    base_score = (
        road_score +           # 0-35
        railway_score +        # 0-20
        aviation_score +       # 0-20
        port_score +           # 0-15
        construction_score +   # 0-10
        planning_score         # 0-5
    )  # Max: 105 points
    
    # Accessibility adjustment (±10 points)
    accessibility_data = calculate_accessibility(region_features)
    accessibility_adjustment = (accessibility_data['overall_score'] - 50) * 0.2
    
    final_score = min(100, max(0, base_score + accessibility_adjustment))
    
    return {
        'infrastructure_score': final_score,
        'component_breakdown': {
            'roads': road_score,
            'railways': railway_score,
            'aviation': aviation_score,
            'ports': port_score,
            'construction': construction_score,
            'planning': planning_score,
            'accessibility_adjustment': accessibility_adjustment
        },
        'component_max': {
            'roads': MAX_ROAD_POINTS,
            'railways': MAX_RAILWAY_POINTS,
            'aviation': MAX_AVIATION_POINTS,
            'ports': MAX_PORT_POINTS,
            'construction': MAX_CONSTRUCTION_POINTS,
            'planning': MAX_PLANNING_POINTS
        }
    }
```

### Key Improvements

1. **Unified Algorithm:** Single approach for both analyzers
2. **Total Caps:** Clear maximum points per component (prevents inflation)
3. **Distance Weighting:** Features farther away contribute less (realistic)
4. **Transparency:** Component breakdown shows exactly where points come from
5. **Simplicity:** No sqrt compression—easier to understand and audit
6. **Consistency:** Same formula whether using standard or enhanced analyzer

---

## Documentation Fixes

### Fix 1: Remove Threshold-Based Component Scoring Section

**Current (INCORRECT):**
```python
# Lines 608-693 - Component Scoring
if major_roads >= 5:
    highway_score = 100
elif major_roads >= 3:
    highway_score = 75
```

**Replacement:**
```python
# Infrastructure Component Scoring (Distance-Weighted with Total Caps)

## Roads (Max 35 Points)
road_score = 0
for road in roads_within_50km:
    distance_km = calculate_distance(target, road)
    decay = exp(-distance_km / 15)  # 15km half-life
    weight = ROAD_WEIGHTS[road.type]  # motorway=1.0, primary=0.8, etc.
    contribution = weight * decay * (35 / 20)  # Assume 20 roads = full allocation
    road_score += contribution

road_score = min(35, road_score)  # Cap at max allocation

## Railways (Max 20 Points)
railway_score = 0
for rail in railways_within_25km:
    distance_km = calculate_distance(target, rail)
    decay = exp(-distance_km / 8)  # 8km half-life
    weight = RAIL_WEIGHTS[rail.type]  # rail=0.85, subway=0.9, etc.
    contribution = weight * decay * (20 / 10)  # Assume 10 lines = full
    railway_score += contribution

railway_score = min(20, railway_score)  # Cap at max allocation

## Aviation (Max 20 Points)
aviation_score = 0
for airport in airports_within_100km:
    distance_km = calculate_distance(target, airport)
    decay = exp(-distance_km / 30)  # 30km half-life
    base_points = 15 if airport.international else 10
    contribution = base_points * decay
    aviation_score += contribution

aviation_score = min(20, aviation_score)  # Cap at max allocation

## Ports (Max 15 Points)
port_score = 0
for port in ports_within_50km:
    distance_km = calculate_distance(target, port)
    decay = exp(-distance_km / 15)  # 15km half-life
    weight = PORT_WEIGHTS[port.type]  # port=0.9, harbour=0.8
    contribution = weight * decay * (15 / 5)  # Assume 5 ports = full
    port_score += contribution

port_score = min(15, port_score)  # Cap at max allocation

## Construction Projects (Max 10 Points)
construction_score = min(10, construction_count * 2)

## Planned Projects (Max 5 Points)
planning_score = min(5, planning_count * 1)

## Final Infrastructure Score
base_score = road + railway + aviation + port + construction + planning  # Max 105
accessibility_adj = (accessibility_score - 50) * 0.2  # ±10 points
infrastructure_score = min(100, base_score + accessibility_adj)
```

### Fix 2: Consolidate Analyzer Comparison Section

**Update Lines 477-597** to reflect unified approach:

```markdown
### Infrastructure Scoring Calculation

CloudClearingAPI uses a **unified distance-weighted total caps approach** for infrastructure scoring.

#### Core Principles

1. **Total Caps:** Each component type (roads, railways, etc.) has a maximum point allocation
2. **Distance Weighting:** Features contribute more when closer to target region (exponential decay)
3. **Importance Weighting:** Different feature types have different base weights (motorway > secondary road)
4. **Transparency:** Component breakdown shows exact point allocation

#### Why This Approach?

**Previously:** Two different analyzers (standard with sqrt compression, enhanced with simple caps)
**Problem:** Inconsistent results, maintenance burden, unclear when to use which
**Solution:** Unified algorithm combining best features of both:
- Total caps (from enhanced) prevent unbounded accumulation
- Distance weighting (from standard) ensures realistic geographic impact
- Simpler than sqrt compression, more nuanced than simple counts

#### Component Point Allocations

| Component | Max Points | Typical Full Allocation | Half-Life (km) | Max Distance (km) |
|-----------|------------|------------------------|----------------|-------------------|
| Roads | 35 | ~20 major roads | 15 | 50 |
| Railways | 20 | ~10 rail lines | 8 | 25 |
| Aviation | 20 | 1-2 airports | 30 | 100 |
| Ports | 15 | ~5 ports | 15 | 50 |
| Construction | 10 | ~5 projects | N/A | Within bbox |
| Planning | 5 | ~5 projects | N/A | Within bbox |
| **Base Total** | **105** | - | - | - |
| Accessibility Adj | ±10 | - | - | - |
| **Final Max** | **100** (capped) | - | - | - |

#### Expected Score Distribution

- **Poor infrastructure (15-35):** Minimal features, distant from major infrastructure
- **Basic infrastructure (35-50):** Some regional roads, distant airports
- **Good infrastructure (50-65):** Multiple highways, rail access, regional airport
- **Excellent infrastructure (65-80):** Dense road network, major rail hub, close airport
- **World-class infrastructure (80-95):** Jakarta/Surabaya level (motorways, international airport, major port, active construction)

**Note:** Scores of 95-100 reserved for exceptional global-tier infrastructure (Singapore, Tokyo levels). Indonesian regions typically range 40-85.
```

---

## Implementation Plan

### Phase 1: Update Standard Analyzer (infrastructure_analyzer.py)

**File:** `src/core/infrastructure_analyzer.py`  
**Method:** `_combine_infrastructure_analysis()` (lines ~520-600)

**Changes:**
1. Replace sqrt compression with total caps + distance weighting
2. Use unified component limits (35/20/20/15/10/5)
3. Add component breakdown to return dict
4. Remove complex bonus logic (already included in caps)

**Test Impact:**
- Run monitoring on 5 test regions
- Compare OLD sqrt approach vs NEW caps approach
- Validate scores stay in 30-85 range for typical regions

### Phase 2: Update Enhanced Analyzer (enhanced_infrastructure_analyzer.py)

**File:** `src/core/enhanced_infrastructure_analyzer.py`  
**Method:** `_calculate_infrastructure_score()` (lines 431-525)

**Changes:**
1. Add distance weighting to existing cap-based approach
2. Align component limits with standard analyzer (currently slightly different)
3. Ensure both analyzers use identical formula
4. Add distance decay parameters

**Test Impact:**
- Compare enhanced analyzer results before/after
- Ensure parity with updated standard analyzer
- Validate multi-source data still flows correctly

### Phase 3: Update Documentation

**File:** `TECHNICAL_SCORING_DOCUMENTATION.md`

**Changes:**
1. **Remove** threshold-based component scoring (lines 608-693)
2. **Replace** with distance-weighted caps formulas (see "Fix 1" above)
3. **Consolidate** dual-analyzer comparison section (lines 477-597)
4. **Add** worked example showing exact calculation for sample region
5. **Update** version table to reflect v2.5 standardization

### Phase 4: Validation & Testing

**Tests:**
1. Unit tests: `test_infrastructure_standardization.py`
   - Verify caps enforced correctly
   - Verify distance decay formula
   - Verify component breakdown accuracy
2. Integration tests: Run full monitoring on 10 regions
   - Compare v2.4.1 (current) vs v2.5 (standardized)
   - Ensure no regions score >90 (Jakarta exception allowed)
   - Validate score distribution matches expected ranges
3. Documentation review: Ensure all formulas match code

---

## Expected Outcomes

### Benefits

1. **Consistency:** Single algorithm across all infrastructure analysis
2. **Maintainability:** One place to fix bugs, not two
3. **Transparency:** Clear component breakdown (roads=25, railways=15, etc.)
4. **Accuracy:** Distance weighting reflects real-world geographic impact
5. **Simplicity:** No complex sqrt compression math
6. **Documentation Alignment:** Code matches docs exactly

### Risks & Mitigations

**Risk 1:** Changing scoring may invalidate historical comparisons  
**Mitigation:** Version results as v2.5, maintain v2.4.1 JSON archives for comparison

**Risk 2:** New formula may produce unexpected scores  
**Mitigation:** Extensive testing on 29 Java regions before production deployment

**Risk 3:** Distance weighting may over-penalize rural regions  
**Mitigation:** Generous max distances (50km for highways, 100km for airports) and appropriate half-lives

---

## Timeline

- **Day 1 (Oct 25):** Review and approve standardization plan
- **Day 2 (Oct 26):** Implement unified algorithm in standard analyzer
- **Day 3 (Oct 27):** Update enhanced analyzer, ensure parity
- **Day 4 (Oct 28):** Update documentation, create worked examples
- **Day 5 (Oct 29):** Testing and validation (29 Java regions)
- **Day 6 (Oct 30):** Production deployment (v2.5 release)

---

## Decision Required

**Question:** Proceed with unified total caps + distance weighting approach?

**Options:**
1. ✅ **YES - Implement standardization** (recommended)
2. ❌ NO - Keep dual approaches, improve documentation only
3. 🔄 HYBRID - Standardize formulas but keep both analyzers for different use cases

**Recommendation:** **Option 1** - The benefits of consistency outweigh the implementation effort.
