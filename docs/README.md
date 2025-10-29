# CloudClearingAPI Documentation

**Version:** 2.9.1 (GEE Caching + Async Processing + Critical Bugfixes)  
**Last Updated:** October 28, 2025  
**Project Status:** Production (29 regions, weekly monitoring, 82-97% performance improvement)

---

## 📚 Documentation Index

### 🏗️ Architecture
Core system design, data flow, and component responsibilities.

- **[Scoring System](architecture/scoring_system.md)** - Investment scoring algorithm (satellite-centric, 0-100 scale)
- **[Data Flow Pipeline](architecture/data_flow.md)** - 3-stage pipeline: Scoring → Financial → PDF
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
- **[Production Validation Results](deployment/production_validation.md)** - v2.8.2 validation (5 regions, 100% success)
- **[Weekly Monitoring Guide](deployment/monitoring_guide.md)** - Running `run_weekly_java_monitor.py`
- **[Troubleshooting Guide](deployment/troubleshooting.md)** - Common issues and solutions
- **[Performance Benchmarks](deployment/performance.md)** - Runtime metrics and optimization

### 🧪 Testing
Test strategies, coverage reports, and validation procedures.

- **[Testing Strategy](testing/strategy.md)** - Unit, integration, property-based, and end-to-end tests
- **[Property-Based Tests](testing/property_based.md)** - Hypothesis invariant validation (9 tests, 416 examples)
- **[Coverage Reports](testing/coverage.md)** - Current coverage metrics and gaps
- **[Validation Procedures](testing/validation.md)** - CCAPI-27.1 12-region validation workflow

### 📝 Changelog & Version History
Release notes, bug fixes, and feature additions.

- **[Version History](changelog/VERSION_HISTORY.md)** - Complete release timeline (v2.0 → v2.9.1)
- **[Bug Fix Log](changelog/BUG_FIXES.md)** - Critical bug resolutions with root cause analysis
- **[Roadmap](changelog/ROADMAP.md)** - Planned features (v2.7-v2.9 tiers)
- **[CCAPI-27.5: GEE Cache + Async Processing + Bugfixes](changelog/CCAPI-27.5-Production-Validation.md)** - v2.9.1 complete (Tasks 1-5 + 3 critical hotfixes)
- **[CCAPI-27.5: GEE Cache Integration (Original Spec)](changelog/CCAPI-27.5-GEE-Cache-Integration.md)** - Satellite data caching design doc

### 🗺️ Roadmap
Strategic development plan and future features.

- **[v2.9 → v3.0 Development Roadmap](roadmap/v2.9-to-v3.0.md)** - DE-focused approach (10-16 weeks)
  - Tier 1: Enhanced testing (property-based, integration)
  - Tier 2: Docker + Terraform + CI/CD
  - Tier 3: Step Functions + dbt + Great Expectations  
  - Tier 4: CloudWatch + MkDocs + demo video

---

## 🚀 Quick Start

### New Developer Onboarding
1. **Read:** [Architecture Overview](architecture/components.md)
2. **Read:** [Data Flow Pipeline](architecture/data_flow.md)  
3. **Read:** [Scoring System](architecture/scoring_system.md)
4. **Review:** [API Documentation](api/corrected_scoring.md)
5. **Try:** Run validation: `python run_ccapi_27_1_validation.py`

### Common Tasks
- **Add new region:** Edit `src/indonesia_expansion_regions.py`
- **Modify scoring thresholds:** See [Scoring System](architecture/scoring_system.md) §3.2
- **Update benchmarks:** Use `tools/recalibrate_benchmarks.py` (see [Benchmark Drift API](api/benchmark_drift_monitor.md))
- **Debug market data:** See [Troubleshooting](deployment/troubleshooting.md) §2.3

### Running Weekly Monitoring (v2.9.1)
```bash
# Authenticate Google Earth Engine (one-time)
earthengine authenticate

# Run weekly monitoring with GEE caching + async parallel processing
# Duration: 0.9-16 min (cache-dependent, 82-97% faster than baseline)
python run_weekly_java_monitor.py

# Outputs:
# - PDF: output/reports/executive_summary_YYYYMMDD_HHMMSS.pdf (130KB)
# - JSON: output/monitoring/weekly_monitoring_YYYYMMDD_HHMMSS.json (25MB)
# - Cache: cache/gee/ (400MB) + cache/osm/ (30MB)
```

**Performance:**
- **Baseline (v2.8):** 87 minutes
- **Cold cache (v2.9.1):** 16 minutes (82% faster)
- **Warm cache (v2.9.1):** 0.9 minutes (97% faster)

---

## 📊 System Overview

**CloudClearingAPI** is a satellite-based land investment intelligence platform monitoring **29+ regions** across Indonesia (Java island focus) for development opportunities. Combines **Sentinel-2 imagery** with real-time infrastructure data and financial projections to generate **weekly investment reports** with BUY/WATCH/PASS recommendations.

### Core Value Proposition
Transform **satellite pixels** → **actionable investment thesis** with concrete **ROI projections**.

### Key Technologies
- **Geospatial:** Google Earth Engine (Sentinel-2, 10m resolution)
- **Infrastructure:** OpenStreetMap Overpass API (7-day caching)
- **Market Data:** Web scraping (Lamudi, Rumah.com, 99.co) + static benchmarks
- **Reports:** ReportLab PDF generation
- **Testing:** pytest + Hypothesis (property-based testing)

### Architecture Principles
1. **Satellite-centric scoring:** Development activity drives base score (0-40 points)
2. **Multiplier-based enrichment:** Infrastructure (0.8-1.3x) and Market (0.85-1.4x) multiply base
3. **Cascading fallback:** Live scraping → Cache → Static benchmarks (never fails)
4. **Strict separation:** Stage 1 (Scoring) → Stage 2 (Financial) → Stage 3 (PDF)

---

## 🔧 Configuration

Main configuration file: `config/config.yaml`

Critical settings:
- `gee_project`: Google Cloud Project ID (required for GEE since 2023)
- `web_scraping.enabled`: Toggle live scraping vs benchmarks only
- `web_scraping.cache_expiry_hours`: Balance freshness vs API load (24-48h recommended)
- `processing.max_cloud_cover`: 20 = strict, 50 = permissive
- `financial_projections.target_investment_usd`: Budget-driven plot sizing (default $100K)

See [Configuration Guide](architecture/configuration.md) for complete reference.

---

## 📈 Current Status

### Production Metrics (October 2025)
- **Regions Monitored:** 29 (Java island)
- **Weekly Runtime:** ~30-35 minutes (first run) / ~15-20 minutes (with warm cache)
- **Parallel Processing:** 5 regions/batch, 6 batches total
- **Market Data Success:** 100% (Lamudi primary source)
- **OSM Cache Hit Rate:** 86% (7-day TTL)
- **GEE Cache Hit Rate:** 0-70% (14-day TTL, increases after first run)
- **Average Score:** 45-75 (varies by region/week)

### Recent Milestones
- ✅ **v2.8.2:** Market data restoration (4 root causes fixed, 100% success rate)
- ✅ **CCAPI-27.1:** Full validation (12 regions, 100/100 improvement score)
- ✅ **CCAPI-27.2:** Benchmark drift monitoring (608 lines, production-ready)
- ✅ **CCAPI-27.3:** Property-based testing (9 tests, 416 examples, all passing)
- ✅ **CCAPI-27.4:** Documentation refactor (modular structure, 76% size reduction)
- ✅ **CCAPI-27.5 (Tasks 1-4):** GEE Caching + Async Processing (79% faster, 19 tests passing, full non-blocking pipeline)
- 🔄 **CCAPI-27.5 (Task 5):** Production performance validation (29 regions, in progress)

---

## 🤝 Contributing

### Adding Features
1. Create feature branch: `git checkout -b feature/CCAPI-XX-description`
2. Write tests first (TDD approach)
3. Implement feature following [Architecture Principles](architecture/components.md)
4. Run validation: `pytest tests/ --cov=src`
5. Update relevant documentation in `docs/`
6. Create PR with detailed description

### Coding Standards
- **Type hints:** All function signatures must have type hints
- **Dataclasses:** Use `@dataclass` for data transfer objects
- **Config-driven:** Never hardcode URLs, paths, or thresholds
- **Logging:** Use `logging` module, not `print()`
- **Error handling:** All network requests must have timeout + try/except

See [Component Overview](architecture/components.md) for detailed patterns.

---

## 📞 Support & Resources

- **GitHub Repository:** https://github.com/MIFUNEKINSKi/CloudClearingAPI
- **Issue Tracker:** GitHub Issues
- **Documentation:** `/docs/README.md` (this file)
- **Legacy Documentation:** `TECHNICAL_SCORING_DOCUMENTATION.md` (deprecated - use modular docs)

---

## 📜 License

Proprietary - CloudClearingAPI Team  
**Author:** Chris Moore  
**Contact:** [Project maintainer contact]

---

**Last Documentation Update:** October 27, 2025 (CCAPI-27.4 Modular Refactor)
