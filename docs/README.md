# CloudClearingAPI Documentation

**Version:** 2.12.1 (Full 65-Region Coverage + Scoring Fixes)  
**Last Updated:** April 4, 2026  
**Project Status:** Production (65 regions across Indonesia, weekly automated reports with email delivery)

---

## 📚 Documentation Index

### 🏗️ Architecture
Core system design, data flow, and component responsibilities.

- **[Scoring System](architecture/scoring_system.md)** - Investment scoring algorithm (satellite-centric, 0-100 scale)
- **[Data Flow Pipeline](architecture/data_flow.md)** - Multi-stage pipeline: Scoring → Financial → PDF
- **[Component Overview](architecture/components.md)** - Module responsibilities and interfaces
- **[Configuration Guide](architecture/configuration.md)** - config.yaml structure and settings

### 🔌 API & Integration
Method signatures, parameters, and integration patterns.

- **[CorrectedInvestmentScorer API](api/corrected_scoring.md)** - Core scoring engine methods
- **[FinancialMetricsEngine API](api/financial_metrics.md)** - ROI, RVI, and land value calculations  
- **[BenchmarkDriftMonitor API](api/benchmark_drift_monitor.md)** - Drift tracking and recalibration
- **[LandPriceOrchestrator API](api/land_price_orchestrator.md)** - Multi-source pricing with fallback
- **[GEE Image Cache API](api/gee_cache.md)** - Satellite data caching system (14-day TTL)

### 🚀 Deployment & Operations
Production validation, monitoring, and troubleshooting.

- **[Docker Setup Guide](deployment/docker-setup.md)** - Complete containerization guide (CCAPI-28.0)
- **[Terraform Infrastructure Guide](deployment/terraform-guide.md)** - AWS infrastructure as code (CCAPI-28.1)
- **[Step Functions Orchestration Guide](deployment/step-functions-guide.md)** - Automated pipeline with AWS Step Functions (CCAPI-29.0)
- **[Production Validation Results](deployment/production_validation.md)** - Validation reports
- **[Weekly Monitoring Guide](deployment/monitoring_guide.md)** - Running `run_weekly_java_monitor.py`
- **[Troubleshooting Guide](deployment/troubleshooting.md)** - Common issues and solutions
- **[Performance Benchmarks](deployment/performance.md)** - Runtime metrics and optimization

### 🧪 Testing
Test strategies, coverage reports, and validation procedures.

- **[Testing Strategy](testing/strategy.md)** - Unit, integration, property-based, and end-to-end tests
- **[Property-Based Tests](testing/property_based.md)** - Hypothesis invariant validation
- **[Coverage Reports](testing/coverage.md)** - Current coverage metrics and gaps
- **[Validation Procedures](testing/validation.md)** - Region validation workflow

### 📝 Changelog & Version History
Release notes, bug fixes, and feature additions.

- **[CHANGELOG.md](../CHANGELOG.md)** - Complete release timeline (v2.0 → v2.12.1)
- **[CCAPI-29.0: Step Functions Orchestration](changelog/CCAPI-29-0-Step-Functions-Orchestration.md)** - Automated pipeline execution
- **[CCAPI-28: DE Foundation Complete](changelog/CCAPI-28-DE-Foundation-Complete.md)** - Docker + Terraform

### 🗺️ Roadmap
Strategic development plan and future features.

- **[Development Roadmap](../DEVELOPMENT_ROADMAP.md)** - Current priorities and future plans

---

## 🚀 Quick Start

### New Developer Onboarding
1. **Read:** [Architecture Overview](architecture/components.md)
2. **Read:** [Data Flow Pipeline](architecture/data_flow.md)  
3. **Read:** [Scoring System](architecture/scoring_system.md)
4. **Review:** [API Documentation](api/corrected_scoring.md)
5. **Try:** Run monitoring: `python run_weekly_java_monitor.py`

### Common Tasks
- **Add new region:** Edit `src/indonesia_expansion_regions.py` and add entries to `infrastructure_analyzer.py` regional fallback + `scraper_orchestrator.py` regional benchmarks
- **Modify scoring thresholds:** See [Scoring System](architecture/scoring_system.md)
- **Update benchmarks:** See [Benchmark Update Procedure](../BENCHMARK_UPDATE_PROCEDURE.md)
- **Debug market data:** See [Troubleshooting](deployment/troubleshooting.md)

### Running Weekly Monitoring (v2.12.1)
```bash
# Authenticate Google Earth Engine (one-time)
earthengine authenticate

# Run Java regions only (31 regions, default)
python run_weekly_java_monitor.py

# Run ALL 65 regions across Indonesia
python run_weekly_java_monitor.py --all --yes

# Outputs:
# - PDF: output/reports/executive_summary_YYYYMMDD_HHMMSS.pdf
# - JSON: output/monitoring/weekly_monitoring_YYYYMMDD_HHMMSS.json
# - Email: Auto-sent to configured recipient with PDF attached
# - Price Archive: output/scraper_cache/price_history/ (JSONL, accumulates)
```

---

## 📊 System Overview

**CloudClearingAPI** is a satellite-based land investment intelligence platform monitoring **65 regions** across Indonesia for development opportunities. Combines **dual-sensor satellite imagery** (Sentinel-2 optical + Sentinel-1 SAR radar) with real-time infrastructure data, live market prices, and development news to generate **weekly investment reports** with BUY/WATCH/PASS recommendations.

### Core Value Proposition
Transform **satellite pixels** → **actionable investment thesis** with concrete **ROI projections**.

### Key Technologies
- **Geospatial:** Google Earth Engine (Sentinel-2 optical 10m + Sentinel-1 SAR radar, dual-sensor fusion)
- **Infrastructure:** OpenStreetMap Overpass API (7-day caching, 65-region fallback database)
- **Market Data:** Web scraping (Lamudi primary, 99.co secondary) + static benchmarks + JSONL price history
- **News:** Jakarta Post, Kompas, Antara News scraping with region matching
- **Reports:** ReportLab PDF with decision matrix, executive summary, and per-region detail pages
- **Email:** Gmail SMTP auto-delivery with PDF attachment
- **Testing:** pytest + Hypothesis (property-based testing)

### Architecture Principles
1. **Satellite-centric scoring:** Development activity drives base score (0-40 points)
2. **Multiplier-based enrichment:** Infrastructure (0.8-1.3x), Market (0.85-1.4x), News (0.95-1.2x), Momentum (0.85-1.3x)
3. **Cascading fallback:** Live scraping → Cache → Static benchmarks (never fails)
4. **Dual-sensor fusion:** Optical + SAR radar with cloud-penetrating fallback
5. **Infrastructure sanity checks:** OSM data validated against curated regional fallback database

---

## 📈 Current Status

### Production Metrics (April 2026)
- **Regions Monitored:** 65 (31 Java + 34 outer islands)
- **Scoring Pipeline:** Activity × Infrastructure × Market × News × Confidence × Momentum
- **Satellite Sensors:** Sentinel-2 optical + Sentinel-1 SAR radar (dual-sensor fusion)
- **Market Data:** Lamudi live scraping (~40% coverage), benchmark fallback for remainder
- **Infrastructure:** OSM with 65-region curated fallback database
- **News Sources:** Jakarta Post, Kompas, Antara News
- **Report Output:** Multi-page PDF with decision matrix + auto-email delivery

### Recent Milestones
- ✅ **v2.12.1 (Apr 2026):** First full 65-region run, infrastructure/market/drift fixes
- ✅ **v2.12 (Mar 2026):** Decision matrix PDF page, expanded to 65 regions
- ✅ **v2.11 (Mar 2026):** SAR radar fusion, news catalyst scoring, price momentum, auto-email
- ✅ **v2.10 (Feb 2026):** Indonesia expansion (39 → 51 regions)
- ✅ **v2.9.1 (Nov 2025):** Docker + Terraform + Step Functions + GEE caching + async processing
- ✅ **v2.8.2 (Oct 2025):** Market data restoration (Lamudi JSON-LD parsing)
- ✅ **v2.7.0 (Oct 2025):** Budget-driven investment sizing

---

## 🤝 Contributing

### Adding Features
1. Create feature branch: `git checkout -b feature/CCAPI-XX-description`
2. Write tests first (TDD approach)
3. Implement feature following architecture principles
4. Run validation: `pytest tests/ --cov=src`
5. Update relevant documentation in `docs/`
6. Create PR with detailed description

### Coding Standards
- **Type hints:** All function signatures must have type hints
- **Dataclasses:** Use `@dataclass` for data transfer objects
- **Config-driven:** Never hardcode URLs, paths, or thresholds
- **Logging:** Use `logging` module, not `print()`
- **Error handling:** All network requests must have timeout + try/except

---

## 📞 Support & Resources

- **GitHub Repository:** https://github.com/MIFUNEKINSKi/CloudClearingAPI
- **Issue Tracker:** GitHub Issues
- **Documentation:** `/docs/README.md` (this file)
- **Main README:** `README.md` (project overview and scoring philosophy)

---

## 📜 License

MIT License  
**Author:** Chris Moore  
**GitHub:** [@MIFUNEKINSKi](https://github.com/MIFUNEKINSKi)

---

**Last Documentation Update:** April 4, 2026 (v2.12.1 — Full 65-Region Coverage + Scoring Fixes)
