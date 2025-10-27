# CloudClearingAPI Documentation Index
**Version:** 2.6-alpha  
**Last Updated:** October 25, 2025

---

## 📋 Quick Navigation

**Getting Started?** → Start with [README.md](#1-readmemd) then [QUICKSTART.md](#2-quickstartmd)  
**Technical Details?** → See [TECHNICAL_SCORING_DOCUMENTATION.md](#3-technical_scoring_documentationmd)  
**Maintaining Benchmarks?** → See [BENCHMARK_UPDATE_PROCEDURE.md](#4-benchmark_update_proceduremd)  
**Understanding Scraping?** → See [WEB_SCRAPING_DOCUMENTATION.md](#6-web_scraping_documentationmd)

---

## 📚 Documentation Structure

```
CloudClearingAPI Documentation
│
├── Core Documentation (Start Here)
│   ├── README.md ........................... System overview & value proposition
│   ├── QUICKSTART.md ....................... Setup guide (10-15 minutes)
│   └── TECHNICAL_SCORING_DOCUMENTATION.md .. Complete technical reference (3000+ lines)
│
├── Feature-Specific Documentation (v2.6-alpha)
│   ├── BENCHMARK_UPDATE_PROCEDURE.md ....... Quarterly benchmark maintenance
│   ├── OFFICIAL_DATA_SOURCES_RESEARCH.md ... BPS/BI API research & integration
│   └── WEB_SCRAPING_DOCUMENTATION.md ....... Multi-source scraping system
│
├── Strategic Roadmaps
│   ├── MARKET_INTELLIGENCE_ROADMAP.md ...... Phase 2A/2B development plan
│   └── PHASE1_VALIDATION_CHECKLIST.md ...... System validation checklist
│
└── Implementation Guides
    ├── IMPROVEMENTS_OCT18_2025.md .......... Recent feature changelog
    └── MONITORING_RUN_STATUS.md ............ Weekly monitoring execution logs
```

---

## 1. README.md

**Purpose:** System overview, quick start, and value proposition

**Key Sections:**
- System overview: What CloudClearingAPI does
- Scoring philosophy: Activity Score → Multipliers → Confidence
- Quick start: Installation and first run
- Example output: Sample investment recommendation
- Troubleshooting: Common issues and solutions

**Target Audience:** New users, investors, project overview

**Read Time:** 10 minutes

**Prerequisites:** None

---

## 2. QUICKSTART.md

**Purpose:** Step-by-step setup and usage guide

**Key Sections:**
- Prerequisites (Python, GEE account, GCP project)
- Installation steps
- Configuration guide (`config.yaml`)
- Running first analysis
- Understanding output (PDF reports, JSON data)
- Common issues and fixes

**Target Audience:** Developers setting up the system

**Read Time:** 15 minutes

**Prerequisites:** Basic Python knowledge, command line familiarity

**Related Files:**
- `config/config.yaml` - System configuration
- `requirements.txt` - Python dependencies
- `run_weekly_java_monitor.py` - Main execution script

---

## 3. TECHNICAL_SCORING_DOCUMENTATION.md

**Purpose:** Single source of truth for all technical details (3000+ lines)

**Key Sections:**

### Architecture & System Overview
- 3-stage pipeline: Core Scoring → Financial Projection → PDF Generation
- Data flow diagrams
- File responsibilities

### Version History (Reverse Chronological)
- **v2.6-alpha (Phase 2A)**: Market Intelligence Foundation (8/11 complete)
  - Phase 2A.1: Regional Tier Classification
  - Phase 2A.2: Tier-Based Benchmark Integration
  - Phase 2A.3: RVI Calculation Implementation
  - Phase 2A.4: RVI Scoring Output Integration
  - Phase 2A.5: Multi-Source Scraping Fallback
  - Phase 2A.6: Request Hardening
  - Phase 2A.7: Benchmark Update Procedure
  - Phase 2A.8: Research Official Data Sources
- **v2.5**: Infrastructure Scoring Standardization
- **v2.4.1**: Confidence Multiplier Refinement
- **v2.4**: Financial Metrics Engine Integration

### Scoring System Details
- Activity Score calculation (0-40 points)
- Infrastructure Multiplier (0.8x - 1.3x)
- Market Multiplier (0.85x - 1.4x)
- Confidence Score (40-95%)
- Relative Value Index (RVI) formula

### Market Intelligence (v2.6-alpha)
- Regional tier classification (4 tiers, 29 regions)
- Tier-based benchmarks and context
- RVI calculation and interpretation
- Multi-source scraping fallback (3-tier cascading)
- Request hardening (retry logic, exponential backoff)

### Development Workflows
- Running full analysis
- Testing individual components
- Adding new regions
- Configuration patterns

**Target Audience:** Developers, technical contributors, algorithm auditors

**Read Time:** 2-3 hours (comprehensive reference)

**Prerequisites:** Understanding of CloudClearingAPI's purpose and basic architecture

**Related Files:**
- `src/core/corrected_scoring.py` - Investment scoring engine
- `src/core/financial_metrics.py` - ROI & land value projections
- `src/core/change_detector.py` - Satellite change detection
- `src/indonesia_expansion_regions.py` - 29 monitored regions

---

## 4. BENCHMARK_UPDATE_PROCEDURE.md

**Purpose:** Complete guide for quarterly benchmark maintenance (950+ lines)

**Key Sections:**

### Process Overview
- Quarterly timeline (4-week process)
- Deadlines: January 15, April 15, July 15, October 15
- Data source priorities and weighting

### Data Collection
- **BPS (Badan Pusat Statistik)**: Property price indices (60% weight)
  - PDF/Excel download procedures
  - Province-level data extraction
  - Index-to-price conversion
- **Bank Indonesia**: Quarterly property reports (included in 60% official weight)
  - "Survei Harga Properti Residensial"
  - City-level price extraction
- **Web Scraping**: Live market data (25% weight)
  - Lamudi, Rumah.com, 99.co
  - Validation criteria (minimum 20 listings)
- **Commercial Reports**: Colliers, JLL (15% weight)
  - Optional, budget-dependent
  - Quality validation

### Calculation Methodology
- Weighted benchmark formula
- Confidence scoring algorithm
- Tier-wide adjustments
- Regional override decision criteria

### Emergency Updates
- Infrastructure event triggers (new airports, highways)
- Economic shock protocols (>20% currency devaluation)
- Market anomaly handling (>50% regions flagged)

### Automation Roadmap
- **Phase 1 (Current)**: Manual process (6-8 hours/quarter)
- **Phase 2 (Future)**: Scripted with single command (2-3 hours)
- **Phase 3 (Vision)**: Fully automated with BPS/BI API (30 min review)

**Target Audience:** Data analysts, benchmark maintainers, quarterly review teams

**Read Time:** 1 hour

**Prerequisites:** Understanding of benchmark system, data source weighting

**Related Files:**
- `src/core/market_config.py` - Benchmark storage
- `BENCHMARK_UPDATE_LOG.md` - Historical update records
- `OFFICIAL_DATA_SOURCES_RESEARCH.md` - BPS/BI API details

**Update Frequency:** Review quarterly, update as needed

---

## 5. OFFICIAL_DATA_SOURCES_RESEARCH.md

**Purpose:** BPS/BI API research and integration approach (8500+ lines)

**Key Sections:**

### Research Findings
- **BPS API**: ✅ Available (REST API with free registration)
  - Base URL: `https://webapi.bps.go.id/v1/api/`
  - Province-level property price indices (quarterly)
  - Coverage: 6 Java provinces
  - **Limitation**: Province-level only (need city-level for 29 regions)
  
- **Bank Indonesia API**: ❌ Not available (404 error)
  - No public API for property data
  - Manual PDF/Excel downloads required

### BPS API Documentation
- Endpoint structure and authentication
- Dynamic Data API (property indices)
- SIMDASI API (regional statistics)
- Province-to-city mapping (29 regions → 6 provinces)
- API registration process

### Integration Approach
- **Current Strategy**: Manual quarterly process (Phase 1)
- **Decision Rationale**: Granularity gap, data quality, low ROI
- **Future Phase 3**: BPS API as validation layer
  - Provincial trend validation (detect >5% deviations)
  - Weighted approach: 40% provincial index + 60% scraped city median
  - Automation when: CloudClearingAPI scales beyond Java

### Implementation Roadmap
- **Phase 2 (Scripted)**: BPS API fetch + automated scraping (60 hour effort)
- **Phase 3 (Semi-Automated)**: Quarterly cron job (70-80% automation)
- Code examples: `BPSAPIClient` implementation
- Testing suite for API connectivity

**Target Audience:** API integration developers, data engineers, Phase 3 planners

**Read Time:** 2 hours (comprehensive reference)

**Prerequisites:** Understanding of BPS/BI data sources, API development knowledge

**Related Files:**
- `BENCHMARK_UPDATE_PROCEDURE.md` - Quarterly maintenance process
- `src/core/market_config.py` - Benchmark storage

**Update Frequency:** Review when BPS API capabilities change or Phase 3 begins

---

## 6. WEB_SCRAPING_DOCUMENTATION.md

**Purpose:** Multi-source scraping system technical reference (774 lines)

**Key Sections:**

### Architecture
- 3-tier cascading fallback: Lamudi → Rumah.com → 99.co
- Cache-first strategy (Priority 4: cached data <24-48h)
- Static benchmarks (Priority 5: last resort)

### Components
- **Base Scraper** (`base_scraper.py`)
  - User-agent rotation (5 agents)
  - Rate limiting (2s between requests)
  - Retry logic with exponential backoff (Phase 2A.6)
  - Request timeout handling (15s primary, 30s fallback)
  
- **Lamudi Scraper** (`lamudi_scraper.py`)
  - CSS selector parsing
  - Indonesian price format handling (Miliar/Juta/Ribu)
  
- **Rumah.com Scraper** (`rumah_scraper.py`)
  - JSON API endpoint parsing
  - Size normalization (m²/hectare conversion)
  
- **99.co Scraper** (`99_scraper.py`)
  - Province-based URL mapping
  - Flexible price extraction

### Orchestrator (`scraper_orchestrator.py`)
- Multi-source coordination
- Cascading logic implementation
- Confidence scoring (85% live, 75-85% cached, 50% benchmark)
- Cache management (24-48h expiry)

### Retry Logic (Phase 2A.6)
- Exponential backoff: 1s → 2s → 4s → ... (max 30s)
- Smart retry strategy: retries 5xx server errors, skips 4xx client errors
- Jitter (±20%) to prevent thundering herd
- Config-driven settings (`config.yaml`)

### Testing
- `test_multi_source_fallback.py` - 3-tier fallback validation
- `test_request_hardening.py` - Retry logic and timeout handling
- Mock server tests for all scrapers

**Target Audience:** Scraping system developers, data collection engineers

**Read Time:** 45 minutes

**Prerequisites:** Understanding of web scraping, HTTP requests, caching

**Related Files:**
- `src/scrapers/base_scraper.py` - Base scraper class
- `src/scrapers/scraper_orchestrator.py` - Multi-source coordination
- `config/config.yaml` - Scraping configuration
- `output/scraper_cache/` - Cached scraping results

**Update Frequency:** Review when adding new scrapers or modifying retry logic

---

## 7. MARKET_INTELLIGENCE_ROADMAP.md

**Purpose:** Phase 2A/2B development plan

**Key Sections:**
- Phase 2A: Market Intelligence Foundation (11 phases)
  - Current progress: 8/11 complete (73%)
- Phase 2B: RVI Integration into Scoring
- Success criteria and validation gates

**Target Audience:** Project managers, development team, stakeholders

**Read Time:** 30 minutes

**Update Frequency:** Weekly during active development

---

## 8. PHASE1_VALIDATION_CHECKLIST.md

**Purpose:** System validation checklist

**Key Sections:**
- Pre-deployment validation steps
- Test coverage requirements
- Data quality checks

**Target Audience:** QA engineers, deployment teams

**Read Time:** 20 minutes

**Update Frequency:** Before major releases

---

## 🔄 Documentation Maintenance

### Update Responsibilities

| Document | Owner | Update Frequency | Last Updated |
|----------|-------|------------------|--------------|
| README.md | Product Lead | After major features | Oct 25, 2025 |
| QUICKSTART.md | DevOps | After setup changes | Oct 6, 2025 |
| TECHNICAL_SCORING_DOCUMENTATION.md | Tech Lead | After each phase | Oct 25, 2025 |
| BENCHMARK_UPDATE_PROCEDURE.md | Data Team | Quarterly reviews | Oct 19, 2025 |
| OFFICIAL_DATA_SOURCES_RESEARCH.md | Data Team | When APIs change | Oct 25, 2025 |
| WEB_SCRAPING_DOCUMENTATION.md | Scraping Team | After scraper changes | Oct 25, 2025 |

### Cross-Reference Checklist

When updating documentation, ensure consistency across:

- ✅ README.md feature list matches TECHNICAL_SCORING_DOCUMENTATION.md version history
- ✅ QUICKSTART.md setup steps reference correct config.yaml sections
- ✅ BENCHMARK_UPDATE_PROCEDURE.md data sources align with OFFICIAL_DATA_SOURCES_RESEARCH.md
- ✅ WEB_SCRAPING_DOCUMENTATION.md changelog matches Phase 2A milestones
- ✅ All file paths and function names are current
- ✅ Version numbers consistent across all docs

---

## 📖 Reading Paths by Role

### New User (Investor)
1. README.md (10 min) - Understand the system
2. QUICKSTART.md (15 min) - Get it running
3. Sample PDF report - See output example

### Developer (Contributing)
1. README.md (10 min) - System overview
2. TECHNICAL_SCORING_DOCUMENTATION.md (2 hours) - Deep dive
3. Relevant feature docs (WEB_SCRAPING, BENCHMARK_UPDATE) - As needed
4. Code exploration with documentation reference

### Data Analyst (Benchmark Maintenance)
1. README.md (10 min) - System context
2. BENCHMARK_UPDATE_PROCEDURE.md (1 hour) - Process guide
3. OFFICIAL_DATA_SOURCES_RESEARCH.md (2 hours) - Data sources
4. Quarterly execution with procedure reference

### QA Engineer (Testing)
1. TECHNICAL_SCORING_DOCUMENTATION.md (focus on version history)
2. PHASE1_VALIDATION_CHECKLIST.md
3. Test files (`tests/` directory)
4. Feature-specific docs for test case development

---

## 🆘 Help & Support

**Can't find what you're looking for?**

1. **Check TECHNICAL_SCORING_DOCUMENTATION.md** - 3000+ lines covering nearly everything
2. **Search within docs** - Use Ctrl+F / Cmd+F for keywords
3. **Check file headers** - Most docs have detailed table of contents
4. **Review code comments** - Implementation files are heavily documented

**Still stuck?**
- Review recent changelog in IMPROVEMENTS_OCT18_2025.md
- Check test files for usage examples
- Consult inline code documentation (docstrings)

---

**Last Updated:** October 25, 2025  
**Documentation Version:** 2.6-alpha (Phase 2A.9)  
**Total Documentation:** ~15,000+ lines across 8 major documents
