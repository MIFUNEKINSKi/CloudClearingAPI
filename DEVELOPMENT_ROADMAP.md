# CloudClearingAPI Development Roadmap
**Updated:** April 27, 2026
**Current Version:** v2.16.3 (sar_only Cap + Confidence Provenance Fix — Merak Audit)

---

## 🎯 Project Vision & Portfolio Strategy

CloudClearingAPI is an automated land investment analyst for Indonesia that combines satellite imagery (Sentinel-2 optical + Sentinel-1 SAR radar), live market prices, infrastructure data, and development news into a single investment score for 65 regions.

**As a portfolio project, this demonstrates:**
- **Data pipeline engineering** — multi-source ingestion (satellite APIs, web scraping, OSM), transformation, and output generation
- **Cloud infrastructure** — AWS (ECS Fargate, Step Functions, S3, CloudWatch), Terraform IaC, Docker containerization
- **Data quality engineering** — benchmark drift monitoring, data validation, cascading fallback systems
- **Python at scale** — ThreadPoolExecutor parallel scoring, caching layers (GEE 14-day, OSM 7-day, SAR 14-day, scraper 24h, news 7-day), async batch execution
- **Orchestration** — Step Functions state machines, scheduled pipelines, error handling with retries
- **Analytics & reporting** — automated PDF generation, email delivery, investment scoring algorithms

---

## ✅ What's Working (v2.16.0)

| Capability | Status | DE Skill Demonstrated |
|-----------|--------|----------------------|
| **65-region data pipeline** | ✅ Working | ETL at scale (satellite + market + infra + news → scored output) |
| **Parallel scoring** | ✅ Working | ThreadPoolExecutor (4 workers), ~4x scoring speedup |
| **Dual-sensor satellite analysis** | ✅ Working | API integration (Google Earth Engine), data fusion |
| **GEE optical caching** | ✅ Working | 14-day cache avoids repeat satellite analysis |
| **Web scraping pipeline** | ✅ 64/65 live (98%) | Lamudi primary; price-outlier clamp (>5× benchmark); 99.co revived via cloudscraper (best-effort, ~1 region/run before CF rate-limits); Rumah.com unused |
| **Infrastructure analysis (OSM)** | ✅ 65/65 live | 17 fresh queries + 48 cache hits per run; 0 fallbacks. Email "live infrastructure" metric was incorrectly excluding cached OSM (now fixed). |
| **News pipeline** | ✅ 5 sources, 17+ regions matched | Jakarta Post, Kompas, Antara, Detik (infrastruktur + properti + berita-ekonomi-bisnis), CNBC Indonesia. Raw articles ~46→~79/run. Genuine 1.05x boost firing for ~6 regions per run. news_wow now populated. |
| **Market tier classification** | ✅ 100% | All 65 regions classified (T1: 10, T2: 18, T3: 29, T4: 8) |
| **Investment scoring engine** | ✅ Working | Multi-factor data transformation pipeline |
| **PDF with decision matrix** | ✅ Working | Market heat, data quality indicators, expanded columns |
| **Actionable email briefing** | ✅ Working | Portfolio overview, top BUY details with ROI/RVI, recommended actions |
| **Auto-email delivery** | ✅ Working | Pipeline output delivery |
| **Multi-layer caching** | ✅ Working | GEE (14d), SAR (14d), OSM (7d), news (7d), scraper (24h) |
| **JSONL price history** | ✅ Working | Append-only data lake pattern |
| **Benchmark drift monitoring** | ✅ Working | Dataclass-aware extraction, consistent alert schema, 65 regions tracked |
| **Docker containerization** | ✅ Defined | Container orchestration (not yet deployed) |
| **Terraform IaC** | ✅ Defined | Infrastructure as Code (**6 modules**, ~70 AWS resources); **no-NAT dev path** wired (`enable_nat_gateway = false` → public subnets + `AssignPublicIp` for ECS RunTask) |
| **Step Functions orchestration** | ✅ Defined | Workflow orchestration (not yet deployed) |

### Latest Run Metrics (Apr 27, 2026, post-SAR-cap + threshold recalibration)
- **65/65 regions** analyzed; runtime ~80–120 min
- **5 STRONG_BUY** (top-decile, all 100% conf, optical+lamudi-live): Merak Port (51.0), Solo Raya (50.4), Subang Patimban (50.4), Serang Cilegon (50.2), Cikarang (49.5)
- **12 BUY**, **24 WATCH**, **24 PASS** — disciplined screen
- **All 5 STRONG_BUYs carry SAR-dominant warning** (ratio 139–428×) — visible to investor before acting
- **65/65 live OSM** (17 fresh + 48 cache, 0 fallbacks)
- **Confidence range** 0.74–1.00; caps biting: SAR-only 0.84, clamped 0.80, low-listing 0.65
- **Drift avg +15.8%** (was +94.5%); 44 CRITICAL alerts
- **6 regions** with news boost (1.05x); **17 regions** with news_wow tracking
- **22 tier upgrades** vs prior run (post-recalibration) — surfaced in email
- **5 caching layers**: GEE (14d), SAR (14d), OSM (7d), news (2d), scraper (24h)

---

## 🔥 Development Priorities (DE-Focused)

Priorities ordered by what matters most for demonstrating data engineering competence to employers.

### Phase 1: Deploy to AWS (Highest Impact for Resume)

**Why:** The Docker, Terraform, and Step Functions code exists but has never been deployed. A live AWS deployment is the single highest-impact thing for proving cloud DE skills.

**Cost-conscious default (Apr 2026):** Use `enable_nat_gateway = false` in `terraform.tfvars` for portfolio dev — avoids NAT fees; ECS tasks launched by Step Functions use **public subnets** and **AssignPublicIp: ENABLED** so the weekly job can still reach GEE and the internet. See [`docs/deployment/cost-aware-aws.md`](docs/deployment/cost-aware-aws.md). Destroy the stack (`terraform destroy`) between interview seasons to go to **\$0**.

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
| Harden 99.co revival (residential proxy rotation, longer dwell, Playwright fallback) | 4-8h | **Web scraping, rate limiting** | P2 |
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
| **Terraform** | 6 modules, ~70 AWS resources, multi-env support, no-NAT dev path | ✅ Code exists |
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
| **v2.16.3** | Apr 25, 2026 | Plug sar_only loophole: cap fused at 500K (was uncapped → Merak saturated activity at 38); fix `satellite_data_source` provenance so SAR-only mode triggers the 0.84 confidence cap (was passing 'optical' even when fusion fell to sar_only); stat-calc timeout 60s → 120s (2/65 regions hit the wall on Apr 27 19:15 run). Net effect on Merak: 61.7 → ~51.2 |
| **v2.16.2** | Apr 25, 2026 | Drift tests cleaned (22 obsolete tier-only tests skipped, suite now 10/22/0); News supply expansion: Detik berita-ekonomi-bisnis + CNBC Indonesia (raw articles 46→79); AWS Terraform: 5 deprecated S3 lifecycle rules fixed (filter{} added) + recursive fmt; 99.co revived via cloudscraper (best-effort, ~1 region/run, breaker trips on first CF block) |
| **v2.16.1** | Apr 27, 2026 | SAR fusion 20× cap + threshold recalibration (49/42/33); tier transitions tracked week-over-week; thread-safe stats timeout (replaced broken signal.alarm); SAR construction/clearing band-name fix |
| **v2.16.0** | Apr 26, 2026 | STRONG_BUY tier (≥58 conf≥0.85); activity log-scaling (was step-cap); confidence hard caps for SAR-only/clamped; Detik Infrastruktur news source; per-region drift benchmarks (avg drift 94%→19%); momentum math bug fixed (was depressing all scores 15%); 5Y/3Y ROI apples-to-apples; news_wow loader bug fixed; Banten + Denpasar benchmark buckets; price-outlier clamp; SMTP preflight + webhook fallback |
| **v2.14.0** | Apr 2026 | Parallel scoring (ThreadPoolExecutor), news WoW rate of change, GEE optical cache integration, province-level scraper fallback, expanded PDF decision matrix (market heat + data quality), actionable email briefing |
| **v2.13.0** | Apr 2026 | Live data pipeline: OSM 0%→78%, Lamudi 85%→94%, 65-region tier config, drift monitoring fixed |
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

### Scraper Coverage Gaps
- **99.co:** Cloudflare JS challenge — partially revived via `cloudscraper` (HTTP 200 + 20-listing __NEXT_DATA__ on first call). CF rate-limits aggressively after that; realistic ceiling ~1 region per run before breaker trips on the next 403. Hardening (residential proxy rotation, Playwright stealth) is the upgrade path.
- **Rumah.com:** Code path exists but never executes (Lamudi covers 98%); candidate for archival
- **Lamudi coverage:** 64/65 (98%) live; 11 regions outlier-clamped (extracted avg >5× benchmark); 1 region on static benchmark
- **OSM coverage:** 65/65 live (17 fresh queries + 48 cache hits per run, 0 fallbacks). The earlier "17/65 live" metric was a labeling error in the email body — fixed.
- **News supply concentration:** Articles concentrated in Bandung/Jakarta/Yogyakarta corridors. v2.16.2 expanded to 5 sources (added Detik berita-ekonomi-bisnis + CNBC Indonesia) — captures Yogya, Aceh, and other secondary regions that the prior 4-source pull missed. Government endpoints (PSN, Kemenperin, Kemenhub) still unreachable due to DNS/SSL issues.

### Score Differentiation
- **Top STRONG_BUY tier compressed** — top 3 within 2.5 pts (60.6, 58.6, 58.1). Activity score caps at 40; with multipliers maxing ~1.61, final ceiling ~64. Could extend cap to 50 for more elite-tier spread but minimal investor value.
- **Momentum dormant** — needs 8+ weeks of price-history archive to fire (currently ~3 weeks). Will activate naturally as runs accumulate.

### Infrastructure Not Deployed
- Docker, Terraform, and Step Functions are fully defined in code but have never been deployed to AWS
- This is the highest-priority gap for portfolio credibility

### Testing Gaps
- Test coverage ~30%, several stale tests
- No CI pipeline running

### Documentation Debt
- Historical Oct–Nov 2025 reports and superseded roadmaps live under **`archived_bloat/historical_reports/`** (see `README.md` there). Root keeps active docs only.
- `docs/roadmap/v2.9-to-v3.0.md` may lag this file — treat **`DEVELOPMENT_ROADMAP.md`** as canonical for priorities.

---

**Roadmap Owner:** Chris Moore  
**GitHub:** [@MIFUNEKINSKi](https://github.com/MIFUNEKINSKi)  
**Last Updated:** April 5, 2026
