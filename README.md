# CloudClearingAPI: Land Development Investment Intelligence

**Version:** 2.11 (Scraper Integration + Price History + Auto-Email)
**Status:** ✅ Production Ready | 29 Java Regions | Weekly Automated Reports with Email Delivery

### What is CloudClearingAPI?

CloudClearingAPI is an **automated land investment analyst for Indonesia**. It spots developing areas early — before the boom — by combining satellite imagery, live market prices, infrastructure data, and development news into a single investment score.

The core idea: satellite change detection (SAR radar + optical) identifies *where* construction and land clearing is happening. Market scrapers, infrastructure analysis, and news articles provide context on *whether that activity is a good investment*. Over time, historical comparisons reveal *which areas are accelerating*.

**This system empowers you to:**
* **Spot Development Early:** Detect land clearing and construction via dual-sensor satellite analysis (optical + cloud-penetrating SAR radar)
* **Evaluate Financial Viability:** Live market prices from Lamudi.co.id feed RVI (Relative Value Index) calculations and price trend analysis
* **Assess Infrastructure:** Real-time OpenStreetMap queries score roads, airports, railways, and construction projects
* **Track Momentum:** Historical score comparisons and price archives reveal accelerating regions
* **Receive Automated Reports:** Weekly PDF executive summary with BUY/WATCH/PASS ratings, emailed automatically after each run

---

## Changelog

### v2.11 (March 2026) — SAR Fusion + News Catalyst + Price Momentum

- **Sentinel-1 SAR radar fusion** — cloud-penetrating radar complements optical imagery; 60/40 weighted fusion with +10% confidence boost
- **News catalyst scoring** — scrapes Jakarta Post, Kompas, Antara News; word-boundary matching to 29 regions; clickable article links in PDF
- **Live market scrapers repaired** — Lamudi returns 20+ real listings/region; 99.co rewritten for `__NEXT_DATA__` JSON parsing
- **JSONL price history archive** — each scrape appends timestamped snapshot; enables 14-60 day price trend calculation
- **Momentum analyzer** — compares 4-week recent velocity vs 8-16 week baseline from historical monitoring JSONs
- **Auto-email after every run** — Gmail SMTP with PDF attachment, not just cron-triggered
- **RVI fix** — `calculate_relative_value_index` now correctly calls `FinancialMetricsEngine`
- **OSM parallelized** — roads, airports, railways queried concurrently with 30s hard timeout

<details>
<summary>Previous releases (v2.0–v2.6)</summary>

**v2.6-beta** — RVI-aware market multiplier, airport premium override (+25% for YIA/BWX/KJT), Tier 1+ ultra-premium sub-classification, tier-specific infrastructure tolerances. 35/35 tests, 39 production regions validated.

**v2.6-alpha** — Regional tier classification (4 tiers, 29 regions), Relative Value Index (RVI), multi-source scraping fallback (Lamudi → 99.co → cache → benchmarks), request hardening with exponential backoff, comprehensive documentation suite.

**v2.5** — Google Earth Engine satellite change detection, OSM infrastructure scoring, PDF executive summary reports, weekly automated monitoring for 29 Java regions.

**v2.0** — Initial release with Sentinel-2 optical analysis and basic scoring.

</details>

---


## ✨ The Scoring Philosophy: From Activity to Opportunity

The system answers three questions every investor asks:

1.  **Where is new activity?** (Satellite change detection — the primary signal)
2.  **Is this activity a good investment?** (Market, infrastructure, and news multipliers)
3.  **Is it accelerating?** (Momentum from historical comparisons)

**Final Score** = Activity × Infrastructure × Market × News × Confidence × Momentum

```
Activity Score (0-40)              ← Satellite changes detected (SAR + optical fusion)
  × Infrastructure (0.8x-1.3x)    ← OSM roads, airports, railways (7-day cache)
  × Market (0.85x-1.40x)          ← RVI from live Lamudi prices, or price trend from history
  × News (0.95x-1.20x)            ← Jakarta Post, Kompas, Antara article sentiment
  × Confidence (0.70-1.00)        ← Data completeness + dual-sensor boost
  × Momentum (0.85x-1.30x)        ← 4-week recent vs 8-16 week baseline acceleration
= Final Investment Score (0-100)   → BUY (≥40) / WATCH (25-39) / PASS (<25)
```

### What each component tracks over time

| Component | Data Source | Cached? | Compares Historically? |
|-----------|-----------|---------|----------------------|
| **Satellite Activity** | GEE Sentinel-1 SAR + Sentinel-2 | 14-day GEE cache | Not directly — momentum analyzer compares weekly scores |
| **Infrastructure** | OpenStreetMap Overpass API | 7-day file cache | Snapshot only (OSM tracks current state) |
| **Market Prices** | Lamudi live scraping (20+ listings/region) | 24h cache + JSONL price archive | ✅ Yes — price trend calculated from 14-60 day history |
| **News Catalyst** | Jakarta Post, Kompas, Antara | Per-run in-memory cache | Not yet (current articles only) |
| **Momentum** | Historical `weekly_monitoring_*.json` files | File system | ✅ Yes — compares 4-week recent velocity vs 8-16 week baseline |
| **RVI (Relative Value Index)** | Scraped prices vs tier benchmarks | Via financial engine | Indirectly (benchmarks are static, scraped prices change) |

---

## ⚙️ How the Scoring Works

### Part 1: Activity Score (0-40 Points) — Satellite Change Detection

The foundation of the score. Detects *where* development is happening via dual-sensor satellite analysis:

* **Sentinel-2 Optical** (primary): 10m resolution imagery detecting vegetation loss, construction, and land clearing
* **Sentinel-1 SAR Radar** (complement): Cloud-penetrating radar that works through Indonesia's frequent cloud cover

**Sensor Fusion:** Both available → 60% optical + 40% SAR (+10% confidence boost). Optical only → standard. SAR only → radar fallback (critical during Java rainy season).

**What gets detected:** Vegetation loss (VH backscatter decrease + NDVI change), new construction (VV increase + VH decrease pattern), land preparation (surface roughness + bare soil index).

**Caching:** GEE image results cached 14 days. Optical attempts limited to 5 date windows to avoid timeouts.

### Part 2: Infrastructure Multiplier (0.8x - 1.3x) — OSM Analysis

Assesses surrounding infrastructure quality via OpenStreetMap Overpass API. Three parallel queries: roads (motorway/trunk/primary density), airports (within 100km, distance-decay weighted), railways (rail/light_rail/subway).

| Infrastructure Score | Multiplier | Interpretation |
| :--- | :--- | :--- |
| **90-100** | **1.30x** | Major hub, excellent connectivity |
| **75-89** | **1.15x** | Strong transport links |
| **60-74** | **1.00x** | Adequate for development |
| **40-59** | **0.90x** | Basic, potential limitations |
| **< 40** | **0.80x** | Weak or missing infrastructure |

**Caching:** OSM results cached 7 days per region. Queries run in parallel with 30s hard timeout.

### Part 3: Market Multiplier (0.85x - 1.40x) — Live Price Data

Two modes, depending on data availability:

**Mode A: RVI-Aware (when FinancialMetricsEngine available)**
Compares live scraped prices against tier-appropriate expected prices:

| RVI Value | Multiplier | Interpretation |
| :--- | :--- | :--- |
| **< 0.7** | **1.40x** | Significantly undervalued |
| **0.7-0.9** | **1.25x** | Undervalued — buy opportunity |
| **0.9-1.1** | **1.00x** | Fair value |
| **1.1-1.3** | **0.90x** | Overvalued — caution |
| **≥ 1.3** | **0.85x** | Significantly overvalued |

**Mode B: Trend-Based (fallback)**
Uses price change over time from JSONL price history archive:

| Price Trend (annualized) | Multiplier | Market Heat |
| :--- | :--- | :--- |
| **> 15%** | **1.40x** | Booming |
| **8-15%** | **1.20x** | Strong |
| **2-8%** | **1.00x** | Stable |
| **0-2%** | **0.95x** | Stagnant |
| **< 0%** | **0.85x** | Declining |

**Data cascade:** Live Lamudi scraping (20+ listings/region, verified Rp 4-24M/m² range) → Rumah.com → 99.co → 24h cache → static benchmarks (last resort, 50% confidence).

**Price history:** Each scrape appends a timestamped snapshot to JSONL files (`output/scraper_cache/price_history/`). Trend calculator reads the record closest to 30 days ago (accepts 14-60 day window). Over successive weekly runs, this builds a reliable price trend for each region.

### Part 4: News Catalyst (0.95x - 1.20x) — Development News

Scrapes Indonesian infrastructure news from three sources:

1. **Jakarta Post** — English business/infrastructure articles
2. **Kompas** — Indonesian property/economy sections
3. **Antara News** — Indonesian wire service economy section

Articles are matched to regions by city name (word-boundary matching to avoid false positives), then scored by keyword relevance (toll roads, SEZs, airports, railway, industrial parks, etc.) and sentiment. Clickable article links appear in the PDF report.

| News Signal | Multiplier |
| :--- | :--- |
| **6+ positive articles** | **1.15x-1.20x** |
| **3-5 positive** | **1.10x** |
| **1-2 positive** | **1.05x** |
| **No articles** | **1.00x** |
| **Negative dominant** | **0.95x** |

### Part 5: Confidence Score (0.70 - 1.00) — Data Quality Check

Ensures the system is honest about data quality. Low confidence reduces the score, preventing strong recommendations from incomplete data.

* **Satellite Data (50% weight):** Higher with recent, cloud-free images. +10% boost with SAR dual-sensor fusion.
* **Infrastructure Data (30% weight):** Highest with live OSM data, lower with regional fallbacks.
* **Market Data (20% weight):** 85% confidence for live scraped prices, 50% for static benchmarks.

### Part 6: Momentum (0.85x - 1.30x) — Historical Acceleration

Compares recent satellite activity against historical baseline to detect regions that are accelerating:

* **Recent window:** Average change_count over last 4 weekly monitoring runs
* **Baseline window:** Average change_count from 8-16 weeks ago
* **Momentum ratio:** recent_velocity / baseline_velocity

| Momentum Ratio | Multiplier | Trend |
| :--- | :--- | :--- |
| **≥ 5.0** | **1.30x** | Surging — dramatic acceleration |
| **2.0-5.0** | **1.15x-1.30x** | Accelerating — strong growth |
| **1.0-2.0** | **1.00x-1.15x** | Steady to growing |
| **0.5-1.0** | **0.85x-1.00x** | Decelerating — activity slowing |
| **< 0.5** | **0.85x** | Stalling — significant slowdown |

**Data source:** Reads all `output/monitoring/weekly_monitoring_*.json` files to build historical velocity per region. Requires at least 2 data points in each window to activate.

---

## 📊 System Output: The Investment Report

The primary output is a multi-page PDF report that provides a comprehensive overview of each region.

* **Page 1: Executive Summary:** Highlights the top investment opportunities and summary statistics.
* **Region Detail Pages:** Each region gets its own detailed analysis, including:
    1.  **Final Recommendation:** A clear **✅ BUY**, **⚠️ WATCH**, or **🔴 PASS** rating.
    2.  **Score & Confidence:** The final score and the data confidence percentage.
    3.  **Financial Projection Summary:** The most valuable section, detailing **ROI projections**, **land value estimates**, total investment costs, and key risks.
    4.  **Satellite Imagery:** A grid of 5 images showing before/after, vegetation loss, and new construction hotspots.
    5.  **Infrastructure Details:** A list of nearby highways, ports, and airports.
    6.  **Development Activity Analysis:** A breakdown of detected activity (e.g., 60% Land Clearing, 40% Active Construction).

---

## 🏗️ System Architecture Overview

```
DATA INPUTS                           CACHING LAYER
├── Sentinel-2 Optical (GEE)    ──→   GEE cache (14-day TTL)
├── Sentinel-1 SAR Radar (GEE)  ──→   GEE cache (14-day TTL)
├── OpenStreetMap Overpass API   ──→   OSM cache (7-day TTL)
├── Lamudi.co.id (live scrape)  ──→   Scraper cache (24h) + JSONL price history
├── 99.co (live scrape)         ──→   Scraper cache (24h) + JSONL price history
└── News (JP, Kompas, Antara)   ──→   In-memory per-run cache
     ↓
SCORING PIPELINE (per region, ~45s each)
├── Optical + SAR Change Detection → satellite_changes (fused)
├── OSM Infrastructure Query (parallel: roads, airports, railways)
├── Live Market Price Scraping → RVI or price trend multiplier
├── News Article Matching → sentiment-based multiplier
├── Momentum Analysis → compare 4wk recent vs 8-16wk baseline
└── CorrectedInvestmentScorer combines all → Final Score (0-100)
     ↓
OUTPUT
├── JSON Data: output/monitoring/weekly_monitoring_[timestamp].json
├── PDF Report: output/reports/executive_summary_[timestamp].pdf
│   └── Clickable news article links, score breakdown, satellite imagery
├── Email: Auto-sent to configured recipient with PDF attached
└── Price Archive: output/scraper_cache/price_history/ (JSONL, accumulates)
```

---

## 🚀 Quick Start

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.**

### Prerequisites

1. **Python 3.8+** - [Download here](https://www.python.org/downloads/)
2. **Google Earth Engine Account** - [Sign up here](https://earthengine.google.com/signup/)
3. **Google Cloud Project** with Earth Engine API enabled

### Installation

```bash
# 1. Clone and setup
git clone https://github.com/MIFUNEKINSKi/CloudClearingAPI.git
cd CloudClearingAPI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Google Earth Engine (one-time)
earthengine authenticate

# 4. Configure settings
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your GCP project ID

# 5. Run investment analysis
python run_weekly_java_monitor.py
```

### Expected Outputs

After running the analysis, you'll find:

- **PDF Report:** `output/reports/executive_summary_[timestamp].pdf`
- **JSON Data:** `output/monitoring/weekly_monitoring_[timestamp].json`
- **Satellite Images:** `output/satellite_images/weekly/[region]/`

---

## 📁 Project Structure

```
CloudClearingAPI/
├── src/
│   ├── core/
│   │   ├── corrected_scoring.py       # Main scoring engine (Activity × Infra × Market × News × Confidence)
│   │   ├── automated_monitor.py       # Orchestrates full 29-region pipeline
│   │   ├── sar_change_detector.py     # Sentinel-1 SAR radar change detection
│   │   ├── change_detector.py         # Sentinel-2 optical change detection
│   │   ├── infrastructure_analyzer.py # OSM Overpass API infrastructure scoring
│   │   ├── news_catalyst.py           # News sentiment → multiplier (0.95-1.20x)
│   │   ├── momentum_analyzer.py       # Historical acceleration (4wk vs 8-16wk baseline)
│   │   ├── financial_metrics.py       # ROI projections, RVI calculation, land value estimates
│   │   ├── pdf_report_generator.py    # Executive summary PDF with linked news articles
│   │   └── gee_cache.py              # GEE image cache (14-day TTL)
│   ├── scrapers/
│   │   ├── lamudi_scraper.py          # Lamudi.co.id HTML+JSON-LD parser (primary source)
│   │   ├── ninety_nine_scraper.py     # 99.co __NEXT_DATA__ JSON parser
│   │   ├── rumah_scraper.py           # Rumah.com (JS-rendered, needs headless browser)
│   │   ├── news_scraper.py            # Jakarta Post, Kompas, Antara News scraper
│   │   ├── scraper_orchestrator.py    # Cascading fallback: Lamudi → 99.co → cache → benchmarks
│   │   └── base_scraper.py           # Base class with caching, retry, price history archive
│   └── indonesia_expansion_regions.py # 29 monitored Java regions with coordinates
│
├── cache/
│   ├── osm/                          # OSM infrastructure query cache (7-day TTL, .gitignored)
│   ├── news/                         # News article cache (weekly TTL, .gitignored)
│   └── gee/                          # GEE satellite image cache (14-day TTL, .gitignored)
│
├── output/
│   ├── reports/                       # Generated PDF executive summaries
│   ├── monitoring/                    # Weekly monitoring JSON (used by momentum analyzer)
│   └── scraper_cache/                 # Market price cache (24h) + price_history/ JSONL archive
│
├── run_weekly_java_monitor.py         # Main entry point — runs all 29 regions + emails report
├── run_weekly_cron.py                 # Cron wrapper with email and error handling
├── .env                              # GMAIL_APP_PASSWORD, GEE project ID (not in git)
└── config/config.yaml                # System configuration
```

---

## 📚 Documentation

This repository includes comprehensive documentation organized hierarchically:

### Core Documentation

1. **[README.md](README.md)** (this file) - System overview, quick start, and value proposition
2. **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step setup and usage guide
3. **[TECHNICAL_SCORING_DOCUMENTATION.md](TECHNICAL_SCORING_DOCUMENTATION.md)** - Single source of truth for all technical details

### Feature-Specific Documentation (v2.6-alpha)

4. **[BENCHMARK_UPDATE_PROCEDURE.md](BENCHMARK_UPDATE_PROCEDURE.md)** - Quarterly benchmark maintenance guide
   - 4-week timeline for BPS/BI data integration
   - Data source weighting (60% official, 25% scraped, 15% commercial)
   - Confidence scoring and emergency update protocols
   
5. **[OFFICIAL_DATA_SOURCES_RESEARCH.md](OFFICIAL_DATA_SOURCES_RESEARCH.md)** - BPS/BI API research
   - BPS REST API documentation and integration approach
   - Province-to-city mapping (29 regions → 6 provinces)
   - Decision matrix: manual vs automated updates
   - Phase 3 automation roadmap

6. **[WEB_SCRAPING_DOCUMENTATION.md](WEB_SCRAPING_DOCUMENTATION.md)** - Multi-source scraping system
   - 3-tier fallback system (live → cache → benchmark)
   - Retry logic and timeout handling
   - Cache management and data freshness

### Strategic Roadmaps

7. **[MARKET_INTELLIGENCE_ROADMAP.md](MARKET_INTELLIGENCE_ROADMAP.md)** - Phase 2A/2B development plan
8. **[PHASE1_VALIDATION_CHECKLIST.md](PHASE1_VALIDATION_CHECKLIST.md)** - System validation checklist

**Documentation Hierarchy:**
```
README.md (Overview)
    ├─> QUICKSTART.md (Setup)
    └─> TECHNICAL_SCORING_DOCUMENTATION.md (Technical Reference)
            ├─> BENCHMARK_UPDATE_PROCEDURE.md (Quarterly Maintenance)
            ├─> OFFICIAL_DATA_SOURCES_RESEARCH.md (API Research)
            └─> WEB_SCRAPING_DOCUMENTATION.md (Scraping System)
```

**For setup instructions:** See [QUICKSTART.md](QUICKSTART.md)  
**For algorithm details:** See [TECHNICAL_SCORING_DOCUMENTATION.md](TECHNICAL_SCORING_DOCUMENTATION.md)  
**For benchmark updates:** See [BENCHMARK_UPDATE_PROCEDURE.md](BENCHMARK_UPDATE_PROCEDURE.md)

---

## 🌍 Current Coverage

**29 Regions Across Java Island:**

| Region | Priority | Focus |
|--------|----------|-------|
| Jakarta Metro (4 regions) | High | Urban expansion |
| Bandung Metro (2 regions) | High | Transportation hubs |
| Semarang-Yogyakarta-Solo (6 regions) | High | Infrastructure corridors |
| Surabaya Metro (4 regions) | High | Industrial development |
| Banten Industrial Corridor (3 regions) | Medium | Port-adjacent zones |
| Regional Hubs (10 regions) | Medium | Emerging markets |

**Total Monitored Area:** ~8,500 km²  
**Analysis Frequency:** Weekly  
**Average Processing Time:** 3 minutes per region

---

## 🔍 Example Output

**Sample Investment Recommendation:**

```
Region: Solo Airport Corridor
Score: 78.5/100 (85% confidence)
Recommendation: ✅ BUY

Financial Projection:
├─ Current Land Value: Rp 5,692,500/m²
├─ 3-Year Projection: Rp 8,257,381/m²
├─ Projected ROI: 34.4% (3-year)
├─ Recommended Plot: 2,000 m²
├─ Total Investment: Rp 11,385,000,000
└─ Data Sources: Lamudi (live), OSM, Sentinel-2 + Sentinel-1 SAR

Satellite Analysis (Fused Optical + SAR):
├─ Optical: 1,234 changes | SAR: 987 radar changes
├─ Fused: 1,135 changes (60/40 weighted, +10% confidence)
├─ SAR Construction: 342 pixels (VV +1.8dB)
└─ Fusion Mode: optical+sar_fusion

News Catalyst: 1.10x multiplier
├─ Articles Found: 4 (3 positive, 1 neutral)
├─ Top Keywords: toll road, airport, highway
└─ Summary: Active development zone covering toll road, airport

Infrastructure:
├─ Major Highway: 2.3 km away
├─ Nearest Airport: 8.5 km (Solo International)
└─ Railway Access: Yes (3 stations within 15 km)

Rationale: Strong development activity near new airport with excellent
infrastructure access. SAR confirms construction through cloud cover.
News catalyst boosts score with 4 positive infrastructure articles.
```

---

## ⚙️ Configuration

Key settings in `config/config.yaml`:

```yaml
# Satellite Analysis
satellite:
  max_cloud_coverage: 20        # Maximum acceptable cloud cover (%)
  image_scale: 10               # Resolution in meters (Sentinel-2)

# Web Scraping (Financial Data)
web_scraping:
  enabled: true                 # Enable live price scraping
  cache_expiry_hours: 24        # Cache validity period
  sites:
    lamudi: enabled
    rumah_com: enabled

# Infrastructure Analysis
infrastructure:
  api_timeout: 30               # OpenStreetMap API timeout (seconds)
  search_radii:
    highways_km: 25
    airports_km: 100
    railways_km: 25

# Google Earth Engine
gee_project: "your-project-id"  # REQUIRED: Your GCP project ID
```

---

## 🔧 Development

### Running Tests

```bash
pytest tests/ -v
pytest --cov=src tests/  # With coverage
```

### Code Quality

```bash
black src/      # Format code
pylint src/     # Lint
mypy src/       # Type checking
```

### Adding New Regions

Edit `src/indonesia_expansion_regions.py`:

```python
from src.indonesia_expansion_regions import ExpansionRegion

ExpansionRegion(
    name="New Region Name",
    slug="new_region_slug",
    bbox=(west, south, east, north),  # Decimal degrees
    priority=1,  # 1=high, 2=medium, 3=emerging
    island="java",
    focus="infrastructure"  # infrastructure/industrial/urban/tourism
)
```

---

## 🐛 Troubleshooting

**Earth Engine Authentication Failed:**
```bash
earthengine authenticate
python -c "import ee; ee.Initialize(); print('✅ Success')"
```

**OSM API Timeouts:**  
Increase timeout in `config.yaml`: `infrastructure.api_timeout: 60`

**Memory Errors:**  
Reduce resolution: `satellite.image_scale: 30` (from 10)

**No Satellite Images Found:**
- Increase `max_cloud_coverage` threshold
- Check region coordinates are within Sentinel-2 coverage

For detailed troubleshooting, see **[TECHNICAL_SCORING_DOCUMENTATION.md](TECHNICAL_SCORING_DOCUMENTATION.md)**.

---

## 📦 Dependencies

**Core:**
- `earthengine-api` - Satellite imagery
- `requests` - HTTP requests
- `beautifulsoup4` - Web scraping
- `reportlab` - PDF generation
- `pyyaml` - Configuration

**Analysis:**
- `numpy`, `pandas` - Data processing
- `geopandas`, `shapely` - Geospatial

Full list: [requirements.txt](requirements.txt)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 👤 Author

**Chris Moore**  
GitHub: [@MIFUNEKINSKi](https://github.com/MIFUNEKINSKi)  
Project: [CloudClearingAPI](https://github.com/MIFUNEKINSKi/CloudClearingAPI)

---

## 🙏 Acknowledgments

- **Google Earth Engine** - Satellite imagery platform
- **OpenStreetMap** - Infrastructure data contributors
- **Sentinel-2 (ESA/Copernicus)** - Free optical satellite imagery program
- **Sentinel-1 (ESA/Copernicus)** - Free SAR radar satellite imagery program
