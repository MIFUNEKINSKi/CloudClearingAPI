# CloudClearingAPI Development Roadmap
**Updated:** April 4, 2026  
**Current Version:** v2.12.1 (Full 65-Region Coverage + Scoring Fixes)

---

## 🎯 Project Vision & Portfolio Strategy

CloudClearingAPI is an automated land investment analyst for Indonesia that combines satellite imagery (Sentinel-2 optical + Sentinel-1 SAR radar), live market prices, infrastructure data, and development news into a single investment score for 65 regions.

**As a portfolio project, this demonstrates:**
- **Data pipeline engineering** — multi-source ingestion (satellite APIs, web scraping, OSM), transformation, and output generation
- **Cloud infrastructure** — AWS (ECS Fargate, Step Functions, S3, CloudWatch), Terraform IaC, Docker containerization
- **Data quality engineering** — benchmark drift monitoring, data validation, cascading fallback systems
- **Python at scale** — async processing, caching layers (GEE 14-day, OSM 7-day, scraper 24h), parallel batch execution
- **Orchestration** — Step Functions state machines, scheduled pipelines, error handling with retries
- **Analytics & reporting** — automated PDF generation, email delivery, investment scoring algorithms

---

## ✅ What's Working (v2.12.1)

| Capability | Status | DE Skill Demonstrated |
|-----------|--------|----------------------|
| **65-region data pipeline** | ✅ Working | ETL at scale (satellite + market + infra + news → scored output) |
| **Dual-sensor satellite analysis** | ✅ Working | API integration (Google Earth Engine), data fusion |
| **Web scraping pipeline** | ⚠️ Partial (40%) | Multi-source ingestion with cascading fallback |
| **Infrastructure analysis (OSM)** | ✅ Working | API integration, caching (7-day TTL), fallback database |
| **Investment scoring engine** | ✅ Working | Multi-factor data transformation pipeline |
| **PDF report generation** | ✅ Working | Automated reporting, data visualization |
| **Auto-email delivery** | ✅ Working | Pipeline output delivery |
| **JSONL price history** | ✅ Working | Append-only data lake pattern |
| **Benchmark drift monitoring** | ✅ Fixed | Data quality monitoring |
| **Docker containerization** | ✅ Defined | Container orchestration (not yet deployed) |
| **Terraform IaC** | ✅ Defined | Infrastructure as Code (5 modules, ~70 AWS resources) |
| **Step Functions orchestration** | ✅ Defined | Workflow orchestration (not yet deployed) |

### Latest Run (April 4, 2026)
- 65/65 regions analyzed in a single `--all` pass
- Improved score differentiation via infrastructure fallback and market heat fixes
- Drift monitoring operational

---

## 🔥 Development Priorities (DE-Focused)

Priorities ordered by what matters most for demonstrating data engineering competence to employers.

### Phase 1: Deploy to AWS (Highest Impact for Resume)

**Why:** The Docker, Terraform, and Step Functions code exists but has never been deployed. A live AWS deployment is the single highest-impact thing for proving cloud DE skills.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| Deploy Terraform infrastructure to AWS | 4-8h | **Terraform, AWS, IaC** | P0 |
| Push Docker image to ECR | 2-4h | **Docker, CI/CD, ECR** | P0 |
| Deploy ECS Fargate task | 4-8h | **ECS, Fargate, container orchestration** | P0 |
| Activate Step Functions weekly trigger | 2-4h | **Step Functions, EventBridge, orchestration** | P0 |
| Set up CloudWatch dashboards + alarms | 4-8h | **Monitoring, observability, CloudWatch** | P1 |
| Configure S3 data lake (raw/cache/reports/logs) | 2-4h | **S3, data lake architecture** | P1 |

**Deliverable:** Live pipeline running weekly on AWS, triggered by EventBridge, with CloudWatch monitoring. This alone makes CloudClearingAPI a top-tier DE portfolio project.

### Phase 2: dbt Data Transformation Layer

**Why:** dbt is one of the most in-demand DE skills. Adding a dbt layer that transforms the raw JSON pipeline output into analytics-ready datasets shows you understand modern data stack patterns.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| Set up dbt project with staging/marts layers | 8-12h | **dbt, data modeling, SQL** | P1 |
| Create staging models (satellite, infrastructure, market, news) | 4-8h | **SQL transformations, data modeling** | P1 |
| Create mart models (investment_scores, price_trends, regional_summary) | 4-8h | **Dimensional modeling, analytics engineering** | P1 |
| Add dbt tests (not_null, accepted_values, custom) | 4-8h | **Data quality, testing** | P1 |
| Generate dbt docs + lineage DAG | 2-4h | **Documentation, data lineage** | P2 |

**Deliverable:** `dbt run` transforms raw JSON → analytics-ready tables. `dbt docs serve` shows a lineage DAG. dbt tests validate data quality.

### Phase 3: CI/CD Pipeline (GitHub Actions)

**Why:** Every DE job requires CI/CD familiarity. A working pipeline that tests, builds, and deploys on push demonstrates DevOps maturity.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| GitHub Actions: test on push/PR | 4-8h | **CI/CD, GitHub Actions** | P1 |
| GitHub Actions: Docker build + push to ECR on merge | 4-8h | **Container registry, automated deployment** | P1 |
| GitHub Actions: Terraform validate on PR | 2-4h | **IaC validation** | P2 |
| Fix broken tests + add regression tests | 8-12h | **Testing, code quality** | P1 |
| Expand test coverage to ≥80% | 16-24h | **Testing strategy** | P2 |

**Deliverable:** Green CI badge on README, automated Docker builds, Terraform validation in CI.

### Phase 4: Data Quality & Observability

**Why:** Great Expectations + CloudWatch shows you think about data reliability, not just data movement.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| Great Expectations: data validation suites | 8-12h | **Data quality, Great Expectations** | P2 |
| CloudWatch custom metrics (processing time, cache hit rate, score distribution) | 4-8h | **Observability, monitoring** | P2 |
| SNS alerts for pipeline failures | 2-4h | **Alerting, operational excellence** | P2 |
| Data profiling + anomaly detection | 8-12h | **Data quality engineering** | P3 |

### Phase 5: Scraper Reliability & Market Data

**Why:** Improving from 40% to 60%+ live market data coverage shows real-world data engineering problem-solving.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| Fix 99.co scraper (request throttling) | 4-8h | **Web scraping, rate limiting** | P2 |
| Add alternative data source (Properti.com) | 8-12h | **Multi-source ingestion** | P2 |
| Build JSONL price history over time | Ongoing | **Append-only data lake** | P2 |
| Scoring formula calibration | 8-16h | **Data analysis, algorithm tuning** | P3 |

### Phase 6: Showcase & Demo

**Why:** A polished demo video + interactive dashboard makes the project interview-ready.

| Task | Effort | DE Skill | Priority |
|------|--------|----------|----------|
| Streamlit performance dashboard | 8-12h | **Data visualization, Streamlit** | P3 |
| MkDocs documentation site on GitHub Pages | 8-12h | **Technical documentation** | P3 |
| 5-minute architecture demo video | 4-8h | **Communication, presentation** | P3 |
| Architecture diagram (Mermaid/Lucidchart) | 2-4h | **System design** | P2 |

---

## 📊 Skills Coverage Matrix

How CloudClearingAPI maps to common DE job requirements:

| Requirement | CloudClearingAPI Feature | Status |
|-------------|-------------------------|--------|
| **Python** | Core pipeline, scoring engine, scrapers, async processing | ✅ Demonstrated |
| **SQL** | dbt models, data transformation | 🔲 Phase 2 |
| **AWS (S3, ECS, Step Functions)** | Full infrastructure defined in Terraform | ⚠️ Defined, not deployed |
| **Terraform** | 5 modules, ~70 AWS resources, multi-env support | ✅ Code exists |
| **Docker** | Multi-stage build, CI/CD pipeline | ✅ Code exists |
| **Data pipelines / ETL** | Satellite → scoring → PDF/email pipeline | ✅ Demonstrated |
| **dbt** | Transformation layer | 🔲 Phase 2 |
| **Airflow / Step Functions** | Step Functions state machine | ⚠️ Defined, not deployed |
| **Data quality** | Benchmark drift monitor, Great Expectations | ⚠️ Partial |
| **CI/CD** | GitHub Actions workflows | 🔲 Phase 3 |
| **Monitoring** | CloudWatch dashboards + alarms | 🔲 Phase 4 |
| **Web scraping** | Multi-source with cascading fallback | ✅ Demonstrated |
| **API integration** | Google Earth Engine, OSM Overpass | ✅ Demonstrated |
| **Data modeling** | Regional tiers, RVI, scoring multipliers | ✅ Demonstrated |

**Current coverage:** 6/14 demonstrated, 3/14 code exists but not deployed, 5/14 planned

**After Phase 1-3:** 12/14 demonstrated — covers virtually every DE job requirement

---

## ✅ Completed Features (Reference)

| Version | Date | Key Features |
|---------|------|-------------|
| **v2.12.1** | Apr 2026 | Full 65-region run, infrastructure fallback expansion, market heat fix, drift monitoring fix |
| **v2.12** | Mar 2026 | Decision matrix PDF, expanded to 65 regions, news scraper improvements |
| **v2.11** | Mar 2026 | SAR radar fusion, news catalyst scoring, JSONL price history, momentum analyzer, auto-email |
| **v2.10** | Feb 2026 | Indonesia expansion to 51 regions |
| **v2.9.1** | Nov 2025 | Docker, Terraform, Step Functions, GEE caching, async processing |
| **v2.8.x** | Oct 2025 | OSM caching, market data restoration |
| **v2.7.0** | Oct 2025 | Budget-driven investment sizing |
| **v2.6** | Oct 2025 | RVI-aware market multiplier, regional tiers, multi-source scraping |
| **v2.0-2.5** | Oct 2025 | Corrected scoring, infrastructure standardization, financial metrics |

---

## 🚨 Known Issues & Limitations

### Broken Scrapers
- **99.co:** HTTP 429 rate limiting
- **Rumah.com:** Requires JavaScript rendering (Selenium/Playwright)
- **Impact:** 60% of regions rely on static benchmark prices

### Infrastructure Not Deployed
- Docker, Terraform, and Step Functions are fully defined in code but have never been deployed to AWS
- This is the highest-priority gap for portfolio credibility

### Testing Gaps
- Test coverage ~30%, several stale tests
- No CI pipeline running

### Documentation Debt
- 48 markdown files in repo root — many are historical Oct 2025 completion reports
- `DEVELOPMENT_ROADMAP_V2.8.2.md` and `docs/roadmap/v2.9-to-v3.0.md` are stale (superseded by this file)

---

**Roadmap Owner:** Chris Moore  
**GitHub:** [@MIFUNEKINSKi](https://github.com/MIFUNEKINSKi)  
**Last Updated:** April 4, 2026
