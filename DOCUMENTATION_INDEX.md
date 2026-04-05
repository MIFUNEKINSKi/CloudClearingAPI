# CloudClearingAPI Documentation Index
**Version:** 2.14.0  
**Last Updated:** April 5, 2026

---

## 📋 Quick Navigation

**Getting Started?** → Start with [README.md](#1-readmemd) then [QUICKSTART.md](#2-quickstartmd)  
**Technical Details?** → See [TECHNICAL_SCORING_DOCUMENTATION.md](#3-technical_scoring_documentationmd)  
**Maintaining Benchmarks?** → See [BENCHMARK_UPDATE_PROCEDURE.md](#4-benchmark_update_proceduremd)  
**Understanding Scraping?** → See [WEB_SCRAPING_DOCUMENTATION.md](#6-web_scraping_documentationmd)  
**Development Roadmap?** → See [DEVELOPMENT_ROADMAP.md](#9-development_roadmapmd)

---

## 📚 Documentation Structure

```
CloudClearingAPI Documentation
│
├── Core Documentation (Start Here)
│   ├── README.md ........................... System overview, scoring philosophy, quick start
│   ├── QUICKSTART.md ....................... Setup guide (10-15 minutes)
│   └── TECHNICAL_SCORING_DOCUMENTATION.md .. Complete technical reference
│
├── Feature-Specific Documentation
│   ├── BENCHMARK_UPDATE_PROCEDURE.md ....... Quarterly benchmark maintenance
│   ├── OFFICIAL_DATA_SOURCES_RESEARCH.md ... BPS/BI API research & integration
│   └── WEB_SCRAPING_DOCUMENTATION.md ....... Multi-source scraping system
│
├── Operational Documentation
│   ├── CHANGELOG.md ........................ Full version history
│   └── DEVELOPMENT_ROADMAP.md .............. Current priorities and future plans
│
├── docs/ (Modular Documentation Hub)
│   ├── README.md ........................... Documentation hub with navigation
│   ├── architecture/ ...................... Scoring, data flow, components, config
│   ├── api/ ............................... API references for core modules
│   ├── deployment/ ........................ Docker, Terraform, Step Functions, **cost-aware-aws.md**
│   ├── testing/ ........................... Test strategies and coverage
│   ├── changelog/ ......................... Detailed release notes
│   └── roadmap/ ........................... Strategic development plans
│
└── archived_bloat/historical_reports/ ..... Superseded roadmaps + Oct–Nov 2025 milestone reports (see README inside)
```

---

## 1. README.md

**Purpose:** System overview, scoring philosophy, quick start, and value proposition

**Key Sections:**
- Scoring philosophy: Activity × Infrastructure × Market × News × Confidence × Momentum
- Detailed scoring component explanations with multiplier tables
- System architecture diagram
- 65-region coverage breakdown by island
- Quick start guide
- Example investment recommendation output
- Troubleshooting

**Target Audience:** New users, investors, project overview

**Read Time:** 15 minutes

---

## 2. QUICKSTART.md

**Purpose:** Step-by-step setup and usage guide

**Key Sections:**
- Prerequisites (Python 3.10+, GEE account, GCP project)
- Installation steps
- Configuration guide (`config.yaml`)
- Running first analysis (`run_weekly_java_monitor.py` or `--all` for 65 regions)
- Understanding output (PDF reports, JSON data, email delivery)

**Target Audience:** Developers setting up the system

---

## 3. TECHNICAL_SCORING_DOCUMENTATION.md

**Purpose:** Single source of truth for all technical scoring details

**Key Sections:**
- Architecture & system overview (3-stage pipeline)
- Scoring system details (Activity, Infrastructure, Market, News, Confidence, Momentum)
- Relative Value Index (RVI) formula
- Market intelligence (regional tier classification)
- Historical version changes

**Target Audience:** Developers, technical contributors, algorithm auditors

**Read Time:** 2-3 hours (comprehensive reference)

---

## 4. BENCHMARK_UPDATE_PROCEDURE.md

**Purpose:** Complete guide for quarterly benchmark maintenance

**Key Sections:**
- Quarterly timeline (4-week process, Jan/Apr/Jul/Oct 15th deadlines)
- Data source weighting: 60% official (BPS/BI), 25% web scraping, 15% commercial
- Emergency update protocols
- Automation roadmap (manual → scripted → fully automated)

**Target Audience:** Data analysts, benchmark maintainers

---

## 5. OFFICIAL_DATA_SOURCES_RESEARCH.md

**Purpose:** BPS/BI API research and integration approach

**Key Sections:**
- BPS API: Available (REST, province-level property indices)
- Bank Indonesia API: Not publicly available
- Province-to-city mapping
- Integration approach and future automation

**Target Audience:** API integration developers, data engineers

---

## 6. WEB_SCRAPING_DOCUMENTATION.md

**Purpose:** Multi-source scraping system technical reference

**Key Sections:**
- 3-tier cascading fallback: Lamudi → 99.co → cache → benchmarks
- Scraper components (Lamudi, 99.co, Rumah.com)
- JSONL price history archive for trend calculation
- Retry logic with exponential backoff

**Target Audience:** Scraping system developers

---

## 7. CHANGELOG.md

**Purpose:** Complete version history from v2.0 through v2.12.1

**Key Versions:**
- v2.12.1 (Apr 2026): Full 65-region run, infrastructure/market/drift fixes
- v2.12 (Mar 2026): Decision matrix PDF, expanded to 65 regions
- v2.11 (Mar 2026): SAR fusion, news catalyst, price momentum, auto-email
- v2.10 (Feb 2026): Indonesia expansion (39 → 51 regions)
- v2.9.1 (Nov 2025): Docker, Terraform, Step Functions, GEE caching
- v2.8.x (Oct 2025): Market data restoration, OSM caching
- v2.7.0 (Oct 2025): Budget-driven investment sizing
- v2.6-beta (Oct 2025): RVI-aware market multiplier, airport premium
- v2.6-alpha (Oct 2025): Regional tiers, RVI, multi-source scraping
- v2.0-2.5 (Oct 2025): Corrected scoring, infrastructure standardization

---

## 8. docs/ Directory

**Purpose:** Modular documentation hub organized by topic

See **[docs/README.md](docs/README.md)** for the full navigation index covering architecture, API references, deployment guides, testing strategies, and roadmap.

---

## 9. DEVELOPMENT_ROADMAP.md

**Purpose:** Current development priorities and future plans

**Key Sections:**
- What's been completed (v2.0 through v2.12.1)
- What's working and what still needs development
- Immediate priorities (scraper reliability, scoring calibration, testing)
- Future plans (CI/CD, monitoring dashboard, ML augmentation)

---

## 🔄 Documentation Maintenance

### Update Responsibilities

| Document | Update Frequency | Last Updated |
|----------|------------------|--------------|
| README.md | After major features | April 5, 2026 |
| CHANGELOG.md | After each release | April 5, 2026 |
| DEVELOPMENT_ROADMAP.md | After each development cycle | April 5, 2026 |
| docs/README.md | After major features | April 5, 2026 |
| DOCUMENTATION_INDEX.md | After doc structure changes | April 5, 2026 |
| TECHNICAL_SCORING_DOCUMENTATION.md | After scoring changes | October 25, 2025 |
| BENCHMARK_UPDATE_PROCEDURE.md | Quarterly reviews | October 25, 2025 |
| WEB_SCRAPING_DOCUMENTATION.md | After scraper changes | October 25, 2025 |

### Cross-Reference Checklist

When updating documentation, ensure consistency across:

- ✅ README.md feature list matches CHANGELOG.md entries
- ✅ Version numbers consistent across all docs
- ✅ Region counts (currently 65) consistent everywhere
- ✅ All file paths and function names are current
- ✅ docs/README.md navigation links are valid

---

## 📖 Reading Paths by Role

### New User (Investor)
1. README.md (15 min) — Understand the system and scoring
2. QUICKSTART.md (15 min) — Get it running
3. Review a generated PDF report — See real output

### Developer (Contributing)
1. README.md (15 min) — System overview
2. TECHNICAL_SCORING_DOCUMENTATION.md (2 hours) — Deep dive
3. docs/ directory — Architecture, API, deployment guides
4. CHANGELOG.md — Understand version evolution

### Data Analyst (Benchmark Maintenance)
1. README.md (15 min) — System context
2. BENCHMARK_UPDATE_PROCEDURE.md (1 hour) — Process guide
3. OFFICIAL_DATA_SOURCES_RESEARCH.md (2 hours) — Data sources

---

**Last Updated:** April 4, 2026  
**Documentation Version:** 2.12.1
