# CloudClearingAPI - AI Agent Development Guide# GitHub Copilot Instructions for CloudClearingAPI



## System OverviewYou are an expert Python developer specializing in geospatial analysis, financial modeling, and web scraping. Your primary role is to assist in developing the CloudClearingAPI.



CloudClearingAPI is a **satellite-based land investment intelligence platform** that monitors 29+ regions across Indonesia (Java island focus) for development opportunities. It combines Sentinel-2 imagery analysis with real-time infrastructure data and financial projections to generate weekly investment reports with BUY/WATCH/PASS recommendations.## 1. Core Project Objective



**Core Value Proposition:** Transform satellite pixels → actionable investment thesis with concrete ROI projections.The system identifies land development investment opportunities in Indonesia by analyzing satellite data for physical changes and then enriching this with infrastructure quality and financial viability metrics. The final output is an automated PDF report.



------



## Critical Architectural Patterns## 2. Key Technologies & Libraries



### 3-Stage Pipeline (NEVER Mix These!)- **Primary Language:** Python 3.10+

- **Geospatial:** `earthengine-api` for satellite data.

The system uses strict separation of concerns across three distinct stages:- **Infrastructure:** `requests` to query the OpenStreetMap Overpass API.

- **Financial Data:** `requests` and `BeautifulSoup4` for web scraping real estate portals (Lamudi, Rumah.com).

#### Stage 1: Core Activity Scoring (`src/core/corrected_scoring.py`)- **PDF Generation:** `reportlab` is the **only** library used for creating PDF reports.

- **Input:** Satellite change detection (pixel counts, area affected)- **Configuration:** `PyYAML` for loading settings from `config.yaml`.

- **Output:** Base activity score (0-40 points) - **Data Structures:** Use `@dataclass` for simple data containers.

- **Multipliers:** Infrastructure (0.8-1.3x) and Market (0.85-1.4x) applied here

- **Rule:** ONLY satellite data determines base score. No financial calculations here.---



```python## 3. Architectural Principles

# CORRECT pattern - satellite drives base score

development_score = self._calculate_development_score(satellite_changes)  # 0-40The system has three main, distinct stages. Always maintain this separation of concerns.

final_score = development_score * infra_multiplier * market_multiplier  # 0-100

```### Stage 1: Core Scoring (Activity Score)



#### Stage 2: Financial Projection (`src/core/financial_metrics.py`)- **File:** `src/core/corrected_scoring.py`

- **Input:** Completed scoring results + raw data from Stage 1- **Purpose:** To generate a base "Activity Score" from 0-40 based **only** on satellite data.

- **Output:** `FinancialProjection` dataclass with ROI, land values, dev costs- **Logic:** This score is then adjusted by Infrastructure and Market multipliers. Do not mix financial calculations into this core score.

- **Data Flow:** 3-tier cascading fallback for land prices

  1. **Live scraping** (Lamudi, Rumah.com) → 85% confidence### Stage 2: Financial Projection Engine

  2. **Cached data** (< 24h old) → 75-85% confidence  

  3. **Static benchmarks** → 50% confidence- **File:** `src/core/financial_metrics.py`

- **Rule:** Runs AFTER scoring completes. Never modifies activity scores.- **Purpose:** This engine runs *after* the core scoring is complete. It takes the satellite, infrastructure, and market data as inputs to calculate ROI, land value, and development costs.

- **Data Source:** It uses the `LandPriceOrchestrator` which has a cascading logic: **Live Scrape > Cache > Static Benchmark**. This pattern is critical.

```python

# Integration point in automated_monitor.py (_generate_investment_analysis method)### Stage 3: PDF Report Generation

if self.financial_engine:

    financial_projection = self.financial_engine.calculate_financial_projection(- **File:** `src/core/pdf_report_generator.py`

        region_name=region_name,- **Purpose:** To take the final scoring results and financial projections and render them into a multi-page PDF using `reportlab`.

        satellite_data=satellite_data,

        infrastructure_data=infrastructure_data,---

        market_data=market_data,

        scoring_result=corrected_result  # Pass completed score## 4. Important Coding Patterns & Rules

    )

    dynamic_score['financial_projection'] = financial_projection- **Strict Type Hinting:** All function signatures and variables should have type hints (`str`, `Dict`, `List`, `Optional`).

```- **Use Dataclasses:** For data transfer objects like `FinancialProjection` or `ScrapeResult`, always prefer using `@dataclass`.

- **Configuration Management:** Never hardcode URLs, file paths, or thresholds. These values must be loaded from a `config.yaml` file via the `Config` class.

#### Stage 3: PDF Report Generation (`src/core/pdf_report_generator.py`)- **Error Handling:** All network requests (`requests.get`, `ee.ImageCollection`) must be wrapped in `try...except` blocks that handle timeouts and connection errors gracefully.

- **Input:** JSON results with scores + financial projections- **Logging, Not Printing:** Use the `logging` module for all debugging and informational output. Avoid using `print()`.

- **Output:** Multi-page PDF with imagery, charts, recommendations- **Web Scraping Rules:** When working on scrapers, always include user-agent rotation and a rate limit (e.g., `time.sleep(2)`).

- **Library:** ONLY `reportlab` (never matplotlib for PDFs)

- **Rule:** Pure rendering layer. No business logic.By following these instructions, you will provide highly relevant, context-aware code that fits perfectly within the existing CloudClearingAPI architecture.

### Data Source Priority Rules

**Infrastructure (OpenStreetMap Overpass API):**
- Highways within 25km → Primary accessibility score
- Airports within 100km → Development catalyst bonus
- Railways within 25km → Industrial potential indicator
- **Timeout handling:** 30s default, fallback to partial data never fails scoring

**Satellite (Google Earth Engine):**
- Sentinel-2 only (10m resolution)
- Smart date finding: Try 7d → 14d → 30d → 60d windows automatically
- Cloud coverage: <20% preferred, <50% acceptable with masking
- **Always succeeds:** Fallback dates ensure 100% uptime

**Market Data (Web Scraping + Benchmarks):**
- Cache-first strategy (check before scraping)
- Rate limiting: 2s between requests
- User-agent rotation (5 agents in config)
- **Graceful degradation:** Never block on scraping failures

---

## Key File Responsibilities

| File | Purpose | Critical Patterns |
|------|---------|------------------|
| `run_weekly_java_monitor.py` | Entry point for automated monitoring | Async/await, region batching, confirmation prompt |
| `src/core/automated_monitor.py` | Orchestrates analysis pipeline | Smart date ranges, parallel region processing, timeout handling |
| `src/core/corrected_scoring.py` | Investment scoring algorithm | Satellite-centric base score, tiered multipliers, confidence weighting |
| `src/core/change_detector.py` | Satellite change detection | NDVI/NDBI/BSI spectral analysis, cloud masking, GEE API calls |
| `src/core/infrastructure_analyzer.py` | OSM infrastructure queries | Overpass API, distance weighting, component normalization |
| `src/core/financial_metrics.py` | ROI and land value projections | 3-tier fallback, regional benchmarks, dataclass outputs |
| `src/scrapers/scraper_orchestrator.py` | Web scraping coordination | Try live → cache → benchmark, never throw exceptions |
| `src/core/pdf_report_generator.py` | Report rendering | reportlab ONLY, section builders, image embedding |

---

## Development Workflows

### Running Full Analysis (Weekly Monitoring)

```bash
# Authenticate GEE first (one-time)
earthengine authenticate

# Run weekly monitoring (29 regions, ~87 minutes)
python run_weekly_java_monitor.py

# Output locations:
# - PDF report: output/reports/executive_summary_YYYYMMDD_HHMMSS.pdf
# - JSON data: output/monitoring/weekly_monitoring_YYYYMMDD_HHMMSS.json
# - Satellite images: output/satellite_images/weekly/[region]/
```

### Testing Individual Components

```python
# Test corrected scoring system
from src.core.corrected_scoring import CorrectedInvestmentScorer
scorer = CorrectedInvestmentScorer(price_engine, infra_engine)
result = scorer.calculate_investment_score(
    region_name="Sleman North",
    satellite_changes=1234,
    area_affected_m2=120000,
    region_config=config,
    coordinates={'lat': -7.7, 'lon': 110.4},
    bbox={'west': 110.25, 'south': -7.95, 'east': 110.55, 'north': -7.65}
)

# Test financial projections
from src.core.financial_metrics import FinancialMetricsEngine
financial_engine = FinancialMetricsEngine(enable_web_scraping=True, cache_expiry_hours=24)
projection = financial_engine.calculate_financial_projection(
    region_name="Yogyakarta North",
    satellite_data={'vegetation_loss_pixels': 5200, 'construction_activity_pct': 0.18},
    infrastructure_data={'infrastructure_score': 72, 'major_features': [...]},
    market_data={'price_trend_30d': 0.08, 'market_heat': 'warming'},
    scoring_result=result
)
```

### Adding New Regions

Edit `src/indonesia_expansion_regions.py`:

```python
ExpansionRegion(
    name="New Region Name",
    slug="new_region_slug",
    bbox=(west, south, east, north),  # Decimal degrees
    priority=1,  # 1=high, 2=medium, 3=emerging
    island="java",
    focus="industrial"  # infrastructure/industrial/urban/tourism
)
```

---

## Configuration Patterns

### Always Use config.yaml (NEVER Hardcode!)

```python
# WRONG - hardcoded values
timeout = 30
max_cloud = 20

# CORRECT - from config
from src.core.config import get_config
config = get_config()
timeout = config.infrastructure.api_timeout
max_cloud = config.satellite.max_cloud_coverage
```

### Critical Config Sections

- `gee_project`: Google Cloud Project ID (REQUIRED since 2023)
- `web_scraping.enabled`: Toggle live scraping vs benchmarks only
- `web_scraping.cache_expiry_hours`: Balance freshness vs API load (24-48h recommended)
- `monitoring.bbox_*`: Coordinates for single-region analysis
- `processing.max_cloud_cover`: 20 = strict, 50 = permissive

---

## Error Handling Requirements

### Network Requests (OSM, Web Scraping)

```python
# ALWAYS wrap with try/except and timeout
try:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
except requests.Timeout:
    logger.warning(f"Timeout fetching {url}, using fallback")
    data = self._get_fallback_data()
except requests.RequestException as e:
    logger.error(f"Request failed: {e}, using fallback")
    data = self._get_fallback_data()
```

### Google Earth Engine Calls

```python
# GEE requires special error handling for quota/server issues
try:
    image = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()
    
    # ALWAYS check if collection is empty before computations
    if image.bandNames().size().getInfo() == 0:
        logger.warning("No images found, trying wider date range")
        # Implement fallback date range logic
        
except ee.EEException as e:
    logger.error(f"GEE error: {e}")
    # Try alternative date range or skip region gracefully
```

### Scraping Failures (NEVER Block Progress)

```python
# Financial projections should NEVER crash the pipeline
try:
    financial_projection = self.financial_engine.calculate_financial_projection(...)
except Exception as e:
    logger.warning(f"Financial projection failed: {e}")
    financial_projection = None  # Continue without financial data

dynamic_score['financial_projection'] = financial_projection  # None is OK
```

---

## Coding Standards

### Type Hints (Strictly Enforced)

```python
# ALL function signatures need complete type hints
def analyze_region(
    region_name: str,
    bbox: Dict[str, float],
    date_range: Tuple[str, str]
) -> Optional[Dict[str, Any]]:
    pass

# Use dataclasses for complex return types
@dataclass
class ScoringResult:
    final_score: float
    confidence: float
    recommendation: str
```

### Logging (Not Printing!)

```python
# WRONG
print(f"Processing {region_name}...")

# CORRECT
logger.info(f"Processing {region_name}...")
logger.debug(f"Using date range: {start_date} to {end_date}")
logger.warning(f"Cloud cover {cloud_pct}% exceeds threshold")
logger.error(f"Failed to fetch data: {error_msg}")
```

### Dataclasses for Data Transfer

```python
# Use @dataclass for structured data (not dicts!)
from dataclasses import dataclass

@dataclass
class FinancialProjection:
    current_land_value_per_m2: float
    projected_roi_3yr: float
    recommended_plot_size_m2: float
    data_sources: List[str]
```

---

## Common Pitfalls & Solutions

### ❌ Mixing Scoring with Financial Calculations
**Problem:** Adding ROI or land prices to Stage 1 scoring  
**Solution:** Financial metrics ONLY in Stage 2, after scoring completes

### ❌ Hardcoding Region Coordinates
**Problem:** Coordinates in function calls instead of config  
**Solution:** Always get regions from `get_expansion_manager()` or config

### ❌ Using print() for Debugging
**Problem:** Output gets lost, no log levels, can't filter  
**Solution:** Use `logger.debug()`, `logger.info()`, etc.

### ❌ Not Handling API Timeouts
**Problem:** Script hangs on network issues  
**Solution:** ALWAYS use `timeout=` parameter, wrap in try/except

### ❌ Cache Without Expiry Checks
**Problem:** Serving stale data indefinitely  
**Solution:** Check file timestamp, respect `cache_expiry_hours`

---

## Testing Strategy

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test specific component
pytest tests/test_core.py::TestCorrectedScoring -v

# End-to-end smoke test (requires GEE auth)
python -c "from src.core.automated_monitor import AutomatedMonitor; \
           import asyncio; \
           asyncio.run(AutomatedMonitor().run_weekly_monitoring())"
```

---

## Dependencies & Installation

```bash
# Core dependencies
pip install earthengine-api google-auth requests pyyaml reportlab

# Financial metrics (web scraping)
pip install beautifulsoup4 lxml

# Development
pip install pytest pytest-cov black pylint mypy

# One-time GEE setup
earthengine authenticate
```

---

## Quick Reference: Data Flow

```
┌─────────────────────────────────────────────┐
│  run_weekly_java_monitor.py (Entry Point)  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  automated_monitor.py (Orchestrator)        │
│  - Smart date finding (7d→14d→30d→60d)     │
│  - Parallel region processing               │
│  - Timeout handling                         │
└───┬──────────────┬──────────────┬───────────┘
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│Sentinel│  │   OSM    │  │  Market  │
│  GEE   │  │Overpass  │  │ Scraping │
└────┬───┘  └─────┬────┘  └─────┬────┘
     │            │              │
     └────────────┼──────────────┘
                  ▼
     ┌────────────────────────┐
     │ corrected_scoring.py   │
     │ (Base Score 0-40)      │
     └──────────┬─────────────┘
                │
                ▼
     ┌────────────────────────┐
     │ financial_metrics.py   │
     │ (ROI Projections)      │
     └──────────┬─────────────┘
                │
                ▼
     ┌────────────────────────┐
     │ pdf_report_generator   │
     │ (Final Reports)        │
     └────────────────────────┘
```

---

## Version History Context

- **v2.4** (Oct 19, 2025): Added financial metrics engine with live web scraping
- **v2.3** (Oct 19, 2025): Fixed infrastructure scoring inflation (100/100 bug)
- **v2.0** (Oct 6, 2025): Major refactor making satellite data PRIMARY score component

**Why this matters:** If you see `speculative_scorer.py` references, they're deprecated. Always use `corrected_scoring.py` for scoring logic.

---

When contributing to CloudClearingAPI, maintain the strict 3-stage separation, always handle network failures gracefully, and remember: **satellite changes drive the base score, everything else multiplies or enriches.**
