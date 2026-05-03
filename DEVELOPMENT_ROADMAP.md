# CloudClearingAPI Development Roadmap

**Updated:** April 28, 2026
**Current Version:** v2.19.2 (Cron Wrapper IsADirectoryError Fix)

---

## 🎯 North-Star Goal

**See Indonesian land-investment opportunities early and make money.** Trade-offs favor signal trustworthiness over breadth. Every BUY in the weekly email should be one the investor would actually act on; one fake BUY is worse than ten real ones missed.

CloudClearingAPI is an automated land-investment analyst for 65 Indonesian regions, combining Sentinel-2 optical + Sentinel-1 SAR satellite change detection, live market scraping (Lamudi primary), OpenStreetMap infrastructure analysis, and Indonesian-press infrastructure news into a single weekly investment score with a PDF + email briefing.

**Two tracks**, explicitly:
- **Track A (primary): Investment alpha** — does the system actually help the investor make money? Phases 1–3 below.
- **Track B (optional): Portfolio polish** — DE-skills demonstration for resume / interviews. Real but secondary; only shipped when it doesn't pull capacity from Track A. Phases 4–7 below.

Historically the roadmap centered Track B, with signal-quality work scattered across P2/P3 items. The April 2026 audit cycle (v2.16.3–v2.16.6) reoriented around Track A; this roadmap formalizes that pivot.

---

## ✅ What's Working

| Capability | Status | Notes |
|---|---|---|
| **65-region pipeline** | ✅ | ~90 min/run, 65/65 success on Apr 27 |
| **Dual-sensor satellite** | ✅ | Optical + SAR fusion with 20× cap (fusion mode) and 500K cap (sar_only mode); SAR-dominant warning surfaced in email |
| **Web scraping** | ✅ 64/65 live | Lamudi primary; outlier-resistant mean (10×-median filter) cut clamps 22→12; 99.co cloudscraper revival best-effort (~1 region/run) |
| **Infrastructure (OSM)** | ✅ 65/65 | 17 fresh + 48 cache hits per run, 0 fallbacks |
| **News pipeline** | ✅ 5 sources | Jakarta Post, Kompas, Antara (revived 2026-04-25 — brotli bug, was 0 articles for 2+ weeks), Detik (×3 subsections), CNBC Indonesia. Title-bigram dedup live. ~105 raw articles/run |
| **Investment scoring** | ✅ | STRONG_BUY ≥49 conf≥0.85; BUY ≥42 conf≥0.75; WATCH ≥33 conf≥0.50; confidence caps biting (sar_only 0.84, clamped 0.55, low-listing 0.65) |
| **Tier transitions** | ✅ | Week-over-week upgrades/downgrades surfaced in email |
| **Drift monitoring** | ✅ | Per-region price-history median (4-week window, ≥3 prior samples), tier fallback, dataclass-aware extraction |
| **PDF + email delivery** | ✅ | SMTP preflight, webhook fallback, low-conf subject prefix |
| **Multi-layer caching** | ✅ | GEE 14d, SAR 14d, OSM 7d, news 2d, scraper 24h |
| **JSONL price history** | ✅ | Append-only data lake; 8 weeks accumulated |
| **Docker / Terraform / Step Functions** | ✅ Defined, ❌ not deployed | 6 modules, ~70 AWS resources, no-NAT dev path wired |

### Latest Run Metrics (Apr 27 20:13 — post-v2.16.5)
- 65/65 regions, 93 min runtime
- **4 STRONG_BUY** / 17 BUY / 21 WATCH (Merak correctly demoted 61.7→51.8 by sar_only cap fix)
- Antara revived: 0 → 29 articles per scrape
- Outlier clamps: 22 → 12 (-45%); remaining 6 are stale-cache, will self-resolve
- Drift: avg +12.2% (was +14.9%)

---

# Track A — Investment Alpha (Primary)

If the system can't be trusted to surface real opportunities, none of Track B matters. These phases are non-optional.

## Phase 1 — Signal trustworthiness ✅ MANDATORY ITEMS COMPLETE (2026-04-28)

Status: all 8 mandatory items shipped (v2.16.3 through v2.16.9). The harness for measuring predictiveness exists; meaningful tier-predictiveness numbers will emerge after 4+ weeks of stable post-fix history accumulates. Re-run `python tools/backtest.py` weekly to track.

**Why:** The October 2025 → April 2026 audit cycle uncovered five distinct classes of silent miscalibration (sar_only loophole, brotli-broken Antara, Lamudi misparse pollution, slug 404s, sar/optical units mismatch). All shipped fixes are real wins, but it's not yet proven the surfaced BUYs are predictive of actual price movement.

| Task | Effort | Status |
|---|---|---|
| Outlier-resistant Lamudi mean (median-anchored) | shipped v2.16.4 | ✅ |
| sar_only cap + provenance fix (Merak) | shipped v2.16.3 | ✅ |
| Antara brotli accept-encoding fix | shipped v2.16.4 | ✅ |
| Lamudi slug refresh (kulon-progo, gunung-kidul) | shipped v2.16.5 | ✅ |
| News title-bigram dedup | shipped v2.16.6 | ✅ |
| **Per-region history-anchored outlier clamp** (use region's own 8-sample median-of-medians when ≥3 samples, bounded by 0.5–3× of static) | shipped v2.16.8 | ✅ |
| **Benchmark recalibration** from 2026-04-28 deep-research report — bucket updates (medan/balikpapan), 11 region-specific overrides, 3 frozen regions | shipped v2.16.7 | ✅ |
| **Forecast log + backtest harness** — `tools/backtest.py` reads historical runs + price history, reports per-tier mean delta (2w/4w/8w) + Spearman ρ(score, delta); `forecast_log.jsonl` writer hooked into weekly monitor. Methodology guards: frozen regions excluded, listing_count-shift filter, pre-fix anchor banner. Current data pre-dates v2.16.x fixes so deltas reflect fix-artifacts; harness ready for meaningful signal once 4+ weeks of post-2026-04-28 history accumulates | shipped v2.16.9 | ✅ |
| Region routing for stuck regions (medan_belawan_port, ambon, papua) | 4-8h | 🔲 P1 |

**Phase 1 done when:** the weekly email STRONG_BUY list, replayed against 4–8 weeks of post-fact price history, shows tier separation (STRONG_BUY > BUY > WATCH > PASS in cumulative price movement). Until that's measurable, "see opportunities early" is unverified.

## Phase 2 — Acquisition feasibility ✅ STATIC LAYER SHIPPED (2026-04-28, v2.16.10)

**Why:** A BUY signal in a region the investor cannot legally close on, or one that's on protected forest / future-PSN right-of-way, is wasted alert weight.

| Task | Effort | Status |
|---|---|---|
| Per-region ownership-pathway lookup (foreign-OK vs nominee vs no-go) | shipped v2.16.10 | ✅ |
| RTRW zoning class per region (static, deep-research-validated for 13 cases + inferred for 14) | shipped v2.16.10 | ✅ |
| Transactions-per-month liquidity estimate (tier-based proxy) | shipped v2.16.10 | ✅ |
| Surface feasibility flags in PDF + email (🚫 / ⚠️ / ✅) | shipped v2.16.10 (email) | ✅ email; PDF picks up automatically via JSON object |
| **Live RTRW API integration** — replace static profiles with bbox-lookup against the OSS KKPR API | 8-12h | 🔲 P2 (static is fine for now) |
| **Liquidity from listing turnover** — `liquidity_estimator.py` reads price-history JSONL, classifies observed tier, asymmetric mismatch flag fires when research overstates liquidity by ≥2 levels. Audit tool at `tools/liquidity_audit.py`. Surfaced 5 real mismatches (Surabaya/Cikarang/Gresik retail < tier_default presumption) | shipped v2.16.12 | ✅ |

**Phase 2 done when:** ✅ every STRONG_BUY in the email carries a feasibility tag and the investor can immediately tell whether a region is closeable, requires leasehold, requires PT PMA, or is restricted. The live-API enhancements are P2 polish — the static layer carries the load for now.

## Phase 3 — Portfolio-aware action ✅ SHIPPED (2026-04-28, v2.16.11)

**Why:** The email said "what's hot this week" but never "what's missing from your book." Phase 3 closes that gap.

| Task | Effort | Status |
|---|---|---|
| Position log (`data/positions.jsonl`) — manually maintained, gitignored | shipped v2.16.11 | ✅ |
| Email "YOUR PORTFOLIO" section: positions with P&L (IDR, %, annualized), feasibility line, per-position alerts | shipped v2.16.11 | ✅ |
| Correlation hints — same-bucket detection adds "📌 already hold X" flag to candidate STRONG_BUYs | shipped v2.16.11 | ✅ |
| Exit-signal heuristics — `EXIT_WATCH` (price down >5% over 4 samples), `LIQUIDITY_RISK` (listing volume drop ≥50%), `TIER_DOWNGRADE` (from tier_transitions) | shipped v2.16.11 | ✅ |

**Phase 3 done when:** ✅ the email is structured around the investor's actual book, not a leaderboard of all 65 regions. Reading it in 2 minutes tells the investor what to add, hold, or watch for exit.

---

# Track B — Portfolio Polish (Optional)

Real value for resume / interviews. Ship only when Track A capacity allows. None of these contribute investment alpha; all are demotable if Track A has open work.

## Phase 4 — AWS deployment

Docker + Terraform (6 modules, ~70 resources) + Step Functions exist but have never been deployed. **Cost-conscious default**: `enable_nat_gateway = false` + public subnets + `AssignPublicIp` on ECS RunTask, ~$0–5/month idle, easy `terraform destroy` between use. P2/P3 unless interviewing.

## Phase 5 — dbt transformation layer

Raw JSON → analytics-ready staging/marts. Adds modern-data-stack pattern to portfolio. P3 — purely portfolio.

## Phase 6 — CI/CD

GitHub Actions test-on-push, Docker build + ECR push, Terraform validate. P2 if portfolio-active.

## Phase 7 — Observability + showcase

Great Expectations data validation, CloudWatch dashboards, SNS alerts, Streamlit dashboard, MkDocs site, demo video, architecture diagram. All P2/P3 polish.

---

## Skills Coverage (informational)

How CloudClearingAPI maps to common DE-job requirements. Track B phases close most of the gaps. Track A doesn't need any of these to make money.

| Requirement | Status |
|---|---|
| Python | ✅ Demonstrated |
| Data pipelines / ETL | ✅ Demonstrated |
| Web scraping | ✅ Demonstrated |
| API integration (GEE, OSM) | ✅ Demonstrated |
| Data modeling (tiers, RVI, multipliers) | ✅ Demonstrated |
| Terraform / Docker | ✅ Code exists, ❌ not deployed |
| AWS (S3, ECS, Step Functions) | ⚠️ Defined |
| Step Functions orchestration | ⚠️ Defined |
| Data quality (drift monitor) | ⚠️ Partial |
| dbt | 🔲 Phase 5 |
| CI/CD | 🔲 Phase 6 |
| Monitoring / observability | 🔲 Phase 7 |
| SQL | 🔲 Phase 5 |

---

## ✅ Completed Features (Reference)

| Version | Date | Key Features |
|---|---|---|
| **v2.19.2** | May 3, 2026 | Cron wrapper bug fix. `run_weekly_cron.py:find_latest_output` was matching a legacy `executive_summary_UPDATED.pdf/` directory via `glob()` (reverse-sorted, 'U' > '2' in ASCII), then crashing at `open()` with IsADirectoryError. Fixed via `.is_file()` filter. The launchd cron had been crashing silently every Sunday for ~2 weeks even though the inner pipeline completed cleanly. Schedule restored; next calendar fire Sun May 10 9am |
| **v2.19.1** | Apr 28, 2026 | Two follow-on fixes from v2.19 audit. (1) Pooled-slug clamp tightening: 6 split sub-regions sharing a Lamudi parent slug now use 2.5× outlier threshold instead of 5×. `subang_pantura_agrarian` correctly clamps from inflated Rp 1.84M to research-anchored Rp 450K. (2) Zoning-aware dev cost: SEZ-designated regions get 0.30× cost (infra preinstalled), industrial 0.60×, default 1.00×. Bitung KEK SEZ ROI flipped −44.6% → +26.7% (model artifact, not real signal) |
| **v2.19.0** | Apr 28, 2026 | Region splits — Subang/Balikpapan/Bitung each split into 2 sub-regions where deep-research found 3-10× pricing spreads inside one bbox. New: `subang_patimban_industrial` + `subang_pantura_agrarian`, `balikpapan_kariangau_industrial` + `balikpapan_selatan_commercial`, `bitung_port_corridor` + `bitung_kek_sez_industrial`. Total regions 65 → 68. Each gets distinct bbox + benchmark + feasibility + infra fallback + news routing |
| **v2.18.0** | Apr 28, 2026 | Prediction Review — closes the feedback loop. New `src/core/prediction_tracker.py` + email/PDF section comparing past forecasts (4w/8w/12w anchors) against today's price-history. Per-region: realized return, annualized, prorated-predicted, status icon (✅⏳🔥⚠❌). Aggregate: tier means, tier integrity check, hit rate. Honest constraints baked in: realized-vs-prorated for short-window fairness, listing_count_shift_flag for coverage-change noise, pre-fix-anchor banner for v2.16.x recalibration era. Forecast log writer enriched with predicted_roi_3yr/5yr + feasibility + weeks_at_tier |
| **v2.17.1** | Apr 28, 2026 | PDF lock-step with email — v2.16.x + v2.17.0 fields (feasibility, observed liquidity, weeks_at_tier, score breakdown, action links, portfolio section) now render in PDF report. Decision matrix gains Feas + Wks columns; investment analysis gains 6 bullet types per top-5 region; new YOUR PORTFOLIO table when positions.jsonl exists |
| **v2.17.0** | Apr 28, 2026 | Trust + friction reduction release. (1) Weeks-at-tier tracking — 🆕 NEW THIS WEEK / 📌 N-week streak flags directly serve the "early" word in the north-star. (2) Score breakdown — `activity 32 × infra 1.15 × market 1.10 × conf 1.00 × news 1.05 × momentum 1.00 = 52.2` rendered per priority opportunity, builds trust through visibility. (3) Action links — Lamudi search + Google Maps satellite + OSM bbox URLs bundled into each STRONG_BUY/BUY entry, removes ~80 min/week of friction |
| **v2.16.12** | Apr 28, 2026 | Phase 2 polish: empirical liquidity from archived listing counts. `liquidity_estimator.py` classifies observed tier (very_low / low / moderate / cap_saturated) from price-history JSONL; asymmetric mismatch flag fires when research overstates liquidity by ≥2 tier levels. `tools/liquidity_audit.py` CLI for periodic review. Surfaced 5 real mismatches: Surabaya/Cikarang/Gresik tier-1 metros where research expected `very_high` but Lamudi retail shows `moderate` (~10-13 listings/scrape) — institutional ≠ retail liquidity |
| **v2.16.11** | Apr 28, 2026 | Phase 3 portfolio-aware action ships — closes Track A. `src/core/portfolio_manager.py` with Position dataclass + load_positions + compute_position_pnl + correlation_hint + per-position alerts (EXIT_WATCH, LIQUIDITY_RISK, TIER_DOWNGRADE). YOUR PORTFOLIO section at top of email when positions.jsonl exists. Correlation hints in priority-opportunities surface "📌 already hold X" when candidates land in same bucket as existing holdings. Track B (AWS/dbt/CI-CD/observability) now genuinely optional polish |
| **v2.16.10** | Apr 28, 2026 | Phase 2 acquisition-feasibility layer ships. `src/core/region_feasibility.py` with `FeasibilityProfile` dataclass + 27 explicit profiles (13 deep-research-validated + 14 inferred from regulatory data) + 38 tier-based defaults. Three dimensions: ownership_pathway, zoning_class+overlays, liquidity_tier. Renders ✅⚠️🚫 flag + one-line summary under each STRONG_BUY/BUY in the email. 3 regions land restricted (Nusantara×2 + Labuan Bajo); 5+ flagged for verification. Soft annotation, not a hard filter |
| **v2.16.9** | Apr 28, 2026 | Forecast log + backtest harness — closes Phase 1 with the gating measurement infrastructure. `tools/backtest.py` reports per-tier mean delta (2w/4w/8w) + Spearman ρ; `forecast_log.jsonl` writer hooked into weekly monitor. Methodology guards: frozen regions excluded, listing_count-shift filter, pre-fix anchor banner. Current data pre-dates v2.16.x fixes; harness ready for meaningful signal once 4+ weeks of post-2026-04-28 history accumulates |
| **v2.16.8** | Apr 28, 2026 | Per-region history-anchored clamp closes Phase 1's last mandatory item. `_resolve_clamp_anchor` chain: frozen → history (≥3 samples within 0.5–3× of static) → region override → bucket → unmapped. Median-of-medians (last 8 samples) is doubly robust — week-level shock absorption on top of v2.16.4's listing-level filter. Sanity band protects against banjarmasin/bitung/mandalika cases where history is itself wrong. 64 of 67 regions eligible for live calibration |
| **v2.16.7** | Apr 28, 2026 | Benchmark recalibration from 2026-04-28 deep-research report. Bucket updates: medan Rp 3.54M→1.6M (-54.8%), balikpapan Rp 3.71M→1.9M (-48.7%). 11 region-specific overrides (cikarang Rp 2.8M, serang/cilegon Rp 4.9M, anyer Rp 1.0M, mandalika Rp 3.5M, batang Rp 1.2M, etc.). 3 frozen regions (nusantara_capital_core, nusantara_balikpapan_corridor, labuan_bajo_komodo_gateway) bypass clamp entirely per research finding that platform aggregates show 40× source disagreement |
| **v2.16.6** | Apr 25, 2026 | News dedup via title-bigram overlap (≥2 shared bigrams = dup); drops 4/9 Bekasi rail-accident articles. Medan Kuala Namu corridor → `deli-serdang` slug (median Rp 18.5M→9.9M, escapes 5× outlier clamp). A/B-tested 6 problem regions; only Medan benefited |
| **v2.16.5** | Apr 25, 2026 | Lamudi slug refresh: kulonprogo→kulon-progo + gunungkidul→gunung-kidul (was hitting 404 → 99.co rate-limit → benchmark fallback). Verified all 31 location_map slugs |
| **v2.16.4** | Apr 25, 2026 | Outlier-resistant Lamudi mean (10×-median filter) — Jakarta sim: old avg Rp 2.21B/m² → new Rp 9.71M/m²; brotli accept-encoding silent failure fixed (Antara news 0→25 articles, was broken ≥2 weeks). Net: 22/65 outlier-clamped regions should return to live data confidence 0.85 |
| **v2.16.3** | Apr 25, 2026 | Plug sar_only loophole: cap fused at 500K; fix `satellite_data_source` provenance so SAR-only mode triggers the 0.84 confidence cap; stat-calc timeout 60s → 120s. Net effect on Merak: 61.7 → 51.8 (validated end-to-end Apr 27 20:13 run) |
| **v2.16.2** | Apr 25, 2026 | Drift tests cleaned (22 obsolete tier-only tests skipped); News supply expansion: Detik berita-ekonomi-bisnis + CNBC Indonesia (raw articles 46→79); AWS Terraform: 5 deprecated S3 lifecycle rules fixed; 99.co revived via cloudscraper (best-effort) |
| **v2.16.1** | Apr 27, 2026 | SAR fusion 20× cap + threshold recalibration (49/42/33); tier transitions tracked week-over-week; thread-safe stats timeout (replaced broken signal.alarm); SAR construction/clearing band-name fix |
| **v2.16.0** | Apr 26, 2026 | STRONG_BUY tier introduced; activity log-scaling; confidence hard caps for SAR-only/clamped; Detik Infrastruktur news source; per-region drift benchmarks (avg drift 94%→19%); momentum math bug fixed; 5Y/3Y ROI apples-to-apples; Banten + Denpasar benchmark buckets; price-outlier clamp; SMTP preflight + webhook fallback |
| **v2.14.0** | Apr 2026 | Parallel scoring (ThreadPoolExecutor), news WoW, GEE optical cache, province-level scraper fallback, expanded PDF, actionable email |
| **v2.13.0** | Apr 2026 | Live data pipeline: OSM 0%→78%, Lamudi 85%→94%, 65-region tier config, drift monitoring fixed |
| **v2.11** | Mar 2026 | SAR radar fusion, news catalyst scoring, JSONL price history, momentum analyzer, auto-email |
| **v2.10** | Feb 2026 | Indonesia expansion to 51 regions |
| **v2.9.1** | Nov 2025 | Docker, Terraform, Step Functions, GEE caching, async processing |
| **v2.6** | Oct 2025 | RVI-aware market multiplier, regional tiers, multi-source scraping |
| **v2.0–2.5** | Oct 2025 | Corrected scoring, infrastructure standardization, financial metrics |

---

## 🚨 Known Issues & Limitations

### Signal quality (Track A)
- **Outlier clamps stuck at 6** for regions with >24h-old Lamudi caches predating v2.16.4; resolves naturally at next 24h cache expiry
- **Per-region benchmark mismatch** — buckets show 10–41× spread internally; per-region history-anchored clamp is Phase 1's next ship
- **Backtest does not exist** — STRONG_BUY predictiveness is unverified. Phase 1 deliverable
- **No acquisition-feasibility data** — Phase 2

### Scraper coverage gaps
- **99.co:** Cloudflare rate-limits aggressively; ceiling ~1 region/run. Hardening (residential proxy rotation, Playwright stealth) is the upgrade path
- **Rumah.com:** Code path exists but never executes (Lamudi covers 98%); candidate for archival
- **News supply concentration:** Articles concentrated in Bandung/Jakarta/Yogyakarta corridors. v2.16.2 expansion + Antara revival captured Yogya, Aceh, secondary regions. Government endpoints (PSN, Kemenperin, Kemenhub) still unreachable due to DNS/SSL issues

### Score differentiation
- **Top STRONG_BUY tier compressed** — top 4 within 1 pt post-v2.16.3 cap. Activity score caps at 40; with multipliers maxing ~1.61, final ceiling ~64
- **Momentum dormant** — needs 8+ weeks of price-history archive to fire (currently ~8 weeks; should activate next run or two)

### Track B not started
- Docker / Terraform / Step Functions exist in code but have never been deployed
- No CI pipeline running
- Test coverage ~30%, several stale tests

### Documentation
- Historical Oct–Nov 2025 reports under `archived_bloat/historical_reports/`. Root keeps active docs only
- `docs/roadmap/v2.9-to-v3.0.md` may lag this file — treat **`DEVELOPMENT_ROADMAP.md`** as canonical
- `TECHNICAL_SCORING_DOCUMENTATION.md` (6,872 lines) is significantly larger than the scoring code it documents; candidate for compression

---

**Roadmap Owner:** Chris Moore
**GitHub:** [@MIFUNEKINSKi](https://github.com/MIFUNEKINSKi)
**Last Updated:** April 28, 2026
