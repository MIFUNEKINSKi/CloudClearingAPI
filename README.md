# CloudClearingAPI: Land Development Investment Intelligence

### What is CloudClearingAPI?

Investing in land development is challenging. Information is scattered, opportunities are hard to spot, and it's difficult to know if development activity translates into a profitable venture.

CloudClearingAPI solves this by acting as an **automated investment analyst**. It scans regions across Indonesia, transforming satellite imagery and market data into clear, actionable investment intelligence.

**This system empowers you to:**
* **📍 Pinpoint Development Hotspots:** Automatically detect where land is being cleared and construction is happening *right now*.
* **💰 Evaluate Financial Viability:** Go beyond just activity to see **projected ROI**, **estimated land values**, and **development costs** based on live market data.
* **🏗️ Assess Real-World Viability:** Understand if a region has the roads, ports, and other critical infrastructure needed to support growth.
* **📊 Make Data-Driven Decisions:** Receive a single, comprehensive investment score (0-100) and a detailed PDF report that summarizes everything you need to know.

---

## ✨ The Scoring Philosophy: From Activity to Opportunity

Our scoring system is designed to answer two fundamental questions every investor asks:

1.  **Where is the activity?** (The Activity Score)
2.  **Is this activity a profitable opportunity?** (The Financial & Contextual Multipliers)

The final score is a blend of these elements, ensuring that we recommend not just *busy* areas, but *valuable* ones.

**Final Score** = (Activity Score) × (Infrastructure Multiplier) × (Market Multiplier) × (Confidence Score)

---

## ⚙️ How the Scoring Works

### Part 1: The Activity Score (0-40 Points) - *Finding the Action*

This is the foundation of our analysis and is derived **entirely from satellite imagery**. It's our 'eye in the sky' that tells us where physical change is happening on the ground. We compare images from the last 7 days to the previous 7 days to find new development.

* **What We Look For:**
    * **Vegetation Loss (High Weight):** Forests or fields being cleared, a strong signal of future construction.
    * **New Construction (Highest Weight):** New buildings and urban areas appearing.
    * **Land Preparation (Medium Weight):** Bare earth being exposed for site preparation.

A region with significant, recent construction activity will receive the highest base scores.

### Part 2: Financial & Contextual Multipliers - *Is It a Good Deal?*

High activity is meaningless if the investment doesn't make financial sense. These multipliers adjust the Activity Score based on real-world financial and logistical factors.

#### 🏗️ **The Infrastructure Multiplier (0.8x - 1.3x)**
This multiplier answers: "Can this area support new development?" It assesses the quality of surrounding infrastructure from OpenStreetMap.

* **Note on Accuracy:** This component was recently overhauled to provide a more realistic analysis. It now correctly models the concept of **diminishing returns**—the first highway provides immense value, while the tenth adds much less.

| Infrastructure Score | Tier | Multiplier | Interpretation |
| :--- | :--- | :--- | :--- |
| **90-100** | Excellent | **1.30x** | World-class infrastructure, major hub. |
| **75-89** | Very Good | **1.15x** | Strong logistical and transport links. |
| **60-74** | Good | **1.00x** | Adequate for standard development. |
| **40-59** | Fair | **0.90x** | Basic infrastructure, potential limitations. |
| **< 40** | Poor | **0.80x** | Weak or missing infrastructure. |

#### 💰 **The Market Multiplier (0.85x - 1.40x)**
This is our most powerful feature. To determine the market context, we use a **cascading data system**:
1.  **Live Web Scraping:** First, we attempt to scrape live land prices from top Indonesian real estate portals like `Lamudi.co.id` and `Rumah.com`.
2.  **Cached Data:** If a live scrape isn't possible, we use data cached within the last 24-48 hours.
3.  **Regional Benchmarks:** As a final fallback, we use our internal database of historical price trends.

This live data feeds our **Market Multiplier**, which rewards regions with strong economic fundamentals.

| Annual Price Trend | Tier | Multiplier | Interpretation |
| :--- | :--- | :--- | :--- |
| **> 15%** | Booming | **1.40x** | Exceptional, high-growth market. |
| **8-15%** | Strong | **1.20x** | Very healthy market with strong demand. |
| **2-8%** | Stable | **1.00x** | Steady, sustainable growth. |
| **0-2%** | Stagnant | **0.95x** | Slow growth, limited momentum. |
| **< 0%** | Declining | **0.85x** | Market is contracting. |

### Part 3: The Reality Check (Confidence Score)

This score ensures our system is honest about the quality of its own data. A low confidence score will reduce the final investment score, preventing us from making a strong recommendation based on incomplete information.

* **How it's calculated:** It's a weighted average of our confidence in each data source:
    * **Satellite Data (50% weight):** Higher confidence with recent, cloud-free images.
    * **Infrastructure Data (30% weight):** Highest with live OSM data, lower with regional fallbacks.
    * **Market Data (20% weight):** Highest with live-scraped prices, lowest with static benchmarks.

For a complete breakdown of the formulas and data sources, see our full [Technical Scoring Documentation](TECHNICAL_SCORING_DOCUMENTATION.md).

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

The system works as a data processing pipeline, taking raw data sources and refining them into a final, actionable report.

```
Data Inputs
├── Sentinel-2 Satellite Imagery (Google Earth Engine)
├── OpenStreetMap Infrastructure Data
└── Indonesian Real Estate Websites (Lamudi, Rumah.com)
     ↓
Core Analysis Engines
├── Activity Scoring Engine (corrected_scoring.py)
│   └── Converts satellite changes → Base Score (0-40)
└── Financial Projection Engine (financial_metrics.py)
    └── Estimates ROI, land values, development costs
     ↓
Aggregated Intelligence
├── Final Investment Score (0-100)
├── Financial Projections (ROI, land values)
├── Confidence Rating (40-95%)
└── BUY/WATCH/PASS Recommendation
     ↓
Final Output
└── Automated PDF Report (Executive Summary + Region Details)
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
│   │   ├── corrected_scoring.py       # Investment scoring engine
│   │   ├── financial_metrics.py       # ROI & land value projections
│   │   ├── change_detector.py         # Satellite change detection
│   │   ├── infrastructure_analyzer.py # Infrastructure analysis
│   │   └── pdf_report_generator.py    # Report generation
│   ├── scrapers/
│   │   ├── lamudi_scraper.py          # Lamudi.co.id scraper
│   │   ├── rumah_scraper.py           # Rumah.com scraper
│   │   └── scraper_orchestrator.py    # Scraping coordination
│   └── indonesia_expansion_regions.py # 29 monitored regions
│
├── config/
│   └── config.yaml                    # System configuration
│
├── output/
│   ├── reports/                       # Generated PDF reports
│   ├── monitoring/                    # JSON analysis data
│   └── scraper_cache/                 # Cached price data
│
├── run_weekly_java_monitor.py         # Main execution script
├── QUICKSTART.md                      # Detailed setup guide
└── TECHNICAL_SCORING_DOCUMENTATION.md # In-depth technical docs
```

---

## 📚 Documentation

This repository includes three comprehensive documents:

1. **README.md** (this file) - System overview and value proposition
2. **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step setup and usage guide
3. **[TECHNICAL_SCORING_DOCUMENTATION.md](TECHNICAL_SCORING_DOCUMENTATION.md)** - Complete technical reference

For setup instructions, see **[QUICKSTART.md](QUICKSTART.md)**.  
For algorithm details and API specs, see **[TECHNICAL_SCORING_DOCUMENTATION.md](TECHNICAL_SCORING_DOCUMENTATION.md)**.

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
└─ Data Sources: Lamudi (live), OSM, Sentinel-2

Activity Detected:
├─ Land Clearing: 1,234 changes (12.4 hectares)
├─ Active Construction: 18% of area
└─ Development Type: Infrastructure-led urban expansion

Infrastructure:
├─ Major Highway: 2.3 km away
├─ Nearest Airport: 8.5 km (Solo International)
└─ Railway Access: Yes (3 stations within 15 km)

Rationale: Strong development activity near new airport with excellent
infrastructure access. Market showing 12% annual appreciation.
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
- **Sentinel-2 (ESA/Copernicus)** - Free satellite imagery program
