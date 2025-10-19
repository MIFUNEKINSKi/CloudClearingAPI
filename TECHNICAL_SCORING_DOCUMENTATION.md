# Technical Scoring Documentation
## CloudClearingAPI Investment Scoring System

**Version:** 2.4 (Financial Metrics Engine Integration)  
**Last Updated:** October 19, 2025  
**Author:** Chris Moore

---

## Version History

| Version | Date | Author | Changes |
| :--- | :--- | :--- | :--- |
| **2.4** | 2025-10-19 | Chris Moore | **Major Enhancement:** Integrated Financial Metrics Engine with live web scraping (Lamudi, Rumah.com) for ROI projections, land value estimation, and development cost indexing. Adds investment profitability layer parallel to development activity scores. |
| 2.3 | 2025-10-19 | Chris Moore | Enhanced Infrastructure Scoring Fix - Fixed both analyzers (standard + enhanced) with compression and strict caps |
| 2.2 | 2025-10-18 | Chris Moore | Infrastructure Scoring Fix (Initial) - Normalized component scores before combining |
| 2.1 | 2025-10-18 | Chris Moore | Tiered Multipliers - Infrastructure (0.8-1.3x) and Market (0.85-1.4x) with 5-tier system |
| 2.0 | 2025-10-06 | Chris Moore | Corrected Scoring System - Satellite data as PRIMARY component (40 points base) |

---

## Recent Updates

### Version 2.4 - October 19, 2025 (Financial Metrics Engine Integration)
**Major Enhancement:** Added parallel financial projection system with live web scraping
- **Purpose:** Translate development activity into actionable investment thesis with concrete financial metrics
- **Web Scraping System:** 3-tier cascading fallback (Live → Cache → Benchmark) for land price data
  - **Primary**: Live scraping from Lamudi.co.id and Rumah.com (85% confidence)
  - **Secondary**: Cached results if < 24-48h old (75-85% confidence)
  - **Tertiary**: Static regional benchmarks (50% confidence)
- **Financial Outputs:**
  - Land value estimates (current + 3-year projection)
  - Development cost index (0-100) based on terrain, access, clearing requirements
  - ROI projections (3-year and 5-year)
  - Investment sizing recommendations (plot size, total capital)
  - Risk assessment (liquidity, speculation, infrastructure)
- **Integration Point:** Post-scoring analysis layer in `automated_monitor.py`
- **Files Added:** 
  - `src/core/financial_metrics.py` (773 lines) - Financial projection engine
  - `src/scrapers/base_scraper.py` (380 lines) - Base scraper with caching
  - `src/scrapers/lamudi_scraper.py` (420 lines) - Lamudi.co.id scraper
  - `src/scrapers/rumah_scraper.py` (415 lines) - Rumah.com scraper
  - `src/scrapers/scraper_orchestrator.py` (390 lines) - Orchestration with fallback logic
  - `WEB_SCRAPING_DOCUMENTATION.md` (600+ lines) - Complete user guide
- **Dependencies Added**: `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`

### Version 2.3 - October 19, 2025 (Enhanced Infrastructure Scoring Fix)
**Critical Bug Fix:** Infrastructure scoring was STILL inflating scores to 100/100 despite Oct 18 fix
- **Problem:** Both `infrastructure_analyzer.py` AND `enhanced_infrastructure_analyzer.py` allowed unlimited accumulation before capping
- **Root Cause:** Oct 18 fix only addressed standard analyzer; enhanced analyzer could accumulate 270+ points before cap
- **Solution:** 
  - **Enhanced Analyzer**: Proper total caps per component type (not per-feature), reduced max allocations, additive accessibility adjustment
  - **Standard Analyzer**: Added square root compression to prevent inflation from many features, more selective bonuses
- **Impact:** Realistic score distribution (20-85 range typical, 85-95 exceptional) with clear regional differentiation
- **Files Modified:** 
  - `src/core/enhanced_infrastructure_analyzer.py` - `_calculate_infrastructure_score()` method
  - `src/core/infrastructure_analyzer.py` - `_combine_infrastructure_analysis()` method (enhanced compression)

### Version 2.2 - October 18, 2025 (Infrastructure Scoring Fix - Initial)
**Critical Bug Fix:** Infrastructure scoring was inflating all scores to 100/100
- **Problem:** Unlimited component scores (roads, airports, railways) combined with multipliers pushed all regions to 100/100
- **Solution:** Normalize component scores to 0-100 BEFORE combining, use additive bonuses instead of multiplicative multipliers
- **Impact:** Partial improvement - standard analyzer fixed, but enhanced analyzer still had issues
- **Files Modified:** `src/core/infrastructure_analyzer.py` - `_combine_infrastructure_analysis()` method

### Version 2.1 - October 18, 2025 (Tiered Multipliers)
**Enhancement:** Replaced linear multipliers with tiered system for better score separation
- **Infrastructure:** 0.8-1.2x → 0.8-1.3x with 5 clear tiers (Poor/Fair/Good/VeryGood/Excellent)
- **Market:** 0.9-1.1x → 0.85-1.4x with 5 clear tiers (Declining/Stagnant/Stable/Strong/Booming)
- **Impact:** 2-3x better score separation between good and excellent opportunities
- **Files Modified:** `src/core/corrected_scoring.py`

### Version 2.0 - October 6, 2025 (Corrected Scoring System)
**Major Refactor:** Satellite data now PRIMARY score component (was being ignored)
- Satellite development activity: 0-40 points (base score)
- Infrastructure quality: 0.8-1.2x multiplier
- Market dynamics: 0.9-1.1x multiplier
- Files: `src/core/corrected_scoring.py` (new), deprecated `speculative_scorer.py`

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Data Sources & APIs](#data-sources--apis)
4. [Scoring Algorithm](#scoring-algorithm)
5. [Component Details](#component-details)
6. [Confidence Calculation](#confidence-calculation)
7. [PDF Report Generation](#pdf-report-generation)
8. [Monitoring System](#monitoring-system)
9. [Technical Implementation](#technical-implementation)

---

## Overview

The CloudClearingAPI Investment Scoring System analyzes Indonesian regions for land development investment opportunities using satellite imagery, infrastructure data, and market intelligence. The system produces scored regions (0-100 points) with confidence ratings and detailed PDF reports.

### Key Objectives
- **Detect Development Changes**: Identify land clearing, construction, and urban expansion using Sentinel-2 satellite imagery
- **Assess Infrastructure**: Evaluate proximity and quality of roads, ports, airports, and railways
- **Calculate Investment Scores**: Combine multiple data sources into actionable investment recommendations
- **Generate Reports**: Produce executive-ready PDF reports with visualizations and recommendations

### Output Format
- **Score**: 0-100 points (weighted combination of development activity, infrastructure, market factors)
- **Confidence**: 40-95% (data quality and completeness assessment)
- **Recommendation**: BUY (>60), WATCH (40-60), PASS (<40)
- **PDF Report**: Multi-page executive summary with maps, charts, and detailed analysis

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MONITORING ORCHESTRATOR                      │
│           (run_weekly_java_monitor.py - 29 regions)             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ├─► Region Configuration (src/regions.py)
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CORRECTED SCORING SYSTEM                      │
│              (src/core/corrected_scoring.py)                     │
└──┬────────────────┬────────────────────┬───────────────────────┘
   │                │                    │
   ▼                ▼                    ▼
┌──────────┐  ┌──────────────┐  ┌─────────────────┐
│ SATELLITE│  │INFRASTRUCTURE│  │ MARKET & PRICE  │
│ ANALYSIS │  │   ANALYZER   │  │  INTELLIGENCE   │
│          │  │              │  │                 │
│ Google   │  │ OpenStreetMap│  │ Jakarta/Bali    │
│ Earth    │  │ Overpass API │  │ Price Patterns  │
│ Engine   │  │              │  │                 │
└────┬─────┘  └──────┬───────┘  └────────┬────────┘
     │               │                    │
     └───────────┬───┴──────────┬─────────┘
                 │              │
                 ▼              ▼
┌──────────────────────────┐  ┌─────────────────────────┐
│  SCORING AGGREGATION     │  │ FINANCIAL PROJECTION    │
│  (Calculates 0-100 Score)│  │ ENGINE (ROI, Land Value)│
│                          │  │                         │
│  Base (0-40) ×           │  │ • Web Scraping (Live)  │
│  Infrastructure (0.8-1.3x)│  │ • Cache (24-48h)       │
│  Market (0.85-1.4x)      │  │ • Benchmarks (Fallback)│
└────────────┬─────────────┘  └────────────┬────────────┘
             │                             │
             └─────────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PDF REPORT GENERATOR                           │
│         (src/core/pdf_report_generator.py)                       │
│                                                                  │
│  • Executive Summary with Recommendations                        │
│  • Infrastructure Breakdown (ports, roads, airports)            │
│  • Development Activity Analysis (land clearing, construction)  │
│  • Confidence Breakdown & Data Quality Assessment               │
│  • Satellite Imagery Visualization (5 images per region)        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Monitoring Orchestrator**: Coordinates analysis across multiple regions
2. **Corrected Scoring System**: Central scoring engine (satellite-centric approach)
3. **Satellite Analysis**: Google Earth Engine for change detection
4. **Infrastructure Analyzer**: OSM/Overpass API for infrastructure data
5. **Market Intelligence**: Price trend analysis and market context
6. **PDF Generator**: Executive report creation with visualizations

---

## Data Sources & APIs

### 1. Google Earth Engine (Satellite Imagery)

**API:** `earthengine-api` Python package  
**Authentication:** Service account JSON key file  
**Data Source:** Sentinel-2 MultiSpectral Instrument (MSI)  

#### Sentinel-2 Specifications
- **Spatial Resolution**: 10m (RGB + NIR), 20m (Red Edge, SWIR)
- **Temporal Resolution**: 5-day revisit time
- **Spectral Bands Used**:
  - B2 (Blue): 490nm
  - B3 (Green): 560nm  
  - B4 (Red): 665nm
  - B8 (NIR): 842nm
  - B11 (SWIR1): 1610nm
  - B12 (SWIR2): 2190nm

#### Cloud Filtering
```python
# Filter criteria applied to all Sentinel-2 queries
- Cloud Coverage: < 20% (CLOUDY_PIXEL_PERCENTAGE)
- Time Period: 7-day windows
- Image Selection: Median composite to reduce noise
```

#### Analysis Periods
- **Historical Baseline**: 7 days ago to 14 days ago
- **Current Period**: Today to 7 days ago
- **Comparison**: Current vs Historical pixel-by-pixel analysis

### 2. OpenStreetMap via Overpass API

**Endpoint:** `https://overpass-api.de/api/interpreter`  
**Data Format:** JSON  
**Update Frequency:** Real-time (community-maintained)  

#### Infrastructure Queries

**Highways (Major Roads)**:
```overpass
[out:json][timeout:30];
(
  way["highway"~"motorway|trunk|primary"](around:RADIUS, LAT, LON);
);
out geom;
```
- **Categories**: Motorways, trunk roads, primary highways
- **Search Radius**: 25km from region center
- **Data Returned**: Road geometries, names, types

**Ports**:
```overpass
[out:json][timeout:30];
(
  node["harbour"="yes"](around:RADIUS, LAT, LON);
  way["harbour"="yes"](around:RADIUS, LAT, LON);
  node["amenity"="ferry_terminal"](around:RADIUS, LAT, LON);
);
out body;
```
- **Types**: Harbours, ferry terminals, industrial ports
- **Radius**: 50km from region center
- **Distance Calculation**: Haversine formula to region centroid

**Railways**:
```overpass
[out:json][timeout:30];
(
  way["railway"~"rail|light_rail|subway"](around:RADIUS, LAT, LON);
);
out geom;
```
- **Types**: Heavy rail, light rail, subway/metro
- **Radius**: 25km from region center
- **Analysis**: Total length, station count

**Airports**:
```overpass
[out:json][timeout:30];
(
  way["aeroway"="aerodrome"](around:RADIUS, LAT, LON);
  node["aeroway"="aerodrome"](around:RADIUS, LAT, LON);
);
out body;
```
- **Radius**: 100km from region center
- **Classification**: International, domestic, regional
- **Distance Sorting**: Nearest airports prioritized

**Construction Projects**:
```overpass
[out:json][timeout:30];
(
  way["construction"](around:RADIUS, LAT, LON);
  way["highway"="construction"](around:RADIUS, LAT, LON);
);
out geom;
```
- **Types**: Road construction, building construction
- **Radius**: 15km from region center
- **Status**: Active construction sites

#### Data Confidence Levels
- **OSM Live Data (85% confidence)**: Direct query returns infrastructure data
- **Regional Fallback (50-60% confidence)**: Known region patterns when OSM incomplete
- **No Data (30% confidence)**: Unknown region with no infrastructure information

### 3. Market & Price Intelligence

**Source:** Internal price database (`src/core/price_intelligence.py`)  
**Reference Markets**: Jakarta, Bali (established benchmarks)  

#### Price Analysis Components
- **Land Price Trends**: Historical appreciation rates
- **Development Stage**: Emerging vs established markets
- **Speculation Risk**: Price volatility assessment
- **Market Momentum**: Recent transaction patterns

#### Confidence Scoring
- **High Confidence (>85%)**: Multiple recent transactions, stable market
- **Medium Confidence (70-85%)**: Limited transaction data, some market indicators
- **Low Confidence (<70%)**: Speculative market, insufficient data

---

## Scoring Algorithm

### Core Formula

```python
final_score = (
    base_development_score      # 0-40 points (satellite analysis)
    × infrastructure_multiplier  # 0.8-1.2x (OSM data)
    × market_multiplier          # 0.9-1.1x (price intelligence)
    × confidence_multiplier      # 0.7-1.0x (data quality)
)
```

### 1. Base Development Score (0-40 points)

**Source:** Satellite change detection  
**Weight:** PRIMARY (100% of base score)

#### Calculation Method

```python
# Step 1: Detect Changes
changes = detect_pixel_changes(
    historical_composite,  # 14-7 days ago
    current_composite,     # 7-0 days ago
    thresholds={
        'ndvi_decrease': -0.15,      # Vegetation loss
        'ndbi_increase': 0.10,       # Built-up area increase
        'brightness_increase': 0.15  # Bare earth increase
    }
)

# Step 2: Calculate Raw Score
raw_score = (
    vegetation_loss_pixels × 1.5 +      # High weight (land clearing)
    built_up_increase_pixels × 2.0 +    # Highest weight (construction)
    bare_earth_pixels × 1.0             # Medium weight (preparation)
) / region_area_km2

# Step 3: Normalize to 0-40
base_score = min(40, raw_score / normalization_factor)
```

#### Change Detection Indices

**NDVI (Normalized Difference Vegetation Index)**:
```python
NDVI = (NIR - Red) / (NIR + Red)
# Detects: Vegetation loss (forest clearing, agricultural conversion)
# Threshold: Decrease > 0.15 indicates significant vegetation removal
```

**NDBI (Normalized Difference Built-up Index)**:
```python
NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
# Detects: Urban expansion, building construction
# Threshold: Increase > 0.10 indicates new development
```

**Brightness Change**:
```python
Brightness = (Red + Green + Blue) / 3
# Detects: Bare earth, soil exposure, land preparation
# Threshold: Increase > 0.15 indicates land clearing
```

#### Activity Type Classification

```python
if ndvi_decrease > 0.15 and ndbi_increase < 0.05:
    activity_type = "Land Clearing (Vegetation Removal)"
    weight = 1.5

elif ndbi_increase > 0.10:
    activity_type = "Active Construction (Building Development)"
    weight = 2.0

elif brightness_increase > 0.15:
    activity_type = "Land Preparation (Bare Earth Exposure)"
    weight = 1.0

elif ndvi_decrease > 0.10 and agricultural_pattern:
    activity_type = "Agricultural Conversion"
    weight = 1.2
```

### 2. Infrastructure Multiplier (0.8-1.3x)

**Source:** OpenStreetMap infrastructure analysis  
**Weight:** SECONDARY (±20-30% adjustment to base score)

#### 🆕 Tiered Multiplier System

Instead of linear scaling, we use tiers to create meaningful separation:

```python
# Tiered Infrastructure Multipliers
if infrastructure_score >= 90:
    multiplier = 1.30  # Excellent - World-class infrastructure
elif infrastructure_score >= 75:
    multiplier = 1.15  # Very Good - Strong infrastructure  
elif infrastructure_score >= 60:
    multiplier = 1.00  # Good - Adequate infrastructure
elif infrastructure_score >= 40:
    multiplier = 0.90  # Fair - Basic infrastructure
else:
    multiplier = 0.80  # Poor - Weak infrastructure
```

**Impact Example:**
- Base score 30 with Excellent infrastructure (95): 30 × 1.30 = 39 points
- Base score 30 with Poor infrastructure (35): 30 × 0.80 = 24 points
- **Spread: 15 points** (vs 4 points with old linear system)

#### Calculation Method

**🔧 CRITICAL FIX (Oct 19, 2025):** Infrastructure scoring was STILL inflating to 100/100 despite initial Oct 18 fix. The system now uses TWO complementary approaches:

#### **Approach 1: Standard Infrastructure Analyzer** (`infrastructure_analyzer.py`)

Uses **square root compression** to prevent score inflation from regions with many features:

```python
import math

# Step 1: Apply Square Root Compression to Raw Scores
# This compresses high values while preserving differences at lower ranges
def compress_score(raw_score, scale=200):
    if raw_score < 25:
        return raw_score  # Linear below 25
    return 25 + math.sqrt((raw_score - 25) * scale)

# Apply compression with different scales based on importance
road_score = compress_score(raw_road_score, 180)      # Less compression (more important)
airport_score = compress_score(raw_airport_score, 120)
railway_score = compress_score(raw_railway_score, 100)

# Step 2: Weighted Combination with Tighter Caps
base_score = (
    min(50, road_score) * 0.5 +      # Roads: 0-25 points
    min(45, airport_score) * 0.45 +  # Airports: 0-20 points
    min(40, railway_score) * 0.4     # Railways: 0-16 points
)  # Maximum base: ~61 points

# Step 3: More Selective Bonuses (only reward exceptional infrastructure)
accessibility_bonus = 0
if raw_road_score > 300:  # Exceptional road network
    accessibility_bonus = 12
elif raw_road_score > 200:  # Excellent
    accessibility_bonus = 7
elif raw_road_score > 100:  # Good
    accessibility_bonus = 3

aviation_bonus = 0
if raw_airport_score > 100:  # Major international airport
    aviation_bonus = 10
elif raw_airport_score > 60:  # Regional airport
    aviation_bonus = 5
elif raw_airport_score > 30:  # Moderate access
    aviation_bonus = 2

railway_bonus = 0
if raw_railway_score > 150:  # Major rail hub
    railway_bonus = 8
elif raw_railway_score > 80:  # Good connectivity
    railway_bonus = 4
elif raw_railway_score > 40:  # Basic access
    railway_bonus = 2

# Step 4: Final Score (capped at 100)
# Typical range: 30-85, exceptional: 85-100
infrastructure_score = min(100, base_score + accessibility_bonus + aviation_bonus + railway_bonus)
```

**Expected Distribution (Standard Analyzer):**
- Poor infrastructure: 15-35
- Basic infrastructure: 35-50
- Good infrastructure: 50-65
- Excellent infrastructure: 65-80
- World-class infrastructure: 80-95

#### **Approach 2: Enhanced Infrastructure Analyzer** (`enhanced_infrastructure_analyzer.py`)

Uses **proper total caps per component type** instead of per-feature caps:

```python
# Step 1: Score Components with TOTAL Caps (not per-feature)
road_score = 0
for road_type, roads in processed['roads'].items():
    contribution = count * (weight / 10)
    road_score += contribution
road_score = min(35, road_score)  # Cap TOTAL road contribution (not per type)

railway_score = 0
for rail_type, rails in processed['railways'].items():
    contribution = count * (weight / 10)
    railway_score += contribution
railway_score = min(20, railway_score)  # Cap TOTAL railway contribution

aviation_score = min(20, (airports * 15) + (runways * 3))  # Reduced from 25
port_score = min(15, ports * 10)  # Reduced from 20
construction_bonus = min(10, construction_projects * 3)  # Reduced from 25
planning_bonus = min(5, planned_projects * 2)  # Reduced from 20

# Step 2: Calculate Base Score
base_score = road_score + railway_score + aviation_score + port_score + construction_bonus + planning_bonus
# Maximum possible: 35 + 20 + 20 + 15 + 10 + 5 = 105 points

# Step 3: Accessibility Adjustment (additive, not multiplicative)
# Changed from multiplier (1.35x) to adjustment (±10 points)
accessibility_adjustment = (accessibility_data['overall_accessibility'] - 50) * 0.2
# Range: -10 to +10 points

# Step 4: Final Score
infrastructure_score = min(100, max(0, base_score + accessibility_adjustment))
```

**Expected Distribution (Enhanced Analyzer):**
- Poor infrastructure: 20-40
- Basic infrastructure: 40-55
- Good infrastructure: 55-70
- Excellent infrastructure: 70-85
- World-class infrastructure: 85-100

#### **Why Two Approaches?**

1. **Standard Analyzer**: Used when querying live OSM data - compression handles variable feature counts
2. **Enhanced Analyzer**: Used for comprehensive multi-source analysis - strict caps prevent accumulation

Both ensure realistic score distributions with clear differentiation between regions.

#### **Step 5: Convert to Tiered Multiplier**

Once the infrastructure score is calculated (0-100), convert to multiplier:

```python
# Tiered Infrastructure Multipliers
if infrastructure_score >= 90:
    multiplier = 1.30  # World-class
elif infrastructure_score >= 75:
    multiplier = 1.15  # Excellent
elif infrastructure_score >= 60:
    multiplier = 1.00  # Good
elif infrastructure_score >= 40:
    multiplier = 0.90  # Fair
else:
    multiplier = 0.80  # Poor
```

#### Component Scoring

**Highway Score (0-100)**:
```python
major_roads = count_highways_within_25km(region)

if major_roads >= 5:
    highway_score = 100
elif major_roads >= 3:
    highway_score = 75
elif major_roads >= 1:
    highway_score = 50
else:
    highway_score = 25
```

**Port Score (0-100)**:
```python
nearest_port_km = distance_to_nearest_port(region)

if nearest_port_km < 10:
    port_score = 100  # Direct port access
elif nearest_port_km < 25:
    port_score = 75   # Close proximity
elif nearest_port_km < 50:
    port_score = 50   # Regional access
else:
    port_score = 25   # Distant/no access
```

**Railway Score (0-100)**:
```python
railway_length_km = total_railway_within_25km(region)

if railway_length_km > 20:
    railway_score = 100
elif railway_length_km > 10:
    railway_score = 75
elif railway_length_km > 5:
    railway_score = 50
else:
    railway_score = 25
```

**Airport Score (0-100)**:
```python
airports = find_airports_within_100km(region)
nearest_airport_km = min([a.distance for a in airports])

if nearest_airport_km < 25 and has_international:
    airport_score = 100
elif nearest_airport_km < 50:
    airport_score = 75
elif nearest_airport_km < 100:
    airport_score = 50
else:
    airport_score = 25
```

**Construction Score (0-100)**:
```python
construction_projects = count_active_construction(region)

if construction_projects >= 10:
    construction_score = 100  # High development momentum
elif construction_projects >= 5:
    construction_score = 75
elif construction_projects >= 2:
    construction_score = 50
else:
    construction_score = 25
```

### 3. Market Multiplier (0.85-1.4x)

**Source:** Price intelligence and market analysis  
**Weight:** TERTIARY (±15-40% adjustment to base score)

#### 🆕 Tiered Multiplier System

Rewards exceptional markets significantly while penalizing stagnation:

```python
# Tiered Market Multipliers
if price_trend >= 15:
    multiplier = 1.40  # Booming - Exceptional growth (>15%/year)
elif price_trend >= 8:
    multiplier = 1.20  # Strong - Very strong market (8-15%/year)
elif price_trend >= 2:
    multiplier = 1.00  # Stable - Healthy growth (2-8%/year)
elif price_trend >= 0:
    multiplier = 0.95  # Stagnant - Slow growth (0-2%/year)
else:
    multiplier = 0.85  # Declining - Market decline (<0%/year)
```

**Impact Example:**
- Base score 30 with Booming market (18%): 30 × 1.40 = 42 points
- Base score 30 with Declining market (-3%): 30 × 0.85 = 25.5 points
- **Spread: 16.5 points** (vs 6 points with old linear system)

#### Calculation Method

```python
# Step 1: Calculate Market Score (0-100)
market_score = (
    price_trend_score * 0.40 +        # 40% weight (appreciation)
    liquidity_score * 0.30 +          # 30% weight (transaction volume)
    speculation_risk_score * 0.20 +   # 20% weight (stability)
    benchmark_comparison_score * 0.10 # 10% weight (relative value)
)

# Step 2: Convert to Tiered Multiplier
# See tier table above
```

#### Market Analysis Components

**Price Trend Score**:
- Strong upward trend (>20% annual): 100 points
- Moderate growth (10-20% annual): 75 points
- Stable (<10% growth): 50 points
- Declining: 25 points

**Liquidity Score**:
- High transaction volume: 100 points
- Moderate transactions: 75 points
- Limited transactions: 50 points
- Speculative/illiquid: 25 points

**Speculation Risk**:
- Low volatility, established market: 100 points
- Moderate volatility: 75 points
- High volatility: 50 points
- Bubble risk: 25 points

### 4. Confidence Multiplier (0.7-1.0x)

**Source:** Data quality assessment across all sources  
**Weight:** QUALITY ADJUSTMENT (reduces score for low confidence)

#### Calculation Method

```python
# Step 1: Aggregate Component Confidences
satellite_confidence = calculate_satellite_confidence(
    cloud_cover,
    image_count,
    temporal_coverage
)  # Typically 80-95%

infrastructure_confidence = osm_data_confidence
# OSM Live: 85%, Regional Fallback: 50-60%, No Data: 30%

market_confidence = calculate_market_confidence(
    data_recency,
    transaction_count,
    price_volatility
)  # Typically 60-90%

# Step 2: Weighted Average
overall_confidence = (
    satellite_confidence * 0.50 +      # 50% weight (primary data)
    infrastructure_confidence * 0.30 + # 30% weight (context)
    market_confidence * 0.20           # 20% weight (validation)
)

# Step 3: Apply Quality Rewards/Penalties
if market_confidence > 0.85:
    overall_confidence *= 1.05  # +5% bonus for excellent market data

if infrastructure_confidence > 0.85:
    overall_confidence *= 1.05  # +5% bonus for excellent infrastructure data

if overall_confidence < 0.70:
    overall_confidence *= 0.95  # -5% penalty for poor data quality

# Step 4: Convert to Multiplier
confidence_multiplier = 0.7 + (overall_confidence - 0.5) * 0.6
# Range: 0.7x (50% confidence) to 1.0x (100% confidence)
```

#### Confidence Level Interpretation

- **90-100%**: Excellent data quality, all sources available, recent data
- **80-89%**: Good data quality, minor gaps, mostly recent data
- **70-79%**: Adequate data quality, some gaps, mixed data recency
- **60-69%**: Limited data quality, significant gaps, older data
- **40-59%**: Poor data quality, major gaps, very limited data
- **<40%**: Insufficient data, satellite-only analysis, high uncertainty

---

## Financial Projection Engine

While the core scoring algorithm quantifies development *activity*, the **Financial Projection Engine** translates this activity into an actionable investment thesis. It uses live and benchmark data to estimate land values, development costs, and potential return on investment (ROI).

### Key Outputs (`FinancialProjection` Object)

- **Land Value Estimates**: Current and projected future land value per square meter (IDR/m²)
- **Development Costs**: An index (0-100) and estimated cost based on terrain, road access, and clearing requirements
- **ROI Projections**: 3-year and 5-year ROI estimates with break-even timeline
- **Investment Sizing**: Recommended plot size and total capital outlay based on development stage
- **Risk Assessment**: Scores for liquidity risk, speculation risk, and infrastructure risk

### Web Scraping System

To provide the most accurate land value estimates, the engine uses a dynamic web scraping system with a cascading fallback architecture that ensures **100% availability** while maximizing data freshness.

**Cascading Priority Logic:**

1. **Priority 1: Live Scraping** - Attempts to pull real-time land price data from `Lamudi.co.id` and `Rumah.com`
   - **Confidence:** 85%
   - **Latency:** 5-10 seconds
   - **Data Sources:** Top 20 listings from each site, averaged
   
2. **Priority 2: Cached Results** - If a successful scrape occurred within the last 24-48 hours, cached data is used
   - **Confidence:** 75-85% (depending on cache age)
   - **Latency:** <100ms
   - **Cache Location:** `output/scraper_cache/`
   
3. **Priority 3: Static Benchmarks** - If live scraping and caching both fail, falls back to regional price benchmarks
   - **Confidence:** 50%
   - **Latency:** <10ms
   - **Coverage:** 6 Indonesian regions (Jakarta, Bali, Yogyakarta, Surabaya, Bandung, Semarang)

**Scraper Architecture:**

```
LandPriceOrchestrator
├─► LamudiScraper (try first)
│   ├─► Check cache (if < 24-48h old)
│   └─► Live scrape (if cache miss/expired)
│
├─► RumahComScraper (try if Lamudi fails)
│   ├─► Check cache
│   └─► Live scrape
│
└─► Regional Benchmarks (guaranteed fallback)
```

**Implementation:** See `WEB_SCRAPING_DOCUMENTATION.md` for complete technical details on scraper architecture, cache management, and configuration.

### Financial Calculation Formulas

**1. Land Value Estimation:**
```python
base_value = get_regional_benchmark(region)  # From web scraping or benchmark
infra_adjustment = infrastructure_multiplier  # 0.75-1.40x based on connectivity
market_adjustment = market_heat_multiplier   # 0.80-1.20x based on market conditions
estimated_value = base_value × infra_adjustment × market_adjustment
```

**2. Development Cost Index:**
```python
dev_cost_index = (
    terrain_difficulty × 0.5 +    # Slope, vegetation density
    road_distance_score × 0.3 +   # Proximity to major roads
    land_clearing_pct × 0.2       # Vegetation removal requirements
)  # Result: 0-100 (higher = more expensive)
```

**3. ROI Calculation:**
```python
appreciation_rate = (
    regional_historical_rate × 0.6 +
    current_market_trend × 0.4 +
    development_momentum_boost    # From satellite activity
)

future_value = current_value × (1 + appreciation_rate) ^ years
total_investment = acquisition_cost + development_cost
roi = (future_value - total_investment) / total_investment
```

**4. Break-Even Timeline:**
```python
break_even_years = log(total_investment / current_value) / log(1 + appreciation_rate)
```

### Integration with Scoring System

The financial engine runs as a **post-scoring analysis layer** using outputs from the three core analyzers:

**Input Data Flow:**
```python
# From Satellite Analysis
satellite_data = {
    'vegetation_loss_pixels': region_data['change_count'] // 2,
    'construction_activity_pct': development_score × 0.2
}

# From Infrastructure Analysis
infrastructure_data = {
    'infrastructure_score': corrected_result.infrastructure_score,
    'major_features': corrected_result.data_sources['infrastructure'],
    'data_confidence': corrected_result.confidence_level
}

# From Market Intelligence
market_data = {
    'price_trend_30d': corrected_result.price_trend_30d,
    'market_heat': corrected_result.market_heat,
    'data_confidence': corrected_result.confidence_level
}

# Calculate Financial Projection
financial_projection = financial_engine.calculate_financial_projection(
    region_name=region_name,
    satellite_data=satellite_data,
    infrastructure_data=infrastructure_data,
    market_data=market_data,
    scoring_result=corrected_result
)
```

**Output Structure:**
```python
FinancialProjection(
    region_name="Sleman North",
    current_land_value_per_m2=5_692_500,      # IDR (live scraped or benchmark)
    estimated_future_value_per_m2=8_257_381,   # IDR (3-year projection)
    appreciation_rate_annual=0.132,             # 13.2%
    development_cost_index=50.0,                # 0-100 scale
    estimated_dev_cost_per_m2=450_000,          # IDR
    terrain_difficulty="Moderate",
    projected_roi_3yr=0.344,                    # 34.4%
    projected_roi_5yr=0.723,                    # 72.3%
    break_even_years=0.6,
    recommended_plot_size_m2=2_000,
    total_acquisition_cost=11_385_000_000,      # IDR (11.38B)
    total_development_cost=900_000_000,         # IDR (900M)
    projected_exit_value=16_514_761_856,        # IDR (16.51B)
    liquidity_risk="Medium",
    speculation_risk="Low",
    infrastructure_risk="Low",
    projection_confidence=0.82,
    data_sources=['satellite_sentinel2', 'lamudi', 'openstreetmap']
)
```

### Regional Benchmarks (Fallback Data)

| Region | Price (IDR/m²) | Historical Appreciation | Market Liquidity |
|--------|----------------|-------------------------|------------------|
| Jakarta | 8,500,000 | 15% annual | High |
| Bali | 12,000,000 | 20% annual | High |
| Yogyakarta | 4,500,000 | 12% annual | Moderate |
| Surabaya | 6,500,000 | 14% annual | High |
| Bandung | 5,000,000 | 13% annual | Moderate |
| Semarang | 3,500,000 | 11% annual | Moderate |

**Note:** These benchmarks are used only when live scraping and cache both fail. They represent conservative mid-market estimates for each region.

---

## Component Details

### Satellite Change Detection Engine

**File:** `src/core/change_detector.py`  
**Primary Function:** `analyze_region_changes(region, start_date, end_date)`

#### Process Flow

```python
# 1. Region Setup
region_geometry = ee.Geometry.Polygon(region.coordinates)
region_area_km2 = calculate_area(region_geometry)

# 2. Image Collection
historical_images = (
    ee.ImageCollection('COPERNICUS/S2_SR')
    .filterBounds(region_geometry)
    .filterDate(start_date - 7_days, start_date)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
)

current_images = (
    ee.ImageCollection('COPERNICUS/S2_SR')
    .filterBounds(region_geometry)
    .filterDate(start_date, end_date)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
)

# 3. Composite Creation (Median)
historical_composite = historical_images.median().clip(region_geometry)
current_composite = current_images.median().clip(region_geometry)

# 4. Index Calculation
def calculate_indices(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
    ndbi = image.normalizedDifference(['B11', 'B8']).rename('ndbi')
    brightness = image.select(['B4', 'B3', 'B2']).reduce(ee.Reducer.mean()).rename('brightness')
    return image.addBands([ndvi, ndbi, brightness])

historical_indices = calculate_indices(historical_composite)
current_indices = calculate_indices(current_composite)

# 5. Change Detection
ndvi_change = current_indices.select('ndvi').subtract(historical_indices.select('ndvi'))
ndbi_change = current_indices.select('ndbi').subtract(historical_indices.select('ndbi'))
brightness_change = current_indices.select('brightness').subtract(historical_indices.select('brightness'))

# 6. Threshold Application
vegetation_loss = ndvi_change.lt(-0.15)  # NDVI decreased significantly
built_up_increase = ndbi_change.gt(0.10)  # NDBI increased significantly
bare_earth = brightness_change.gt(0.15)  # Brightness increased significantly

# 7. Change Mask
change_mask = vegetation_loss.Or(built_up_increase).Or(bare_earth)

# 8. Pixel Counting
change_stats = change_mask.reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=region_geometry,
    scale=10,  # 10m resolution
    maxPixels=1e9
)

total_change_pixels = change_stats.get('change_mask').getInfo()
total_change_area_km2 = (total_change_pixels * 100) / 1_000_000  # 10m pixels = 100m²

# 9. Score Calculation
base_score = min(40, (total_change_area_km2 / region_area_km2) * 100 * 4)
```

#### Satellite Data Confidence

```python
def calculate_satellite_confidence(historical_images, current_images, cloud_cover):
    # Image count confidence
    hist_count = historical_images.size().getInfo()
    curr_count = current_images.size().getInfo()
    
    if hist_count >= 3 and curr_count >= 3:
        count_confidence = 1.0
    elif hist_count >= 2 and curr_count >= 2:
        count_confidence = 0.9
    elif hist_count >= 1 and curr_count >= 1:
        count_confidence = 0.8
    else:
        count_confidence = 0.6
    
    # Cloud cover confidence
    avg_cloud_cover = (cloud_cover_historical + cloud_cover_current) / 2
    if avg_cloud_cover < 10:
        cloud_confidence = 1.0
    elif avg_cloud_cover < 20:
        cloud_confidence = 0.9
    elif avg_cloud_cover < 30:
        cloud_confidence = 0.8
    else:
        cloud_confidence = 0.7
    
    # Combined
    satellite_confidence = (count_confidence * 0.6 + cloud_confidence * 0.4)
    return satellite_confidence  # Typically 0.80-0.95
```

### Infrastructure Analysis Engine

**File:** `src/core/infrastructure_analyzer.py`  
**Primary Function:** `analyze_infrastructure(region)`

#### OSM Query Process

```python
def query_overpass_api(query, timeout=30):
    """
    Execute Overpass API query with retry logic and error handling
    """
    endpoint = "https://overpass-api.de/api/interpreter"
    
    for attempt in range(3):  # 3 retry attempts
        try:
            response = requests.post(
                endpoint,
                data={'data': query},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            if attempt == 2:
                logging.warning(f"OSM query timeout after {attempt+1} attempts")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
        
        except requests.exceptions.RequestException as e:
            logging.error(f"OSM query failed: {e}")
            return None
    
    return None
```

#### Infrastructure Data Processing

```python
def analyze_infrastructure(region):
    lat, lon = region.center_lat, region.center_lon
    
    # Query all infrastructure types
    highways = query_highways(lat, lon, radius_km=25)
    ports = query_ports(lat, lon, radius_km=50)
    railways = query_railways(lat, lon, radius_km=25)
    airports = query_airports(lat, lon, radius_km=100)
    construction = query_construction(lat, lon, radius_km=15)
    
    # Determine data source and confidence
    has_osm_data = bool(highways or ports or railways or airports or construction)
    
    if has_osm_data:
        data_source = 'osm_live'
        data_confidence = 0.85
    elif region.name in KNOWN_REGIONS:
        # Use regional fallback patterns
        data_source = 'regional_fallback'
        data_confidence = 0.60
    else:
        data_source = 'no_data'
        data_confidence = 0.30
    
    # Calculate component scores
    highway_score = score_highways(highways)
    port_score = score_ports(ports, lat, lon)
    railway_score = score_railways(railways)
    airport_score = score_airports(airports, lat, lon)
    construction_score = score_construction(construction)
    
    # Aggregate infrastructure score
    infrastructure_score = (
        highway_score * 0.30 +
        port_score * 0.25 +
        railway_score * 0.20 +
        airport_score * 0.15 +
        construction_score * 0.10
    )
    
    return {
        'infrastructure_score': infrastructure_score,
        'data_source': data_source,
        'data_confidence': data_confidence,
        'highways': highways,
        'ports': ports,
        'railways': railways,
        'airports': airports,
        'construction_projects': construction,
        'breakdown': {
            'highway_score': highway_score,
            'port_score': port_score,
            'railway_score': railway_score,
            'airport_score': airport_score,
            'construction_score': construction_score
        }
    }
```

#### Distance Calculation (Haversine Formula)

```python
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points on Earth in kilometers
    """
    R = 6371  # Earth radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c
```

### Market Intelligence Engine

**File:** `src/core/price_intelligence.py`  
**Primary Function:** `analyze_market_context(region)`

#### Reference Market Database

```python
REFERENCE_MARKETS = {
    'jakarta': {
        'avg_price_per_m2': 8_500_000,  # IDR
        'annual_appreciation': 0.15,     # 15%
        'liquidity': 'high',
        'transaction_volume': 'very_high'
    },
    'bali': {
        'avg_price_per_m2': 12_000_000,  # IDR
        'annual_appreciation': 0.20,     # 20%
        'liquidity': 'high',
        'transaction_volume': 'high'
    },
    'yogyakarta': {
        'avg_price_per_m2': 4_500_000,   # IDR
        'annual_appreciation': 0.12,     # 12%
        'liquidity': 'moderate',
        'transaction_volume': 'moderate'
    }
}
```

#### Market Score Calculation

```python
def analyze_market_context(region):
    # Find nearest reference market
    reference_market = find_nearest_reference(region)
    
    # Calculate price positioning
    price_ratio = region.avg_price / reference_market['avg_price_per_m2']
    
    if price_ratio < 0.4:
        price_score = 100  # Significantly undervalued
    elif price_ratio < 0.6:
        price_score = 85   # Undervalued
    elif price_ratio < 0.8:
        price_score = 70   # Fair value
    else:
        price_score = 50   # At or above market
    
    # Appreciation potential
    appreciation_score = min(100, reference_market['annual_appreciation'] * 500)
    
    # Liquidity assessment
    liquidity_map = {'very_high': 100, 'high': 85, 'moderate': 70, 'low': 50}
    liquidity_score = liquidity_map.get(reference_market['liquidity'], 50)
    
    # Aggregate market score
    market_score = (
        price_score * 0.40 +
        appreciation_score * 0.40 +
        liquidity_score * 0.20
    )
    
    # Determine confidence based on data recency and completeness
    if region.last_transaction_date within 90 days:
        market_confidence = 0.90
    elif region.last_transaction_date within 180 days:
        market_confidence = 0.75
    elif region.has_price_estimate:
        market_confidence = 0.60
    else:
        market_confidence = 0.40
    
    return {
        'market_score': market_score,
        'market_confidence': market_confidence,
        'reference_market': reference_market['name'],
        'price_positioning': price_ratio,
        'appreciation_potential': reference_market['annual_appreciation']
    }
```

---

## Confidence Calculation

### Overall Confidence Formula

```python
def calculate_overall_confidence(satellite_conf, infrastructure_conf, market_conf):
    # Weighted average (satellite is most important)
    base_confidence = (
        satellite_conf * 0.50 +         # Satellite: 50% weight
        infrastructure_conf * 0.30 +    # Infrastructure: 30% weight
        market_conf * 0.20              # Market: 20% weight
    )
    
    # Apply quality rewards (additive bonuses)
    if market_conf > 0.85:
        base_confidence *= 1.05         # +5% bonus
    
    if infrastructure_conf > 0.85:
        base_confidence *= 1.05         # +5% bonus
    
    # Apply quality penalties
    if base_confidence < 0.70:
        base_confidence *= 0.95         # -5% penalty
    
    # Clamp to valid range
    final_confidence = max(0.40, min(0.95, base_confidence))
    
    return final_confidence
```

### Confidence Ranges & Meaning

| Range | Category | Interpretation | Typical Scenario |
|-------|----------|----------------|------------------|
| 90-95% | Excellent | All data sources available, recent, high quality | Jakarta/Surabaya with full OSM data |
| 80-89% | Good | Most data sources available, recent | Established regions with good coverage |
| 70-79% | Adequate | Some data gaps, mixed recency | Emerging regions with partial OSM data |
| 60-69% | Limited | Significant gaps, older data | Regional areas with fallback infrastructure data |
| 50-59% | Poor | Major data gaps, very limited sources | Remote regions with minimal infrastructure info |
| 40-49% | Minimal | Satellite-only analysis, no infrastructure/market data | Unknown regions, no OSM coverage |

### Confidence Impact on Final Score

```python
# Example: Region with 70 raw points, 75% confidence
final_score = 70 * (0.7 + (0.75 - 0.5) * 0.6)  # confidence_multiplier = 0.85
final_score = 70 * 0.85 = 59.5 points

# Example: Region with 70 raw points, 90% confidence  
final_score = 70 * (0.7 + (0.90 - 0.5) * 0.6)  # confidence_multiplier = 0.94
final_score = 70 * 0.94 = 65.8 points

# 90% confidence provides 6.3 points advantage over 75% confidence
```

---

## PDF Report Generation

**File:** `src/core/pdf_report_generator.py`  
**Library:** ReportLab  
**Output Format:** Multi-page PDF with embedded images and charts

### Report Structure

```
┌─────────────────────────────────────────────┐
│         EXECUTIVE SUMMARY (Page 1)          │
├─────────────────────────────────────────────┤
│ • Monitoring Period & Scope                 │
│ • Key Highlights (top opportunities)        │
│ • Overall Summary Statistics                │
│ • Investment Recommendations Overview       │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│    REGION DETAIL PAGES (Pages 2-N)          │
├─────────────────────────────────────────────┤
│ For Each Region:                            │
│                                             │
│ [1] REGION HEADER                           │
│     • Region Name                           │
│     • Recommendation (✅ BUY / ⚠️ WATCH / 🔴 PASS)  │
│     • Final Score & Confidence              │
│                                             │
│ [2] SCORE BREAKDOWN CHART                   │
│     • Bar chart showing component scores    │
│     • Development Activity (base score)     │
│     • Infrastructure Impact                 │
│     • Market Context                        │
│                                             │
│ [3] SATELLITE IMAGERY                       │
│     • 5 images in grid layout:              │
│       - True Color (current)                │
│       - NDVI (vegetation)                   │
│       - NDBI (built-up)                     │
│       - Change Detection Mask               │
│       - Development Hotspots                │
│                                             │
│ [4] INFRASTRUCTURE BREAKDOWN                │
│     • Highways: [List with distances]       │
│     • Ports: [List with distances]          │
│     • Railways: [Total length]              │
│     • Airports: [List with distances]       │
│     • Construction: [Active projects count] │
│                                             │
│ [5] DEVELOPMENT ACTIVITY ANALYSIS           │
│     • Activity Type Breakdown:              │
│       - Land Clearing: XX%                  │
│       - Active Construction: XX%            │
│       - Land Preparation: XX%               │
│       - Agricultural Conversion: XX%        │
│     • Dominant Activity Interpretation      │
│     • Investor Significance                 │
│                                             │
│ [6] CONFIDENCE BREAKDOWN                    │
│     • Satellite Data: XX%                   │
│     • Infrastructure Data: XX%              │
│     • Market Intelligence: XX%              │
│     • Overall Confidence: XX%               │
│     • Data Quality Notes                    │
│                                             │
│ [7] FINANCIAL PROJECTION SUMMARY       ← NEW│
│     • Land Value Estimates:                 │
│       - Current: Rp X,XXX,XXX/m²           │
│       - 3-Year Projection: Rp X,XXX,XXX/m² │
│     • Development Cost Estimates:           │
│       - Cost Index: XX/100 (Terrain)       │
│       - Est. Cost: Rp XXX,XXX/m²           │
│     • ROI Projections:                      │
│       - 3-Year ROI: XX%                     │
│       - 5-Year ROI: XX%                     │
│       - Break-Even: X.X years               │
│     • Investment Sizing:                    │
│       - Recommended Plot: X,XXX m²          │
│       - Total Investment: Rp XX.XB          │
│       - Projected Exit Value: Rp XX.XB      │
│     • Risk Assessment Matrix:               │
│       - Liquidity Risk: Low/Medium/High     │
│       - Speculation Risk: Low/Medium/High   │
│       - Infrastructure Risk: Low/Medium/High│
│     • Data Source: [Live/Cached/Benchmark]  │
│                                             │
│ [8] RECOMMENDATION RATIONALE           ← RENUMBERED│
│     • Why BUY/WATCH/PASS?                   │
│     • Key strengths                         │
│     • Risk factors                          │
│     • Next steps                            │
└─────────────────────────────────────────────┘
```

### Key PDF Components

#### 1. Executive Summary Page

```python
def generate_executive_summary(canvas, monitoring_data):
    # Title
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawString(50, 750, "Java-Wide Investment Opportunity Report")
    
    # Monitoring period
    canvas.setFont("Helvetica", 12)
    canvas.drawString(50, 720, f"Period: {start_date} to {end_date}")
    canvas.drawString(50, 705, f"Regions Analyzed: {region_count}")
    
    # Top opportunities (BUY recommendations)
    y_position = 670
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(50, y_position, "🏆 Top Investment Opportunities")
    
    y_position -= 25
    canvas.setFont("Helvetica", 11)
    for region in sorted_regions[:5]:  # Top 5
        score_display = f"{region.final_score:.1f}/100 ({region.confidence:.0%} confidence)"
        canvas.drawString(70, y_position, f"✅ {region.name}: {score_display}")
        y_position -= 20
    
    # Summary statistics
    y_position -= 30
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(50, y_position, "📊 Summary Statistics")
    
    y_position -= 25
    canvas.setFont("Helvetica", 11)
    canvas.drawString(70, y_position, f"Average Score: {avg_score:.1f}/100")
    y_position -= 20
    canvas.drawString(70, y_position, f"Average Confidence: {avg_confidence:.0%}")
    y_position -= 20
    canvas.drawString(70, y_position, f"BUY Recommendations: {buy_count} regions")
    y_position -= 20
    canvas.drawString(70, y_position, f"WATCH Recommendations: {watch_count} regions")
```

#### 2. Region Header with Recommendation

```python
def draw_region_header(canvas, region, y_position):
    # Recommendation emoji
    rec_emoji = {
        'BUY': '✅',
        'WATCH': '⚠️',
        'PASS': '🔴'
    }
    emoji = rec_emoji.get(region.recommendation, '❓')
    
    # Title with recommendation
    canvas.setFont("Helvetica-Bold", 18)
    title = f"{emoji} {region.name.upper()} - {region.recommendation}"
    canvas.drawString(50, y_position, title)
    
    # Score and confidence
    canvas.setFont("Helvetica", 12)
    score_text = f"Score: {region.final_score:.1f}/100 | Confidence: {region.confidence:.0%}"
    canvas.drawString(50, y_position - 20, score_text)
    
    return y_position - 50
```

#### 3. Infrastructure Breakdown Section

```python
def draw_infrastructure_breakdown(canvas, region, y_position):
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(50, y_position, "🏗️ Infrastructure Analysis")
    
    y_position -= 20
    canvas.setFont("Helvetica", 10)
    
    # Highways
    if region.infrastructure.highways:
        canvas.drawString(70, y_position, "Highways:")
        y_position -= 15
        for highway in region.infrastructure.highways[:3]:  # Top 3
            canvas.drawString(90, y_position, f"• {highway.name} ({highway.type})")
            y_position -= 12
    
    # Ports
    if region.infrastructure.ports:
        y_position -= 8
        canvas.drawString(70, y_position, "Ports:")
        y_position -= 15
        for port in region.infrastructure.ports[:2]:  # Top 2
            distance_km = haversine_distance(region.lat, region.lon, port.lat, port.lon)
            canvas.drawString(90, y_position, f"• {port.name} ({distance_km:.1f}km)")
            y_position -= 12
    
    # Railways
    if region.infrastructure.railways:
        y_position -= 8
        canvas.drawString(70, y_position, "Railways:")
        y_position -= 15
        total_length = sum(r.length_km for r in region.infrastructure.railways)
        canvas.drawString(90, y_position, f"• {total_length:.1f}km of rail within 25km")
        y_position -= 12
    
    # Airports
    if region.infrastructure.airports:
        y_position -= 8
        canvas.drawString(70, y_position, "Airports:")
        y_position -= 15
        for airport in region.infrastructure.airports[:2]:  # Top 2
            distance_km = haversine_distance(region.lat, region.lon, airport.lat, airport.lon)
            airport_type = "International" if airport.is_international else "Regional"
            canvas.drawString(90, y_position, f"• {airport.name} ({airport_type}, {distance_km:.1f}km)")
            y_position -= 12
    
    # Construction Projects
    if region.infrastructure.construction_count > 0:
        y_position -= 8
        canvas.drawString(70, y_position, "Active Construction:")
        y_position -= 15
        canvas.drawString(90, y_position, f"• {region.infrastructure.construction_count} active projects within 15km")
        y_position -= 12
    
    return y_position - 10
```

#### 4. Development Activity Analysis Section

```python
def draw_activity_breakdown(canvas, region, y_position):
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(50, y_position, "🔍 Development Activity Breakdown")
    
    y_position -= 20
    canvas.setFont("Helvetica", 10)
    
    # Activity percentages
    activities = region.activity_breakdown
    
    if activities.land_clearing_pct > 0:
        canvas.drawString(70, y_position, f"Land Clearing (Vegetation Removal): {activities.land_clearing_pct:.1f}%")
        y_position -= 15
        canvas.setFont("Helvetica-Oblique", 9)
        canvas.drawString(90, y_position, "Forest/vegetation being cleared, preparing for development")
        y_position -= 12
        canvas.setFont("Helvetica", 10)
    
    if activities.construction_pct > 0:
        y_position -= 5
        canvas.drawString(70, y_position, f"Active Construction: {activities.construction_pct:.1f}%")
        y_position -= 15
        canvas.setFont("Helvetica-Oblique", 9)
        canvas.drawString(90, y_position, "Buildings/structures under construction, high development momentum")
        y_position -= 12
        canvas.setFont("Helvetica", 10)
    
    if activities.land_preparation_pct > 0:
        y_position -= 5
        canvas.drawString(70, y_position, f"Land Preparation: {activities.land_preparation_pct:.1f}%")
        y_position -= 15
        canvas.setFont("Helvetica-Oblique", 9)
        canvas.drawString(90, y_position, "Bare earth exposure, grading, site preparation")
        y_position -= 12
        canvas.setFont("Helvetica", 10)
    
    if activities.agricultural_conversion_pct > 0:
        y_position -= 5
        canvas.drawString(70, y_position, f"Agricultural Conversion: {activities.agricultural_conversion_pct:.1f}%")
        y_position -= 15
        canvas.setFont("Helvetica-Oblique", 9)
        canvas.drawString(90, y_position, "Farmland being converted to urban/industrial use")
        y_position -= 12
        canvas.setFont("Helvetica", 10)
    
    # Dominant activity interpretation
    y_position -= 10
    canvas.setFont("Helvetica-Bold", 10)
    dominant = activities.dominant_activity
    canvas.drawString(70, y_position, f"Dominant Activity: {dominant}")
    
    y_position -= 15
    canvas.setFont("Helvetica-Oblique", 9)
    interpretations = {
        'Land Clearing': 'Early-stage development, land acquisition opportunity',
        'Active Construction': 'High momentum, consider downstream opportunities',
        'Land Preparation': 'Mid-stage development, infrastructure plays',
        'Agricultural Conversion': 'Urban expansion, emerging market opportunity'
    }
    canvas.drawString(90, y_position, f"→ {interpretations.get(dominant, 'Mixed development activity')}")
    
    return y_position - 20
```

#### 5. Satellite Image Grid

```python
def draw_satellite_images(canvas, region, y_position):
    # 5 images in 2x3 grid (2 on top row, 3 on bottom row)
    image_width = 200
    image_height = 150
    spacing = 20
    
    images = [
        ('true_color.png', 'True Color'),
        ('ndvi.png', 'NDVI (Vegetation)'),
        ('ndbi.png', 'NDBI (Built-up)'),
        ('change_mask.png', 'Change Detection'),
        ('hotspots.png', 'Development Hotspots')
    ]
    
    # Top row (2 images)
    x_positions_top = [50, 50 + image_width + spacing]
    for i in range(2):
        img_path = f"output/satellite_images/weekly/{region.slug}/{images[i][0]}"
        if os.path.exists(img_path):
            canvas.drawImage(
                img_path,
                x_positions_top[i],
                y_position,
                width=image_width,
                height=image_height,
                preserveAspectRatio=True
            )
            canvas.setFont("Helvetica", 9)
            canvas.drawString(
                x_positions_top[i],
                y_position - 12,
                images[i][1]
            )
    
    # Bottom row (3 images)
    y_position -= (image_height + 30)
    x_positions_bottom = [50, 50 + image_width + spacing, 50 + 2*(image_width + spacing)]
    for i in range(2, 5):
        img_path = f"output/satellite_images/weekly/{region.slug}/{images[i][0]}"
        if os.path.exists(img_path):
            canvas.drawImage(
                img_path,
                x_positions_bottom[i-2],
                y_position,
                width=image_width,
                height=image_height,
                preserveAspectRatio=True
            )
            canvas.setFont("Helvetica", 9)
            canvas.drawString(
                x_positions_bottom[i-2],
                y_position - 12,
                images[i][1]
            )
    
    return y_position - 20
```

---

## Monitoring System

### Java-Wide Monitoring

**File:** `run_weekly_java_monitor.py`  
**Scope:** 29 regions across Java island  
**Frequency:** Weekly  
**Duration:** ~87 minutes (3 minutes per region)

#### Region Groups

```python
JAVA_REGIONS = {
    'jakarta_metro': [
        'jakarta_north_sprawl',
        'jakarta_south_suburbs',
        'tangerang_bsd_corridor',
        'bekasi_industrial'
    ],
    'bandung_area': [
        'bandung_periurban',
        'cimahi_expansion'
    ],
    'central_java': [
        'semarang_suburbs',
        'solo_periphery',
        'yogyakarta_north',
        'yogyakarta_south',
        'magelang_corridor',
        'purwokerto_area'
    ],
    'east_java': [
        'surabaya_west',
        'surabaya_south',
        'malang_suburbs',
        'sidoarjo_delta'
    ],
    'banten': [
        'serang_industrial',
        'cilegon_corridor',
        'merak_port'
    ],
    'regional': [
        'cirebon_port',
        'tegal_industrial',
        'pekalongan_coast',
        'jepara_coast',
        'probolinggo_corridor',
        'banyuwangi_ferry',
        'jember_area',
        'kediri_suburbs',
        'blitar_area',
        'madiun_suburbs'
    ]
}
```

#### Monitoring Process Flow

```python
def run_weekly_monitoring():
    # 1. Initialize
    print("🇮🇩 JAVA-WIDE WEEKLY MONITORING")
    print(f"📊 Regions: {len(JAVA_REGIONS)} total")
    print(f"⏱️ Estimated: 87 minutes")
    
    # 2. Date ranges
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # 3. Process each region
    results = []
    for i, region in enumerate(JAVA_REGIONS, 1):
        print(f"\n{'='*60}")
        print(f"🔍 [{i}/{len(JAVA_REGIONS)}] Analyzing: {region.name}")
        print(f"{'='*60}")
        
        try:
            # Satellite analysis (60-90 seconds)
            satellite_data = analyze_satellite_changes(region, start_date, end_date)
            
            # Infrastructure analysis (30-60 seconds)
            infrastructure_data = analyze_infrastructure(region)
            
            # Market analysis (10-20 seconds)
            market_data = analyze_market_context(region)
            
            # Calculate final score (instant)
            final_score = calculate_final_score(
                satellite_data,
                infrastructure_data,
                market_data
            )
            
            # Save satellite images (20-30 seconds)
            save_satellite_images(region, satellite_data)
            
            # Store results
            results.append({
                'region': region.name,
                'score': final_score,
                'confidence': calculate_confidence(satellite_data, infrastructure_data, market_data),
                'recommendation': get_recommendation(final_score),
                'satellite_data': satellite_data,
                'infrastructure_data': infrastructure_data,
                'market_data': market_data
            })
            
            print(f"✅ {region.name}: {final_score:.1f}/100 ({recommendation})")
            
        except Exception as e:
            print(f"❌ {region.name}: Failed - {str(e)}")
            logging.error(f"Region {region.name} failed: {e}", exc_info=True)
            continue
    
    # 4. Generate PDF report
    print(f"\n{'='*60}")
    print("📄 Generating PDF Report...")
    print(f"{'='*60}")
    
    pdf_path = generate_pdf_report(results, start_date, end_date)
    
    # 5. Save JSON data
    json_path = save_json_results(results, start_date, end_date)
    
    # 6. Summary
    print(f"\n{'='*60}")
    print("✅ MONITORING COMPLETE")
    print(f"{'='*60}")
    print(f"📄 PDF Report: {pdf_path}")
    print(f"💾 JSON Data: {json_path}")
    print(f"📊 Regions Analyzed: {len(results)}/{len(JAVA_REGIONS)}")
    print(f"⏱️ Total Time: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
```

---

## Technical Implementation

### Dependencies

```txt
# Core
earthengine-api>=0.1.300
google-auth>=2.0.0
google-auth-oauthlib>=0.4.6

# Geospatial
geopandas>=0.10.0
shapely>=1.8.0
rasterio>=1.3.0

# Data Processing
numpy>=1.21.0
pandas>=1.3.0

# API & Web
requests>=2.27.0
flask>=2.0.0  # For API endpoints

# Web Scraping (NEW - v2.4)
beautifulsoup4>=4.12.0  # For HTML parsing
lxml>=4.9.0             # For fast XML/HTML parsing

# PDF Generation
reportlab>=3.6.0
Pillow>=9.0.0

# Utilities
python-dotenv>=0.19.0
pyyaml>=6.0
```

### Environment Configuration

```bash
# .env file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
EE_PROJECT=your-gee-project-id

# Optional
OSM_API_TIMEOUT=30
SATELLITE_IMAGE_SCALE=10
MAX_CLOUD_COVERAGE=20
```

### Key Files & Line Counts

```
# Core Scoring System
src/core/corrected_scoring.py       - 406 lines (scoring engine)
src/core/infrastructure_analyzer.py - 486 lines (OSM queries)
src/core/change_detector.py         - 620 lines (satellite analysis)
src/core/price_intelligence.py      - 280 lines (market data)

# Financial Metrics System (NEW - v2.4)
src/core/financial_metrics.py       - 773 lines (financial projection engine)
src/scrapers/base_scraper.py        - 380 lines (base scraper with caching)
src/scrapers/lamudi_scraper.py      - 420 lines (Lamudi.co.id scraper)
src/scrapers/rumah_scraper.py       - 415 lines (Rumah.com scraper)
src/scrapers/scraper_orchestrator.py- 390 lines (orchestration with fallback)

# Report Generation & Orchestration
src/core/pdf_report_generator.py    - 1180 lines (PDF creation)
src/core/automated_monitor.py       - 1604 lines (monitoring system)
run_weekly_java_monitor.py          - 247 lines (monitoring orchestrator)
src/regions.py                       - 450 lines (region definitions)

# Documentation
WEB_SCRAPING_DOCUMENTATION.md       - 600+ lines (scraping system guide)
TECHNICAL_SCORING_DOCUMENTATION.md  - 2000+ lines (this document)
```

### Error Handling

```python
# Satellite analysis errors
try:
    satellite_data = analyze_satellite_changes(region, start_date, end_date)
except ee.EEException as e:
    logging.error(f"Earth Engine error for {region.name}: {e}")
    satellite_data = None
    satellite_confidence = 0.0
except Exception as e:
    logging.error(f"Unexpected satellite error for {region.name}: {e}")
    satellite_data = None
    satellite_confidence = 0.0

# Infrastructure API errors (graceful degradation)
try:
    osm_data = query_overpass_api(query, timeout=30)
    if osm_data is None:
        # Use regional fallback
        osm_data = get_regional_fallback(region)
        data_source = 'regional_fallback'
        data_confidence = 0.60
except Exception as e:
    logging.warning(f"OSM query failed for {region.name}: {e}")
    osm_data = get_regional_fallback(region)
    data_source = 'fallback'
    data_confidence = 0.30

# PDF generation errors
try:
    generate_pdf_report(results, start_date, end_date)
except Exception as e:
    logging.error(f"PDF generation failed: {e}")
    # Save JSON backup
    save_json_results(results, start_date, end_date)
    raise
```

### Performance Optimization

```python
# Parallel region processing (future enhancement)
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    # Process 3 regions simultaneously
    futures = [
        executor.submit(analyze_region, region)
        for region in JAVA_REGIONS[:3]
    ]
    results = [f.result() for f in futures]

# Caching infrastructure queries (30-day cache)
@functools.lru_cache(maxsize=100)
def query_infrastructure_cached(region_id, cache_date):
    return query_infrastructure(region_id)

# Satellite image reuse (avoid re-exporting)
if os.path.exists(cached_image_path) and is_recent(cached_image_path):
    return cached_image_path
else:
    return export_new_image()
```

---

## Appendix: Formula Reference Card

### Quick Reference

```
FINAL SCORE = BASE × INFRA × MARKET × CONFIDENCE

BASE SCORE (0-40 points):
  = min(40, (change_area_km2 / region_area_km2) * 100 * 4)

INFRASTRUCTURE MULTIPLIER (0.8-1.3x) - TIERED:
  Excellent (90-100): 1.30x
  Very Good (75-89):  1.15x
  Good (60-74):       1.00x
  Fair (40-59):       0.90x
  Poor (<40):         0.80x

MARKET MULTIPLIER (0.85-1.4x) - TIERED:
  Booming (>15%/yr):   1.40x
  Strong (8-15%/yr):   1.20x
  Stable (2-8%/yr):    1.00x
  Stagnant (0-2%/yr):  0.95x
  Declining (<0%/yr):  0.85x

CONFIDENCE MULTIPLIER (0.7-1.0x):
  = 0.7 + (overall_confidence - 0.5) * 0.6

OVERALL CONFIDENCE:
  = (satellite * 0.5 + infrastructure * 0.3 + market * 0.2) 
    × quality_bonuses × quality_penalties

RECOMMENDATION:
  - BUY:   score >= 60
  - WATCH: 40 <= score < 60
  - PASS:  score < 40
```

### Thresholds

```
SATELLITE CHANGE THRESHOLDS:
  NDVI Decrease: > 0.15  (vegetation loss)
  NDBI Increase: > 0.10  (built-up increase)
  Brightness:    > 0.15  (bare earth)

INFRASTRUCTURE RADII (EXPANDED):
  Highways:      50 km (expanded from 25km for rural coverage)
  Ports:         50 km
  Railways:      25 km
  Airports:      100 km
  Construction:  15 km

INFRASTRUCTURE TIERS:
  Excellent: 90-100 → 1.30x multiplier (World-class: Jakarta, Surabaya)
  Very Good: 75-89  → 1.15x multiplier (Major cities: Bandung, Semarang)
  Good:      60-74  → 1.00x multiplier (Urban centers: Yogyakarta, Malang)
  Fair:      40-59  → 0.90x multiplier (Developing: Magelang, Bantul)
  Poor:      <40    → 0.80x multiplier (Rural: Gunungkidul)

EXPECTED INFRASTRUCTURE SCORE RANGES (Post Oct 19 Fix):
  World-class (85-100): Major metro areas with airports, ports, rail, highways
  Excellent (70-84):    Regional hubs with good multi-modal connectivity
  Good (55-69):         Urban areas with highway and basic infrastructure
  Basic (40-54):        Suburban/developing with limited connectivity
  Poor (20-39):         Rural/remote with minimal infrastructure

MARKET TIERS:
  Booming:   >15%/yr  → 1.40x multiplier
  Strong:    8-15%/yr → 1.20x multiplier
  Stable:    2-8%/yr  → 1.00x multiplier
  Stagnant:  0-2%/yr  → 0.95x multiplier
  Declining: <0%/yr   → 0.85x multiplier

CONFIDENCE BONUSES/PENALTIES:
  Market > 85%:         +5% bonus
  Infrastructure > 85%: +5% bonus
  Overall < 70%:        -5% penalty

CLOUD COVERAGE:
  Maximum acceptable: 20%
  Preferred:          < 10%
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.1 | 2025-10-18 | Chris Moore | **Major improvements:** Tiered multipliers (infra 0.8-1.3x, market 0.85-1.4x), expanded infrastructure search radius (50km), comprehensive retry logic with fallback servers, 35-region infrastructure database |
| 2.0 | 2025-10-18 | Chris Moore | Complete technical documentation created |
| 1.x | 2025-10-11 | Chris Moore | Various debugging and fix documentation |
| 0.1 | 2025-09-25 | Chris Moore | Initial project setup |

---

**End of Technical Documentation**
