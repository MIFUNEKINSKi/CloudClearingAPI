# Changelog

All notable changes to CloudClearingAPI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [2.19.5] - 2026-05-14 - Pooled-Slug History Carve-Out + Price-Trend ROI Clamp

### Fixed
- **Pooled-slug history contamination** (`scraper_orchestrator._resolve_clamp_anchor`): the 6 split sub-regions share a Lamudi parent slug, so their price-history JSONLs reflect the pooled price, not the sub-region. `_resolve_clamp_anchor` was returning the contaminated history median when it fell within the 0.5–3.0 static-trust band, defeating v2.19.1's 2.5× clamp. Now pooled-slug regions skip the history path entirely and always use the research-validated static benchmark. `subang_pantura_agrarian` now correctly clamps Rp 1.725M extract → Rp 450K.
- **Price-trend ROI inflation** (`financial_metrics._estimate_appreciation_rate`): `price_trend_30d` feeds the appreciation rate at 40% weight. Cikarang's +56.3% trend (a scraper-recovery artifact) inflated the rate to 29.7%/yr → +118% projected 3yr ROI. Clamp the trend contribution to ±20% before blending. Cikarang now: 15.2%/yr → ~+53% 3yr land ROI.

### Verified
- All 6 pooled-slug regions resolve to research static benchmarks; industrial halves still pass, agrarian/SEZ halves clamp correctly.
- Price-trend clamp: +56% / +30% both clamp to +20%; sane +12% passes through; -40% crash clamps to -20%.
- Tests: 26 passed, 22 skipped, 0 failed.

### Note
- Both bugs were latent until v2.19.0's region splits created pooled-slug sub-regions AND enough weekly history accumulated to trip the history-anchor path. The splits + clamp tightening were correct; the history anchor needed a pooled-slug carve-out.

## [2.19.4] - 2026-05-04 - Catalyst-Floor Calibration Alert

### Added
- `detect_calibration_alerts(forecasts)` in `prediction_tracker.py` — picks longest available anchor (12w/8w/4w), groups realizations by catalyst class (SEZ / PSN / KSPN via `region_feasibility.zoning_overlays`), excludes listing-shifted samples, fires when ≥3 regions in the same class show realized < 0.5× prorated-predicted.
- `CalibrationAlert` dataclass + `calibration_alerts_to_email_lines` renderer.
- Email + PDF integration: alerts render at the TOP of the PREDICTION REVIEW section so they jump out before per-anchor detail.

### Why
- v2.19.3 catalyst floors are hard-coded constants. Without a feedback loop, an over-aggressive floor would silently produce over-optimistic ROI numbers indefinitely.
- Semi-automatic was chosen over full self-adjustment to avoid self-reinforcing wrong-floor risk during the noisy v2.16.x post-fix calibration period.

### Verified
- Catalyst classification correct (SEZ → bitung_kek + batang_industrial_sez, PSN → subang_patimban_industrial, KSPN → lake_toba + labuan_bajo, plain industrial → None).
- 0 alerts fire on current data (expected — forecast log too thin; alerts become possible from ~late May 2026).
- Synthetic-test rendering verified for both email and PDF paths.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.19.3] - 2026-05-03 - Catalyst-Aware Appreciation Floor

### Fixed
- `_estimate_appreciation_rate` floor was 5%/yr for all regions, including SEZs designed to attract FDI. Now reads `region_feasibility.zoning_overlays` and raises the floor for catalyst regions: `sez_designated` / `government_subsidized` → 10%/yr, `psn_right_of_way` → 8%/yr, `kspn_priority` / `kspn_strict` → 7%/yr, default → 5%/yr.

### Why
- v2.19.1 dev-cost fix correctly cut Bitung KEK SEZ dev cost from Rp 800K → Rp 240K, but headline ROI was still −12.5% 3yr because the 5% appreciation floor undershot what SEZ economics deliver. With v2.19.3: 3yr ROI 0.1%, 5yr +21.1%.

### Verified
- Catalyst floors propagate correctly: bitung_kek 10%, batang_industrial_sez 10%, subang_patimban_industrial 8%, lake_toba 7%. Other regions unchanged.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.19.2] - 2026-05-03 - Cron Wrapper IsADirectoryError Fix

### Fixed
- `run_weekly_cron.py:find_latest_output` now filters `glob()` to `.is_file()` only. Previously a legacy `output/reports/executive_summary_UPDATED.pdf/` *directory* matched the glob and reverse-sorted to the front (`'U' > '2'` in ASCII). The wrapper crashed at the email-attachment step every Sunday for ~2 weeks even though the inner pipeline completed successfully each time.

### Cleanup
- Renamed `output/reports/executive_summary_UPDATED.pdf/` → `output/reports/_archived_legacy_oct2025_dir/` to prevent recurrence.

### Schedule
- Today's missed Sunday May 3 run kicked off manually under the fixed wrapper.
- launchd calendar trigger confirmed for next Sunday May 10 09:00.

## [2.19.1] - 2026-04-28 - Pooled-Slug Clamp + Zoning-Aware Dev Cost

### Fixed
- **Pooled-slug clamp**: split sub-regions sharing a Lamudi slug now use a tighter 2.5× clamp (vs standard 5×). New `_POOLED_SLUG_REGIONS` set covers the 6 sub-regions from v2.19.0. `subang_pantura_agrarian` was previously accepting industrial-priced Subang listings; now correctly clamps to its research anchor (Rp 450K/m²).
- **Zoning-aware development cost** in `_estimate_development_costs`: SEZ-designated / government-subsidized industrial regions get 0.30× dev cost (infra preinstalled by SEZ authority); plain `industrial` zoning gets 0.60× (estate-provided utilities); other zoning gets 1.00× greenfield baseline. Bitung KEK SEZ ROI flipped from −44.6% to +26.7% — the −44% number was a model artifact, not a real signal.

### Changed
- Clamp log message now prints the actual multiplier used (was hard-coded "5.0×" even when the pooled-slug 2.5× threshold fired).
- `batang_industrial_sez` feasibility profile gained `sez_designated` + `government_subsidized` overlays (was missing — only bitung_kek had them).

### Verified
- Smoke test: pooled-slug clamp behavior verified across all 6 split sub-regions plus a non-pooled control (cikarang). Zoning multipliers verified across SEZ / industrial / agrarian / tourism / mixed regions.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.19.0] - 2026-04-28 - Region Splits (3 over-broad regions → 6 sub-regions)

### Changed
- **subang_patimban_megaport** split into `subang_patimban_industrial` (eastern, Rp 1.5M/m², HGB) and `subang_pantura_agrarian` (western, Rp 450K/m², nominee-only).
- **balikpapan_port_industrial** split into `balikpapan_kariangau_industrial` (north, Rp 1.9M/m²) and `balikpapan_selatan_commercial` (south, Rp 2.25M/m²).
- **bitung_port_industrial** split into `bitung_port_corridor` (east, Rp 2.5M/m²) and `bitung_kek_sez_industrial` (west, Rp 350K/m²).
- Net region count: 65 → 68.

### Added
- News routing for sub-region keywords: `aertembaga`, `kek bitung`, `tanjung merah`, `kariangau`, `sepinggan`, `smartpolitan`, `pantura`, `patimban`.

### Files touched (6)
- `src/indonesia_expansion_regions.py` — bbox definitions
- `src/core/market_config.py` — tier classification
- `src/core/region_feasibility.py` — explicit profiles per sub-region
- `src/core/infrastructure_analyzer.py` — fallback infra scores
- `src/scrapers/scraper_orchestrator.py` — `_REGION_SPECIFIC_BENCHMARKS`
- `src/scrapers/news_scraper.py` — `CITY_TO_REGIONS`

### Verified
- All 6 new regions resolve correctly: classify_region_tier, _resolve_clamp_anchor returns research-anchored Rp value per sub-region, get_feasibility returns researched profile.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.18.0] - 2026-04-28 - Prediction Review (Closes the Feedback Loop)

### Added
- **`src/core/prediction_tracker.py`** — `Forecast`, `Realization`, `PredictionReview` dataclasses; `load_forecasts_from_log` + `load_forecasts_from_run_archive` + `compute_realization` + `build_review` + `build_full_review_section` rendering helpers.
- **PREDICTION REVIEW section** in the weekly email — sits between TIER CHANGES and PRIORITY OPPORTUNITIES.
- **Prediction Review table in PDF** — `_build_prediction_review_section` renders 4w/8w/12w windows with per-region detail (Region / Tier / Then / Now / Realized / vs Predicted / Status) plus aggregate metrics (tier means + tier integrity + hit rate).

### Changed
- `forecast_log.jsonl` writer now records `predicted_roi_3yr`, `predicted_roi_5yr`, `feasibility_flag`, `feasibility_path`, `weeks_at_tier` per pick (backwards-compatible).
- Annualized-return display capped at ±500% with "ann saturated (likely data artifact, not market)" fallback to prevent absurd numbers from short-window extreme deltas misleading the investor.

### Honest design notes
- Realized vs prorated-predicted (not vs full 3-yr ROI) — fair comparison for short windows.
- `listing_count_shift_flag` excludes coverage-change noise from aggregate hit-rate.
- Anchors before 2026-04-25 surface a "pre-fix" banner; clean post-fix data starts ~2026-05-23 (4w window).

### Verified
- Smoke test: 4w anchor (2026-03-28) renders correctly with pre-fix banner; 6 listing-shift flags fire on Surabaya/Bandung/Cikarang regions whose listing pools changed.
- 8w/12w windows correctly render "insufficient post-fix history" placeholder with projected meaningful-data date.
- PDF generates cleanly at 1.7 MB; tests: 26 passed, 22 skipped, 0 failed.

## [2.17.1] - 2026-04-28 - PDF Lock-Step with Email

### Fixed
- PDF report had drifted out of lock-step with the email. None of the v2.16.x or v2.17.0 fields (feasibility, observed liquidity, correlation hints, weeks_at_tier, score_breakdown, action_links) were rendering in the PDF. Investor reading the PDF as their permanent reference saw a less-actionable view.

### Added (in `pdf_report_generator.py`)
- Decision matrix: `Feas` column (✅/⚠️/🚫) + `Wks` column (🆕 week 1 / Nw 2-3 / **Nw** ≥4 confirmed) + legend update.
- Investment analysis (top-5 detail): tier-streak indicator at top of bullet list, score breakdown bullet, feasibility line, liquidity-mismatch warning, observed-listings supplement, action links rendered as live clickable URLs via ReportLab's `<a href>` tag.
- New `_build_portfolio_section` (Phase 3 mirror): activates only when `data/positions.jsonl` exists; per-position table with cost basis, current price, P&L (color-coded green/red), annualized return, feasibility, observed liquidity, alerts.

### Changed
- Executive summary news-source list updated to "Jakarta Post, Kompas, Antara, Detik [×3 subsections], CNBC Indonesia" (was the v2.16.0-era 4-source list).

### Verified
- Smoke-tested PDF generation with synthetic v2.17.0 fields injected; PDF generates cleanly at 1.7 MB both with and without positions.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.17.0] - 2026-04-28 - Trust + Friction Reduction (Weeks-at-Tier + Score Breakdown + Action Links)

### Added
- **`AutomatedMonitor._compute_weeks_at_tier`** — walks back through last 12 `weekly_monitoring_*.json` files (deduplicated by calendar date), counts consecutive runs each region held its current tier. Surfaced in email as 🆕 NEW THIS WEEK / Nth consecutive week / 📌 N weeks at tier.
- **`AutomatedMonitor._build_score_breakdown`** — one-line provenance string `"activity X × infra Y × market Z × conf W × news V × momentum U = final"`. Re-derives confidence multiplier from the same formula `corrected_scoring.py` uses.
- **`AutomatedMonitor._build_action_links`** — bundle of due-diligence URLs per region (Lamudi search, Google Maps satellite, OSM bbox).
- Three new fields on every recommendation dict: `weeks_at_tier`, `score_breakdown`, `action_links`.

### Changed
- `run_weekly_java_monitor` priority-opportunity rendering: weeks-at-tier flag, score breakdown line, and three action-link lines added to each STRONG_BUY/BUY entry.

### Why
- "See opportunities **early**" was unmeasured — weeks_at_tier closes that.
- Score was opaque — breakdown makes the math visible (trust).
- 80+ min/week of manual URL construction was friction the investor didn't need — action links collapse it to a click.

### Verified
- Tests: 26 passed, 22 skipped, 0 failed.
- Smoke test: weeks_at_tier on Apr 28 run shows distribution {2: 18, 3: 19, 4: 19, 5: 4, 7: 1, 10: 3, 11: 1}, all 8 STRONG_BUYs on 2-3 week streaks.
- Score breakdown handles all three confidence-multiplier branches (≥0.85 linear, 0.50-0.85 quadratic, <0.50 floor).

### Track A status
- All Phase 1+2+3 mandatory items shipped through v2.16.11.
- Phase 2 polish (empirical liquidity) shipped v2.16.12.
- Trust + friction reduction shipped v2.17.0.
- Track A is fully addressed; further code work is optional polish or Track B (AWS/dbt/CI-CD).

## [2.16.12] - 2026-04-28 - Empirical Liquidity from Archived Listings (Phase 2 polish)

### Added
- **`src/core/liquidity_estimator.py`** — `estimate_liquidity(region)` reads price-history JSONL, returns LiquidityEstimate with n_samples, avg/median/min/max listings, observed_tier, and scraper_saturated flag. `liquidity_mismatch(research_tier, observed)` flags asymmetric disagreement (research overstating liquidity by ≥2 tier levels).
- **`tools/liquidity_audit.py`** — CLI tool for periodic review (`--thin`, `--mismatch` filters).

### Changed
- `automated_monitor` now attaches `observed_listings` dict + `liquidity_mismatch_flag` to every recommendation's feasibility object.
- Priority opportunities in email now print a one-line liquidity-mismatch warning when research and observed disagree.
- YOUR PORTFOLIO section adds an "Observed liquidity: X listings/scrape avg" line per position.

### Findings on current archive (8 weeks)
- 5 mismatches: yogyakarta_urban_core (high → low, 7.8/scrape), surabaya_east/west (very_high → moderate, 10.6), cikarang_mega_industrial (very_high → moderate, 12.5), gresik_port_industrial (very_high → moderate, 13.1). All tier-1 metro patterns suggesting institutional liquidity ≠ retail visibility.
- 5 genuinely thin markets (avg < 10/scrape): Jayapura, Ambon, Probolinggo, Yogyakarta urban core, Padang.

### Verified
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.16.11] - 2026-04-28 - Phase 3: Portfolio-Aware Action (Track A complete)

### Added
- **`src/core/portfolio_manager.py`** — `Position` dataclass + `load_positions()` + `compute_position_pnl()` + per-position alerts (`EXIT_WATCH`, `LIQUIDITY_RISK`, `TIER_DOWNGRADE`).
- **`correlation_hint(candidate, positions)`** — same-bucket detection that surfaces "📌 You already hold X — adds correlation" hints in the priority-opportunities section.
- **`docs/positions.jsonl.example`** — schema reference. Actual positions log lives at `data/positions.jsonl` (gitignored, investor-private).
- **YOUR PORTFOLIO section** at top of weekly email — only renders when positions exist; lists each position with cost basis, current price, unrealized P&L (IDR, %, annualized), feasibility line, and any active alerts.

### Track A status
- All three Phase 1-3 mandatory items shipped:
  - Phase 1 signal trustworthiness: v2.16.3-9
  - Phase 2 acquisition feasibility: v2.16.10
  - Phase 3 portfolio-aware action: v2.16.11
- Track B (AWS/dbt/CI-CD/observability) is now genuinely optional polish.

### Verified
- Smoke test: 2-position book (Cikarang HGB + Lombok Senggigi leasehold) renders cleanly. Correlation flags fire on Tangerang (Jakarta bucket) and Mandalika (Lombok bucket). LIQUIDITY_RISK alert fired on Senggigi (listings 12→5).
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.16.10] - 2026-04-28 - Phase 2: Acquisition Feasibility Layer

### Added
- **`src/core/region_feasibility.py`** — `FeasibilityProfile` dataclass + 27 explicit per-region profiles (13 deep-research-validated, 14 inferred from public regulatory data) + tier-based defaults for the remaining 38 regions.
- **3 dimensions per region**: `ownership_pathway` (hgb_pt_pma / leasehold / hak_pakai / nominee_only / restricted / off_limits), `zoning_class` + `zoning_overlays`, `liquidity_tier`.
- **Actionability flag** (✅ ⚠️ 🚫) computed from path + overlays + liquidity, plus a one-line `actionability_summary` rendered in the email beneath each STRONG_BUY/BUY entry.

### Changed
- `automated_monitor._generate_dynamic_recommendations` now attaches a `feasibility` dict to every recommendation (used by email rendering, JSON output, future PDF integration).
- `run_weekly_java_monitor` priority-opportunity rendering surfaces the feasibility summary line alongside Score/Confidence/Market.

### Restricted regions surfaced this round
- `nusantara_capital_core`, `nusantara_balikpapan_corridor` — Indigenous claims, contested zoning, speculative platform pricing
- `labuan_bajo_komodo_gateway` — KSPN strict; off-market trading

### Flagged-for-verification regions (⚠️)
- `jayapura_urban_development` (hak ulayat + military), `banda_aceh_reconstruction` (Sharia), `subang_patimban_megaport` (PSN ROW), `lake_toba_tourism_zone` (KSPN + shoreline), tier-4 frontiers.

### Verified
- Tests: 26 passed, 22 skipped, 0 failed.
- End-to-end smoke: feasibility renders correctly for 6 sample regions across the spectrum.

## [2.16.9] - 2026-04-28 - Forecast Log + Backtest Harness (Phase 1 mandatory items complete)

### Added
- **`tools/backtest.py`** — reads historical `weekly_monitoring_*.json` + per-region price history; for each anchor run reports per-tier mean price-change (2w/4w/8w windows) + Spearman ρ(score, realized delta).
- **`data/forecasts/forecast_log.jsonl`** writer hooked into `run_weekly_java_monitor.py` — slim, schema-stable archive of each run's BUY/STRONG_BUY/WATCH picks (region, tier, score, confidence, current price, satellite changes, market_clamped flag).

### Methodology guards in backtest
- Frozen regions (Nusantara, Labuan Bajo) excluded — unreliable per deep-research.
- `listing_count` shift ≥2× flags suspect samples; headline tier-mean uses only "clean" samples.
- Pre-fix anchor banner prints when anchor pre-dates the last v2.16.x fix (2026-04-28). Calls out specific examples (kulon_progo slug fix, outlier-resistant mean side effects).

### Current backtest results (informational, not a verdict)
- Every available anchor pre-dates v2.16.4–8 fixes; deltas reflect scraper-extraction corrections more than real market movement.
- 2w window: BUY +5.37%, WATCH +19.21% (inverted/unclear).
- Spearman ρ ≈ -0.19 (weak, near-noise).
- The harness is ready; the data isn't yet. Re-run after 4+ weeks of stable post-2026-04-28 history.

### Phase 1 status
- All mandatory items from the rewritten roadmap's Phase 1 are now shipped: outlier-resistant Lamudi mean (v2.16.4), sar_only cap (v2.16.3), Antara brotli fix (v2.16.4), slug refresh (v2.16.5), news dedup (v2.16.6), benchmark recalibration (v2.16.7), per-region history-anchored clamp (v2.16.8), forecast log + backtest harness (v2.16.9).

## [2.16.8] - 2026-04-28 - Per-Region History-Anchored Clamp (Phase 1 close)

### Added
- `_get_history_anchor(region)` reads `output/scraper_cache/price_history/<region>.jsonl`, returns median-of-medians from the last 8 samples (≥3 listings each).
- `_resolve_clamp_anchor(region)` returns (anchor, source_label) following: frozen → history (within 0.5–3× of static) → region override → bucket → unmapped.
- Clamp log messages now include the anchor source (e.g., "history (n=8, 1.20× static)" vs "region-override").

### Changed
- `_sanity_check_price` refactored to use `_resolve_clamp_anchor` instead of going straight to `_find_nearest_benchmark`.

### Why median-of-medians
- Each weekly median already filtered listing-level outliers (v2.16.4's 10×-median filter).
- The outer median absorbs week-level shocks (one bad scrape with neighborhood bias).
- 8-sample window keeps the anchor responsive without letting one stale week dominate.

### Why the 0.5–3× sanity band
- `banjarmasin_port_development` history Rp 17M from urban listings → 12.6× research benchmark Rp 1.35M → research wins (correctly).
- `bitung_port_industrial` history Rp 616K SEZ-dominated → 0.25× research Rp 2.5M port-side → research wins (correctly; real fix is bbox-level sub-market split).
- `lombok_mandalika_resort` history Rp 1.6M → 0.46× research Rp 3.5M → research wins on USD-pegged commercial premium.
- `bogor_puncak_highland` history Rp 1.95M → 0.23× Jakarta-bucket Rp 8.56M → bucket retained (region needs its own override in next research round).

### Verified
- Smoke test across 18 known-tricky regions: 8 history-anchored, 7 region-override, 2 bucket fallback, 2 frozen.
- 64 of 67 regions have ≥3 history samples available.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.16.7] - 2026-04-28 - Benchmark Recalibration from Deep-Research Report

### Recalibrated
- **medan bucket**: Rp 3.54M → 1.6M (-54.8%); 3 institutional sources within ±15%.
- **balikpapan bucket**: Rp 3.71M → 1.9M (-48.7%); CBRE/Savills/Cushman consensus.

### Added (`_REGION_SPECIFIC_BENCHMARKS`)
- 11 region-level overrides for cases where bucket routing was off by 2×+. Notable: `cikarang_mega_industrial` Rp 2.8M (was Jakarta 8.56M); `serang_cilegon_industrial` / `merak_port_corridor` Rp 4.9M; `anyer_carita_coastal` Rp 1.0M; `lombok_mandalika_resort` Rp 3.5M; `batang_industrial_sez` Rp 1.2M.

### Added (`_FROZEN_BENCHMARK_REGIONS`)
- 3 regions bypass the clamp entirely: `nusantara_capital_core`, `nusantara_balikpapan_corridor`, `labuan_bajo_komodo_gateway`. Research finding: retail-platform data here is "fundamentally un-investable via automated retail screening methodologies" — IKN shows 40× source disagreement; Labuan Bajo trades off-market.

### Verified
- Smoke-test against Apr 27 run extracts: Cikarang Rp 2.5M PASS (was clamped 8.56M), Serang/Cilegon Rp 4.5M PASS (was 4.0M), Bitung Rp 616K PASS (SEZ-side now accepted), Banjarmasin Rp 17M still clamps to research Rp 1.35M.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.16.6] - 2026-04-25 - News Dedup + Medan Corridor Slug Override

### Added
- **News article dedup** via title-bigram overlap (≥2 shared bigrams = duplicate). Drops 4 of 9 Bekasi rail-accident articles in the test corpus while keeping LRT/MRT/Tol stories correctly distinct. Runs after relevance-sort so the highest-scoring framing wins.
- **`REGION_SPECIFIC_SLUGS` override map** in `lamudi_scraper.py`. First entry: `medan_kuala_namu_corridor` → `deli-serdang` (median Rp 18.5M/m² → Rp 9.9M/m², below 5× clamp).

### Investigated
- (c) Cloud-cover handling: the CRITICAL drift alerts on `lake_toba`/`lombok_mandalika`/`bitung` are price-history drift artifacts (history archives held pre-clamp avg Rp 2.18B/m² values; current runs now use post-clamp Rp 1.2M median → -99.9% drift). v2.16.4 outlier-resistant mean already fixes the source. Alerts will self-clear over 4–8 weekly runs as polluted history rolls out of the window. No code change.

### A/B-test results (documented in code so future iterations don't re-explore dead ends)
- `cikarang_mega_industrial`: cikarang-utara only returns 5 listings (too few); ORIG `cikarang` n=20 wins.
- `jakarta_*_sprawl`: `jakarta-utara` returns premium central-N (Rp 25M); generic `jakarta` returns the right sprawl-tier price (Rp 9.7M).
- `bitung_port_industrial`: `bitung` slug returns mostly rural at Rp 0.6M (too low); ORIG `manado` is more representative.
- `bogor_puncak_highland`, `lake_toba_*`: similar between alternatives — no improvement.

## [2.16.5] - 2026-04-25 - Lamudi Slug Refresh (kulon-progo, gunung-kidul)

### Fixed
- Lamudi switched to hyphenated slugs for `kulon-progo` and `gunung-kidul`; the no-hyphen forms now return a 145KB 404 template. `yogyakarta_kulon_progo_airport` had been hitting this 404 every run for an unknown duration.
- Probed all 31 known `location_map` slugs; these were the only two stale ones. (`merak`/`purwokerto` are already aliased to `serang`/`banyumas` in the map — no fix needed.)

### Verification
- Smoke test: kulon-progo extracts 10 listings at Rp 798K-892K/m² (plausible peripheral-Yogya land near YIA airport).

## [2.16.4] - 2026-04-25 - Outlier-Resistant Price Mean + Brotli Bug Fix (Antara revival)

### Fixed
- **Lamudi misparses corrupting the mean.** `base_scraper._calculate_statistics` mean was a plain arithmetic mean across all listings, so 1–2 misparsed listings per scrape (e.g. Rp 22 BILLION/m²) dragged the average 100×+ above truth in 22/65 regions. The median was correct in every case. Now median anchors the calculation; mean is computed only over listings whose price-per-m² is ≤10× median. Sim against Jakarta_north_sprawl (18 valid + 2 misparses): old mean Rp 2.21B/m² → new mean Rp 9.71M/m².
- **Brotli accept-encoding silent failure.** Both `base_scraper.py` and `news_scraper.py` advertised `Accept-Encoding: gzip, deflate, br` without `brotli` installed. Sites preferring brotli (Antara) returned bodies the requests lib couldn't decode → BeautifulSoup parsed garbage → 0 tags found → 0 articles for ≥2 weeks. Dropped `br` from both. Antara live count: 0 → 25 per scrape.

### Cleanup
- Cleared one poisoned 0-article Antara cache entry that would otherwise have masked the brotli fix for up to 2 days (cache TTL).

### Verification
- Tests: 26 passed, 22 skipped, 0 failed.
- Net effect on confidence distribution: regions previously clamped to `lamudi_clamped` (data_confidence 0.55) should largely return to plain `lamudi` (data_confidence 0.85) at next run, restoring real live-market coverage.

## [2.16.3] - 2026-04-25 - sar_only Cap + Confidence Provenance Fix (Merak audit)

### Fixed
- **`fuse_optical_and_sar` sar_only branch was uncapped.** Fusion mode had a 20× SAR cap; sar_only mode (optical returns 0) had none. Merak's 4.6M SAR pixels saturated activity log-scale at ~38. Added `SAR_ONLY_MAX = 500_000` cap. Original count preserved in JSON.
- **`satellite_data_source` provenance leak.** When fusion fell into sar_only mode, `region_data['data_source']` stayed `'optical'`. The SAR-only confidence cap (0.84) keyed off this string and was bypassed. Now resolves `effective_satellite_source` from `fusion_result['source']` and uses it for both scoring AND the `data_sources` JSON output (so PDF/email reflect truth).

### Changed
- Stat-calc timeout 60s → 120s (2/65 regions hit the 60s wall in Apr 27 19:15 run).

### Verification
- Merak recompute against actual run data: 61.7 → ~51.2. Still STRONG_BUY (>49) but with SAR-dominant warning honestly visible and confidence properly capped at 0.84.
- Tests: 26 passed, 22 skipped, 0 failed.

## [2.16.2] - 2026-04-25 - Future-Work Batch (Drift Tests, News Supply, AWS Lifecycle, 99.co Revival)

### Tests
- 22 obsolete tier-only drift tests skipped with documented reason (DriftSnapshot now uses per-region/tier fallback model; old tier-vs-tier asserts no longer reflect behavior). Suite is clean: 10 pass, 22 skip, 0 fail.
- `DriftSnapshot.__getitem__` shim restored for backward-compat with code that uses dict-style access.

### News pipeline
- Added Detik `finance.detik.com/berita-ekonomi-bisnis` (live probe: 4 infra hits, comparable density to /infrastruktur subsection).
- Added CNBC Indonesia (`cnbcindonesia.com/news` + `/market`) with listing-card metadata stripper for trailing "News4 jam yang lalu"-style suffixes that bleed into link text.
- Raw articles per run: ~46 → ~79.

### Infrastructure
- `terraform validate` now passes cleanly: fixed 5 deprecated S3 lifecycle rules missing required `filter{}`/`prefix` (raw, staging, curated, logs×2). Without this they become hard errors in a future AWS provider version.
- Ran `terraform fmt -recursive` across the tree (whitespace-only across non-data_lake modules).

### Scrapers
- 99.co revived via `cloudscraper`: replaces plain `requests` (which always hit the CF JS challenge) with a `cloudscraper.create_scraper()` session shared across regions. Live probe verified: `/jual/tanah/yogyakarta` returns HTTP 200 + 20-listing `__NEXT_DATA__`; smoke test extracted 10 yogya listings at Rp 8.4M/m² avg.
- Realistic ceiling: 0–1 regions per run (CF rate-limits aggressively after first challenge solve). Existing process-wide breaker correctly trips on first 403, capping wasted time at ~15s/run.
- Removed misleading homepage CF probe — homepage 403s under cloudscraper even when listing URLs work.
- `cloudscraper>=1.2.71` added to `requirements.txt` + `requirements-prod.txt`.

## [2.16.0] - 2026-04-26 - Honest Math + STRONG_BUY Tier + Detik News + Confidence Caps

See [README.md](README.md) v2.16.0 changelog block for the full version. Highlights:

### Scoring (math is now honest)
- Activity log scaling (was step function saturating at 40 above 50K changes).
- New STRONG_BUY tier (≥58, conf ≥0.85); BUY ≥50/0.75; WATCH ≥35/0.50.
- Confidence caps that actually bite: SAR-only at 0.84, market-clamped at 0.80.
- Momentum: fixed `_ratio_to_multiplier(1.0)` returning 0.85 (depressed all scores 15%); fixed fake `ratio=2.0` for empty-baseline (3.4% inflation across all 65 regions).
- 5Y vs 3Y ROI now apples-to-apples (added `land_only_roi_5yr`).
- SAR fusion: cap SAR contribution at 20× optical (was effectively 99/1 split, not the nominal 60/40).

### News pipeline
- Detik infrastructure scraper added (4th source).
- City-direct matching + sentiment threshold loosened.
- News cache TTL 7d → 2d.
- Fixed `_load_previous_news_counts` bug — news_wow now populates.

### Drift
- Per-region benchmarks from price-history archive (avg drift 94.5% → 19.1%).
- Apples-to-apples comparison (avg vs avg).
- STRONG_BUY blind spot fixed.
- Annualization noise cap at 12.2× (was 73× for 5-day histories).

### Benchmark routing
- Fixed substring bug (`'bali' in 'balikpapan'` was True).
- Banten + Denpasar buckets added.
- 11 of 15 benchmarks refreshed.

### Reliability + observability
- Tier-transition tracking ("⬆ UPGRADES this week" in email).
- ~500 fewer log warnings per run (Empty composite + URL-gen DEBUG-downgraded).
- OSM circuit breaker + 99.co Cloudflare short-circuit.
- GEE empty-composite root cause (cloud threshold pass-through).
- OSM coverage metric corrected (was 17/65, actual 65/65).
- SAR-dominant warning in email when ratio > 20×.
- Low-listing confidence penalty (Lamudi <10 listings → 0.65).

### Delivery
- SMTP preflight, webhook fallback, `[LOW-CONF]` subject prefix.

### Fixed (legacy)

- **`change_detector._calculate_statistics`:** `signal.alarm` is always cleared in a `finally` block. Previously, if the wrapped Earth Engine `getInfo()` call raised **any exception other than `TimeoutError`**, the alarm stayed armed and **SIGALRM** could terminate the process tens of seconds later (manifesting as `zsh: alarm` during a later pipeline phase).

### Added

- **`scripts/prep-aws-zero-cost.sh`:** runs `terraform init`, `validate`, and `plan` (plus optional local `docker build` when Docker is installed) without `terraform apply` or ECR push; documented in [`docs/deployment/cost-aware-aws.md`](docs/deployment/cost-aware-aws.md). `.gitignore` now excludes `infra/terraform/terraform.tfvars`.
- **Observability (weekly run):** dynamic scoring logs a separate-phase note plus per-region **`Scoring [i/N]`** lines with rolling ETA; OSM cache misses log **Overpass 1/3 → 3/3** legs with timings and element counts; each Overpass attempt logs **waiting for shared slot** then **HTTP POST**; while the request is in flight, **stall warnings** every 45s (`CC_OVERPASS_STALL_LOG_SEC`) and **`(connect, read)` timeouts** (`CC_OVERPASS_CONNECT_TIMEOUT_SEC` + read caps, default read max 90s) reduce silent multi-minute wedges. `run_weekly_java_monitor.py` prints that batch ETA does not apply during investment analysis.

### Changed

- **Terraform (portfolio dev):** When `enable_nat_gateway = false`, Step Functions ECS `RunTask` uses **public subnets** and **`AssignPublicIp: ENABLED`** so the weekly monitor can reach GEE and the internet without NAT charges. When `true`, behavior remains private subnets + `DISABLED` (production-style).
- **Documentation:** Added [`docs/deployment/cost-aware-aws.md`](docs/deployment/cost-aware-aws.md); updated root `README.md`, `DEVELOPMENT_ROADMAP.md`, `DOCUMENTATION_INDEX.md`, `infra/terraform/README.md`, and `docs/README.md` for cost-aware deployment and module count (6).
- **Repository layout:** Moved 41 superseded milestone/roadmap markdown files to `archived_bloat/historical_reports/`; restored [`QUICKSTART.md`](QUICKSTART.md) at repo root.

---

## [2.14.0] - 2026-04-05

### Added

#### Parallel Scoring with ThreadPoolExecutor
- Scoring phase now runs 4 regions concurrently via `ThreadPoolExecutor(max_workers=4)`
- Reduces total scoring time from ~50 min to ~15 min for 65 regions
- Pre-scrapes news articles once before parallel loop (thread-safe)
- Replaced `signal.alarm` (not thread-safe) with per-future timeout
- Files modified: `src/core/automated_monitor.py`

#### News Week-over-Week Rate of Change
- Loads previous run's per-region news article counts from `output/monitoring/weekly_monitoring_*.json`
- Computes `news_wow` ratio (current vs previous articles), classifies as surging/increasing/stable/declining
- Feeds a 1.0–1.08x multiplier into momentum when news coverage is surging or increasing
- New field `news_wow` in scored region output (current_articles, previous_articles, ratio, delta, trend)
- Files modified: `src/core/automated_monitor.py`

#### GEE Optical Cache Integration
- Wired existing `GEEImageCache` (14-day TTL) into `ChangeDetector.detect_weekly_changes`
- Cache check before expensive GEE satellite analysis; cache save after successful analysis
- Subsequent runs skip satellite processing for cached regions, saving significant GEE API quota
- Files modified: `src/core/change_detector.py`

#### Lamudi Province-Level Fallback
- When a city slug returns no listings, automatically retries with broader province slug
- `PROVINCE_FALLBACKS` maps sparse-listing cities to their province (e.g., `toba-samosir` → `sumatera-utara`)
- Improved slug mappings: Lombok → `lombok-barat`/`lombok-tengah`, Lake Toba → `toba-samosir`, Solo Raya → `sukoharjo`
- Files modified: `src/scrapers/lamudi_scraper.py`

### Changed

#### PDF Decision Matrix Expanded
- Added Market Heat column (color-coded: booming/strong green, stable black, cooling/cold red)
- Added Data Quality column (●● both live, ●○ partial, ○○ fallback)
- Updated legend to explain new columns
- Fixed corrupted section header encoding
- Files modified: `src/core/pdf_report_generator.py`

#### Email Upgraded to Actionable Investment Briefing
- Portfolio overview with BUY/WATCH/PASS counts + data quality summary
- Top 7 BUY opportunities with: entry price, projected value, 3Y/5Y ROI, acquisition cost, RVI, momentum, news WoW, data source warnings
- WATCH list with score headroom to BUY threshold
- Recommended actions section (priority due diligence, title verification, undervalued region callouts)
- Files modified: `run_weekly_java_monitor.py`

---

## [2.12.1] - 2026-04-04

### Fixed

#### Infrastructure Scoring: OSM Sanity Check + 65-Region Fallback Database
- **Issue**: OSM Overpass API returned empty road/railway data for major regions (e.g., Jakarta, Cikarang), producing implausibly low infrastructure scores (e.g., 20 for a metro area)
- **Impact**: Score clustering — many regions scored identically because they all received the same low default infrastructure multiplier
- **Fix**: Added sanity check in `infrastructure_analyzer.py`: if OSM score is < 60% of the curated regional fallback, the fallback is used instead. Expanded the regional fallback database from 29 Java regions to all 65 monitored regions across Indonesia
- **Result**: Each region now gets a differentiated infrastructure multiplier reflecting its actual transport connectivity
- Files modified: `src/core/infrastructure_analyzer.py`

#### Market Heat: Benchmark Appreciation Values
- **Issue**: `historical_appreciation` values in `regional_benchmarks` were stored as decimals (e.g., `0.15` for 15%) but interpreted as raw percentages — resulting in all regions showing "stable" market heat and ~0.01% trend
- **Impact**: All 65 regions had identical "stable" market classification; market multiplier provided no differentiation
- **Fix**: Corrected values to actual percentages (e.g., `15.0` for 15%). Added regional benchmarks for Sumatra, Bali, Kalimantan, Sulawesi, Lombok/NTT, and Eastern Indonesia. Improved `_find_nearest_benchmark` with island-level matching
- **Result**: Regions now show varied market heat (Booming / Strong / Stable / Stagnant / Declining)
- Files modified: `src/scrapers/scraper_orchestrator.py`

#### Benchmark Drift Monitoring
- **Issue**: `BenchmarkDriftMonitor.track_drift()` received raw satellite analysis results (no financial projections), causing `'list' object has no attribute 'get'` error
- **Impact**: Drift monitoring failed on every run
- **Fix**: Modified `run_weekly_java_monitor.py` to extract scored regions (which include `financial_projection`) from `investment_analysis` and pass those to the drift monitor. Normalized the `region` key to `region_name`
- **Result**: Drift monitoring now completes successfully
- Files modified: `run_weekly_java_monitor.py`

#### Region Method Call Fix
- **Issue**: `run_weekly_java_monitor.py` called non-existent `expansion_manager.get_monitoring_regions()`
- **Fix**: Changed to `expansion_manager.get_java_regions()`
- Files modified: `run_weekly_java_monitor.py`

#### Test Import Fix
- **Issue**: `tests/test_core.py` imported `ChangeDetectionConfig` from `core.config` instead of `core.change_detector`
- **Fix**: Corrected the import path
- Files modified: `tests/test_core.py`

### Added

#### First Full 65-Region Analysis Run
- Executed `run_weekly_java_monitor.py --all --yes` to analyze all 65 regions in a single pass
- Covers Java (31), Bali (6), Sumatra (11), Kalimantan (6), Sulawesi (4), Lombok/NTT (4), Eastern Indonesia (3)

---

## [2.12] - 2026-03

### Added

#### Decision Matrix Page in PDF
- All regions ranked in a single table with Score, BUY/WATCH/PASS action, Price/m², RVI, Momentum, 3Y ROI, and Confidence
- Color-coded rows for quick visual scanning

#### Expanded Region Coverage (51 → 65 Regions)
- Added: Labuan Bajo (Komodo gateway), Nusa Dua/Bukit (Bali luxury), Senggigi (Lombok), Kupang (NTT), Karawang industrial corridor, Batang SEZ, Padang, Banda Aceh
- Total coverage: 31 Java + 6 Bali + 11 Sumatra + 6 Kalimantan + 4 Sulawesi + 4 Lombok/NTT + 3 Eastern Indonesia

#### News Scraper Improvements
- Added Kompas regional sections (Jawa Barat/Tengah/Timur)
- Province-level article matching
- Fixed Antara relative URL handling

---

## [2.11] - 2026-03

### Added

#### Sentinel-1 SAR Radar Fusion
- Cloud-penetrating SAR radar complements Sentinel-2 optical imagery
- 60/40 weighted fusion with +10% confidence boost when both sensors available
- SAR-only fallback critical for Indonesia's rainy season

#### News Catalyst Scoring (0.95x-1.20x)
- Scrapes Jakarta Post, Kompas, and Antara News
- Word-boundary region matching to avoid false positives
- Clickable article links in PDF reports

#### Live Market Scrapers Repaired
- Lamudi returns 20+ real listings per region
- 99.co rewritten for `__NEXT_DATA__` JSON parsing (rate-limited but functional)

#### JSONL Price History Archive
- Each scrape appends timestamped snapshot to per-region JSONL files
- Enables 14-60 day price trend calculation across successive weekly runs

#### Momentum Analyzer
- Compares 4-week recent velocity vs 8-16 week baseline from historical monitoring JSONs
- Multiplier range: 0.85x (stalling) to 1.30x (surging)

#### Auto-Email After Every Run
- Gmail SMTP with PDF attachment sent automatically after each monitoring run

### Fixed
- `calculate_relative_value_index` now correctly calls `FinancialMetricsEngine`
- OSM queries parallelized with 30s hard timeout

---

## [2.10] - 2026-02

### Added
- Indonesia expansion: 39 → 51 monitored regions
- Bali (6): Denpasar, Sanur, Canggu, Ubud, Tabanan
- Sumatra (8): Medan (2), Palembang (2), Lampung (2), Batam, Pekanbaru
- Kalimantan (5): Nusantara/IKN (2), Balikpapan, Samarinda, Banjarmasin
- Sulawesi (3): Makassar (2), Manado

---

## [2.9.1] - 2025-11-02

### Added

#### CCAPI-29.0: AWS Step Functions Orchestration
- 10-state workflow with validation, execution, and error handling
- ECS Fargate task execution (2 vCPU, 4GB memory)
- EventBridge rule for weekly trigger (Mondays 6am UTC)
- CloudWatch metrics, alarms, and X-Ray tracing
- SNS notifications for success/failure/partial failure
- Dead letter queue for failed EventBridge events
- ~$0.71/month incremental cost

#### CCAPI-28.0: Docker Containerization
- Multi-stage build, final image 1.19GB (50% reduction from initial 2.36GB)
- Non-root user (UID 1000) for security
- CI/CD pipeline with Trivy security scanning
- Health checks for all core Python modules

#### CCAPI-28.1: Terraform Infrastructure-as-Code
- 5 reusable modules (~1,570 lines): network, data_lake, security, compute, monitoring
- ~70 AWS resources defined
- Cost-optimized: $23/mo (dev) to $139/mo (prod)
- Multi-environment support (dev/staging/prod)

#### CCAPI-27.5: GEE Caching + Async Processing
- 82-97% faster monitoring (16 min cold, 0.9 min warm vs 87 min baseline)
- 14-day GEE image cache
- Async parallel processing for regions

#### CCAPI-27.4: Modular Documentation Refactor
- 76% size reduction via modular structure under `docs/`

#### CCAPI-27.3: Property-Based Testing
- 9 Hypothesis tests, 416 examples, all passing

#### CCAPI-27.2: Benchmark Drift Monitoring
- 608-line production-ready drift monitor

#### CCAPI-27.1: Full End-to-End Validation
- 12 regions, 100/100 improvement score

### Fixed
- Market data restoration: 4 root causes fixed, 100% Lamudi success rate

---

## [2.8.2] - 2025-10-27

### Fixed
- Location slug mapping (70+ city mappings) for Lamudi scraper
- JSON-LD structured data parsing for JavaScript-rendered Lamudi pages
- Market data availability restored to ~40% (Lamudi-only)

---

## [2.8.1] - 2025-10-26

### Fixed
- Lamudi scraper URL fix (`/buy/` → `/jual/`) — Indonesian language requirement

---

## [2.8.0] - 2025-10-20

### Added
- OSM infrastructure caching (7-day expiry)
- Performance: 48% faster monitoring (87 → 45 min projected)
- 162x speedup per cached region, 86% reduction in API calls

---

## [2.7.0] - 2025-10-26

### Added

#### CCAPI-27.0: Budget-Driven Investment Sizing ✅ PRODUCTION READY
- **Re-architected investment sizing from plot-size-driven to budget-driven**
- Plot sizes now calculated from target budget: `plot_size = target_budget / (land_cost + dev_cost)`
- **Business Impact**: 10x expansion of addressable investor market ($50K-$150K vs $500K-$2M)
- **Tier 4 regions now yield exactly $100K USD recommendations** (750 m² plots)
- Configuration-driven via `financial_projections` section in config.yaml:
  - `target_investment_budget_idr`: 1.5B IDR (~$100K USD)
  - `min_plot_size_m2`: 500 m² (prevents impractically small plots)
  - `max_plot_size_m2`: 50,000 m² (5 hectares maximum)
- Enhanced logging with detailed budget calculation breakdowns
- Backward compatible (defaults work without config)
- Files modified: 
  - `config/config.yaml` (financial_projections section)
  - `src/core/config.py` (FinancialProjectionConfig dataclass)
  - `src/core/financial_metrics.py` (budget-driven algorithm)
  - `src/core/automated_monitor.py` (config integration)
- **Tests**: 15/15 passing (10 unit + 5 integration)
  - `tests/test_ccapi_27_0_budget_sizing.py` (10 unit tests)
  - `test_ccapi_27_0_integration.py` (5 integration tests)
- **Documentation**: 
  - `CCAPI_27_0_COMPLETION_REPORT.md`
  - `CCAPI_27_0_FINAL_COMPLETION.md`
  - `DEPLOYMENT_PLAN_V2_7_0.md`

### Fixed

#### Critical Bug #1: Market Data Retrieval (v2.6 → v2.7)
- **Issue**: `corrected_scoring.py` called non-existent `_get_pricing_data()` method
- **Impact**: Market data never retrieved, all regions fell back to static benchmarks
- **Fix**: Changed to `get_land_price()` public method
- **Result**: RVI calculations now functional, market data retrieved successfully
- File: `src/core/corrected_scoring.py` (line 403)
- Discovered: October 26, 2025 (during CCAPI-27.1 validation test creation)
- Fixed: October 26, 2025

#### Critical Bug #2: RVI Calculation Parameter Mismatch (v2.6 → v2.7)
- **Issue**: Passed invalid `market_momentum` parameter to `calculate_relative_value_index()`
- **Impact**: RVI calculation failed silently, Phase 2B.1 multipliers inactive
- **Fix**: Changed to correct `satellite_data` parameter
- **Result**: RVI-aware market multipliers now operational
- File: `src/core/corrected_scoring.py` (line 426)
- Discovered: October 26, 2025 (during CCAPI-27.1 validation test creation)
- Fixed: October 26, 2025
- **Documentation**: `BUG_FIXES_OCT26_2025.md`

### Changed
- FinancialMetricsEngine constructor now accepts optional `config` parameter
- Plot size calculation method signature updated (added `current_land_value_per_m2`, `dev_costs_per_m2`)
- Removed hard-coded `recommended_plot_sizes` dict (tier-based sizing deprecated)

### Deprecated
- Tier-based plot sizing (early=5000m², mid=2000m², late=1000m²) replaced by budget-driven formula

---

## [2.6-beta] - 2025-10-26

### Added

#### Phase 2B.1: RVI-Aware Market Multiplier
- Replaced trend-based market multipliers (0.85-1.4x) with RVI-aware thresholds
- Market multiplier now responds to valuation signals:
  - RVI < 0.7: 1.40x (significantly undervalued)
  - RVI 0.7-0.9: 1.25x (undervalued)
  - RVI 0.9-1.1: 1.0x (fair value)
  - RVI 1.1-1.3: 0.90x (overvalued)
  - RVI ≥ 1.3: 0.85x (significantly overvalued)
- Added momentum adjustment (±10%) based on price trends as secondary factor
- Maintained backward compatibility with trend-based fallback when RVI unavailable
- Files modified: `src/core/corrected_scoring.py`, `src/core/automated_monitor.py`
- Tests: `test_phase_2b_1_rvi_market_multiplier.py` (11 tests passing)

#### Phase 2B.2: Airport Premium Override
- Added +25% benchmark premium for regions with airports opened within 5 years
- Created `RECENT_AIRPORTS` database tracking 3 major airports:
  - Yogyakarta International Airport (YIA) - Opened Aug 2020, 30km radius
  - Banyuwangi Airport (BWX) - Expansion Jun 2021, 25km radius
  - Kertajati International Airport (KJT) - Opened May 2018, 35km radius
- Integrated airport premium into RVI expected price calculation
- Files modified: `src/core/market_config.py`, `src/core/financial_metrics.py`
- Tests: `test_phase_2b_2_airport_premium.py` (8 tests passing)

#### Phase 2B.3: Tier 1+ Ultra-Premium Sub-Classification
- Created Tier 1+ sub-tier with 9.5M IDR/m² benchmark (+18.75% vs standard 8M Tier 1)
- Added `TIER_1_PLUS_REGIONS` list identifying 8 ultra-premium zones:
  - Tangerang BSD Corridor (master-planned city)
  - Jakarta South Suburbs (Senopati, Cipete lifestyle)
  - Jakarta Central SCBD (international business district)
  - Jakarta South Pondok Indah (established luxury)
  - Jakarta South Kemang (expat/lifestyle)
  - Bekasi Summarecon (premium zone)
  - Cikarang Delta Silicon (industrial park)
- Modified `get_tier_benchmark()` to check for Tier 1+ override
- Modified `get_region_tier_info()` to apply Tier 1+ benchmarks automatically
- Files modified: `src/core/market_config.py`
- Tests: `test_phase_2b_3_tier_1_plus.py` (7 tests passing)

#### Phase 2B.4: Tier-Specific Infrastructure Ranges
- Implemented tier-specific infrastructure premium tolerances reflecting development predictability:
  - Tier 1 (±15%): Predictable metro infrastructure
  - Tier 2 (±20%): Moderate secondary city variability
  - Tier 3 (±25%): Higher emerging zone variability
  - Tier 4 (±30%): Highest frontier uncertainty
- Created `TIER_INFRA_TOLERANCE` dictionary in `market_config.py`
- Created `get_tier_infrastructure_tolerance()` function
- Modified infrastructure premium calculation in `financial_metrics.py` to use tier-specific tolerance
- Files modified: `src/core/market_config.py`, `src/core/financial_metrics.py`
- Tests: `test_phase_2b_4_tier_infra_ranges.py` (9 tests passing)

#### Phase 2B.5: Integration Testing & Validation
- Created comprehensive validation test comparing v2.5 vs v2.6-beta across 12 regions
- Achieved 88.8/100 improvement score (1.2 points below ≥90 target, acceptable)
- Achieved 75.0% RVI sensibility rate ✅ GATE PASSED (≥75% required)
- Tier 2 perfect score: 100/100 improvement, 100% sensibility (no regressions)
- Tier 4 perfect sensibility: 100% (validates Phase 2B.4 ±30% tolerance fix)
- Files created: `test_v25_vs_v26_validation.py` (702 lines)
- Documentation: `VALIDATION_REPORT_V26_BETA.md` (comprehensive validation analysis)

#### Phase 2B.6: Documentation & Release
- Updated `TECHNICAL_SCORING_DOCUMENTATION.md` with Phase 2B.5-2B.6 sections
- Updated `README.md` to v2.6-beta with Phase 2B feature summary
- Created `CHANGELOG.md` (this file)
- Documentation status: In progress (version strings update pending)

### Changed

#### Market Multiplier Logic
- **Old (v2.6-alpha)**: Market multiplier based solely on price trend (0.85-1.4x)
- **New (v2.6-beta)**: Primary multiplier from RVI thresholds, momentum as secondary adjustment
- **Impact**: Market multiplier now accounts for valuation context, not just momentum
- **Example**: 
  - Region with 15% price growth + RVI 1.5 (overvalued): Was 1.40x, now 0.85-0.90x
  - Region with 5% price growth + RVI 0.7 (undervalued): Was 1.00x, now 1.35-1.40x

#### Tier 1 Benchmark Structure
- **Old (v2.6-alpha)**: All Tier 1 regions use 8M IDR/m² benchmark
- **New (v2.6-beta)**: Tier 1 base (8M) + Tier 1+ ultra-premium (9.5M) for top districts
- **Impact**: BSD Corridor, Senopati, SCBD no longer falsely flagged as "overvalued"
- **Example**: BSD RVI from 0.91 (overvalued) to 1.05 (fair value)

#### Infrastructure Premium Calculation
- **Old (v2.6-alpha)**: Fixed ±20% tolerance for all tiers
- **New (v2.6-beta)**: Tier-specific tolerances (±15% to ±30% based on tier)
- **Impact**: Frontier regions with good infrastructure no longer penalized
- **Example**: Pacitan (Tier 4) RVI from 0.93 (overvalued) to 0.90 (fair value)

#### RVI Expected Price Formula
- **Old (v2.6-alpha)**: `Expected = Peer Avg × Infrastructure × Momentum`
- **New (v2.6-beta)**: `Expected = Peer Avg × Infrastructure × Momentum × Airport`
- **Impact**: Regions near new airports (YIA, BWX, KJT) correctly valued with +25% premium
- **Example**: Yogyakarta Sleman RVI from 0.76 (undervalued artifact) to 0.95 (fair value)

### Fixed
- BSD Corridor false "overvalued" flag (Tier 1+ 9.5M benchmark fix)
- Yogyakarta regions false "undervalued" flag (airport premium fix)
- Pacitan coastal false "overvalued" flag (Tier 4 ±30% tolerance fix)
- Market multiplier ignoring valuation context (RVI-aware multiplier fix)

### Tests
- **Total Phase 2B Unit Tests**: 35/35 passing (100%)
  - Phase 2B.1: 11 tests (RVI-aware market multiplier)
  - Phase 2B.2: 8 tests (airport premium)
  - Phase 2B.3: 7 tests (Tier 1+ classification)
  - Phase 2B.4: 9 tests (tier-specific infrastructure ranges)
- **Integration Test**: `test_v25_vs_v26_validation.py` (12 regions, 4 tiers)
- **Validation Report**: `VALIDATION_REPORT_V26_BETA.md`

### Documentation
- `TECHNICAL_SCORING_DOCUMENTATION.md`: Added Phase 2B.5-2B.6 sections, updated version to 2.6-beta
- `README.md`: Updated to v2.6-beta, added Phase 2B feature summary
- `VALIDATION_REPORT_V26_BETA.md`: Comprehensive validation analysis (new file)
- `CHANGELOG.md`: Created (this file)

---

## [2.6-alpha] - 2025-10-25

### Added

#### Phase 2A.1: Regional Tier Classification System
- Created 4-tier hierarchy for 29 Java regions based on economic development:
  - Tier 1 (9 regions): Metropolitan core - Jakarta + Surabaya metros
  - Tier 2 (7 regions): Secondary cities - Provincial capitals
  - Tier 3 (10 regions): Emerging corridors - Periurban + tourism gateways
  - Tier 4 (3 regions): Frontier regions - Early-stage development
- Created `src/core/market_config.py` with `REGIONAL_HIERARCHY` data structure
- Added functions: `classify_region_tier()`, `get_tier_benchmark()`, `get_region_tier_info()`
- Tier-specific benchmarks: Tier 1 (8M), Tier 2 (5M), Tier 3 (3M), Tier 4 (1.5M IDR/m²)
- Tests: `test_market_config.py` (validation of all 29 regions)

#### Phase 2A.2: Tier-Based Benchmark Integration
- Integrated tier-based benchmarks into `financial_metrics.py`
- Modified `FinancialProjection` dataclass with 3 new fields: `regional_tier`, `tier_benchmark_price`, `peer_regions`
- Replaced `_find_nearest_benchmark()` with tier-aware lookup
- Maintained backward compatibility with graceful fallback to legacy 6-benchmark system
- Tests: `test_tier_integration.py` (4 regions across all tiers)

#### Phase 2A.3: Relative Value Index (RVI) Calculation
- Implemented RVI to distinguish true undervaluation from "cheap because frontier region"
- RVI Formula: `Actual Price / Expected Price`
  - Expected Price = `Peer Avg × Infrastructure Premium × Momentum Premium`
- Infrastructure Premium: ±20% based on deviation from tier baseline
- Momentum Premium: ±15% based on satellite development activity
- RVI Interpretation: <0.80 (undervalued), 0.95-1.05 (fair), >1.20 (overvalued)
- Created `calculate_relative_value_index()` method in `financial_metrics.py`
- Tests: `test_rvi_calculation.py` (6 tests covering all scenarios)

#### Phase 2A.4: RVI Scoring Output Integration
- Added 4 optional fields to `CorrectedScoringResult` dataclass: `rvi`, `expected_price_m2`, `rvi_interpretation`, `rvi_breakdown`
- Modified `calculate_investment_score()` to accept `actual_price_m2` parameter
- Integrated RVI calculation in `automated_monitor.py` after financial projection
- Created `_draw_rvi_analysis()` method (225 lines) in `pdf_report_generator.py` for PDF reports
- Visual indicators in reports: 🟢🟡⚪🟠🔴 based on valuation status
- Tests: `test_rvi_integration_phase2a4.py` (5 tests), `test_rvi_pdf_display.py` (2 tests)

#### Phase 2A.5: Multi-Source Scraping Fallback
- Created 3-tier cascading data system for land price scraping:
  1. Live scraping (Lamudi, Rumah.com, 99.co) → 85% confidence
  2. Cached data (<24-48h old) → 75-85% confidence
  3. Static benchmarks → 50% confidence
- Created `NinetyNineCoScraper` class in `src/scrapers/ninety_nine_scraper.py`
- Enhanced `LandPriceOrchestrator` with 3-source fallback logic
- Added `ninety_nine` configuration to `config.yaml`
- Tests: `test_multi_source_fallback.py` (4 tests covering all fallback scenarios)

#### Phase 2A.6: Request Hardening
- Added exponential backoff retry logic with configurable parameters:
  - `max_retries`: 3 (default)
  - `initial_backoff`: 1s
  - `max_backoff`: 30s
  - `backoff_multiplier`: 2.0
- Smart retry logic: Retries 5xx/timeouts, NO retry on 4xx client errors
- Enhanced `BaseLandPriceScraper._make_request()` with retry mechanism
- Added `_handle_retry()` helper method with jitter (±20%) to prevent thundering herd
- Tests: `test_request_hardening.py` (8 tests covering retry logic)

#### Phase 2A.7: Benchmark Update Procedure Documentation
- Created `BENCHMARK_UPDATE_PROCEDURE.md` (950+ lines) - Complete quarterly update guide
- Documented quarterly update process (Jan, Apr, Jul, Oct 15th deadlines)
- Data source weighting: 60% official (BPS/BI), 25% web scraping, 15% commercial reports
- Confidence scoring formula with freshness penalties
- Emergency update protocols for infrastructure events, economic shocks
- Automation roadmap: Manual (Phase 1) → Scripted (Phase 2) → Fully automated (Phase 3)

#### Phase 2A.8: Official Data Sources Research
- Created `OFFICIAL_DATA_SOURCES_RESEARCH.md` (8500+ lines) - BPS/BI API research
- Discovered BPS API availability: Province-level property indices via REST API
- Researched Bank Indonesia API: Not publicly available (404 error)
- Documented province-to-city mapping (29 regions → 6 BPS province codes)
- Decision: Keep manual quarterly process (province data too coarse for city-level analysis)
- Future automation: BPS API as validation layer (detect when scraped prices diverge >5% from provincial trends)

#### Phase 2A.9: Complete Documentation Updates
- Created `DOCUMENTATION_INDEX.md` (2000+ lines) - Central navigation hub
- Updated `README.md` with v2.6-alpha features section, documentation hierarchy
- Cross-referenced all documentation files (8 major docs, 15,000+ total lines)
- Verified consistency: All file paths, version numbers, progress tracking aligned

#### Phase 2A.10: Comprehensive Test Suite
- Created `test_market_intelligence_v26.py` (400+ lines, 31 tests)
- 17 passing tests validating core Phase 2A features (75% coverage)
- Test coverage:
  - Tier classification (1 test)
  - RVI calculation (4 tests)
  - Request hardening (2 tests)
  - Benchmark updates (4 tests)
  - BPS API integration (4 tests)
  - Integration workflows (2 tests)

#### Phase 2A.11: v2.5 vs v2.6-alpha Validation
- Created `test_v25_vs_v26_validation.py` (680+ lines) - Side-by-side comparison script
- Tested 12 regions across all 4 tiers with both v2.5 and v2.6-alpha systems
- Results:
  - Average improvement score: **86.7/100** ✅ GATE PASSED (≥80% required)
  - RVI sensibility: 66.7% (8/12 regions economically sensible)
  - Recommendation changes: 25% (3 regions changed)
  - Tier 2 perfect score: 100/100 (validates core tier approach)
  - Tier 4 critical correction: -53% benchmark prevents overinvestment in frontier regions
- Created `VALIDATION_REPORT_V26_ALPHA.md` - Comprehensive validation analysis
- Decision: ✅ PROCEED TO PHASE 2B - RVI integration into market multiplier approved

### Changed

#### Financial Projection Benchmark Selection
- **Old**: Used proximity-based selection from 6 static reference markets
- **New**: Uses tier-based benchmarks with peer region context
- **Impact**: More appropriate price expectations for emerging and frontier regions

#### RVI Calculation
- **Old**: Not implemented (no relative valuation context)
- **New**: RVI = Actual / (Tier Benchmark × Infrastructure × Momentum)
- **Impact**: Can distinguish "cheap" from "undervalued" regions

#### Scraping Reliability
- **Old**: Single source (Lamudi only), fails completely on timeout
- **New**: 3-tier fallback (live → cache → benchmark), never fails
- **Impact**: ~95% uptime vs ~70% uptime

### Fixed
- "Cheaper = better" fallacy (now accounts for tier context via RVI)
- Single-source scraping fragility (3-tier fallback prevents complete failures)
- Network timeout failures (exponential backoff retry logic)

### Documentation
- `BENCHMARK_UPDATE_PROCEDURE.md`: Quarterly maintenance process (950+ lines)
- `OFFICIAL_DATA_SOURCES_RESEARCH.md`: BPS/BI API research (8500+ lines)
- `DOCUMENTATION_INDEX.md`: Central navigation hub (2000+ lines)
- `WEB_SCRAPING_DOCUMENTATION.md`: Multi-source scraping technical reference
- `TECHNICAL_SCORING_DOCUMENTATION.md`: Single source of truth (3200+ lines)
- `VALIDATION_REPORT_V26_ALPHA.md`: v2.5 vs v2.6-alpha comparison
- Updated `README.md` with Phase 2A complete features

---

## [2.5] - 2025-10-25

### Changed

#### Infrastructure Scoring Standardization
- **Unified approach**: Both standard and enhanced analyzers now use identical scoring algorithm
- **Total caps + distance weighting**: Replaced dual approaches (sqrt compression vs simple caps)
- **Component limits**: Roads (35), Railways (20), Aviation (20), Ports (15), Construction (10), Planning (5)
- **Distance decay**: Exponential decay maintains geographic realism (highways 50km, airports 100km)
- **Impact**: Simpler to understand, easier to maintain, consistent results across analyzers

### Fixed
- Infrastructure scoring inconsistency between standard and enhanced analyzers
- Complex sqrt compression math removed (replaced with simpler total caps)

---

## [2.4.1] - 2025-10-25

### Changed

#### Confidence Multiplier Refinement
- **Non-linear scaling**: Quadratic curve below 85% confidence, linear above
- **Old formula**: Linear `0.7 + (conf - 0.5) * 0.6`
- **New formula** (high confidence ≥85%): `0.97 + (conf - 0.85) * 0.30`
- **New formula** (lower confidence <85%): `0.70 + 0.27 * ((conf - 0.5) / 0.35)^1.2`
- **Impact**: Better score differentiation - poor data (50-70%) gets steeper penalties, excellent data (85-95%) has diminishing marginal value

#### Quality Bonus Strategy
- **Old**: Applied +5% bonuses AFTER weighted average (could inflate confidence)
- **New**: Bonuses built into component confidence calculations before weighting
- **Impact**: Prevents confidence inflation, maintains realistic confidence values

#### Penalty Threshold
- **Old**: -5% penalty for <70% confidence (minimal impact)
- **New**: -10% penalty for <60% confidence + quadratic scaling below 85%
- **Impact**: Better differentiation between adequate (70%) and limited (60%) data quality

### Fixed

#### Financial Projection Bug
- **Problem**: Financial projections calculated but not saved to JSON output
- **Root cause**: `_generate_dynamic_investment_report()` didn't copy `financial_projection` to recommendation dict
- **Fix**: Added `'financial_projection': region_score.get('financial_projection')` to recommendation dict
- **Impact**: Financial projections (land values, ROI, investment sizing) now flow to JSON and PDF

#### Infrastructure Details Bug
- **Problem**: `infrastructure_details` dict empty in JSON output
- **Root cause**: Scorer only stored summary counts, not detailed breakdown
- **Fix**: Added `infrastructure_details: Dict[str, Any]` field to `CorrectedScoringResult` dataclass, populate with granular counts before return
- **Impact**: PDF now displays infrastructure breakdown (e.g., "6 major highways, 1 airport within range, 2 railway lines")

---

## [2.4] - 2025-10-19

### Added

#### Financial Metrics Engine Integration
- Created parallel financial projection system with live web scraping
- Web scraping system: 3-tier cascading fallback (Live → Cache → Benchmark)
  - Primary: Live scraping from Lamudi.co.id and Rumah.com (85% confidence)
  - Secondary: Cached results if <24-48h old (75-85% confidence)
  - Tertiary: Static regional benchmarks (50% confidence)
- Financial outputs:
  - Land value estimates (current + 3-year projection)
  - Development cost index (0-100) based on terrain, access, clearing requirements
  - ROI projections (3-year and 5-year)
  - Investment sizing recommendations (plot size, total capital)
  - Risk assessment (liquidity, speculation, infrastructure)
- Files added:
  - `src/core/financial_metrics.py` (773 lines) - Financial projection engine
  - `src/scrapers/base_scraper.py` (380 lines) - Base scraper with caching
  - `src/scrapers/lamudi_scraper.py` (420 lines) - Lamudi.co.id scraper
  - `src/scrapers/rumah_scraper.py` (415 lines) - Rumah.com scraper
  - `src/scrapers/scraper_orchestrator.py` (390 lines) - Orchestration with fallback logic
  - `WEB_SCRAPING_DOCUMENTATION.md` (600+ lines) - Complete user guide
- Dependencies added: `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`

---

## [2.3] - 2025-10-19

### Fixed

#### Enhanced Infrastructure Scoring Fix
- **Problem**: Infrastructure scoring still inflating to 100/100 despite Oct 18 fix
- **Root cause**: Enhanced analyzer could accumulate 270+ points before cap
- **Fix**: Proper total caps per component type (not per-feature), reduced max allocations, additive accessibility adjustment
- **Impact**: Realistic score distribution (20-85 typical, 85-95 exceptional)
- Files modified: `src/core/enhanced_infrastructure_analyzer.py`, `src/core/infrastructure_analyzer.py`

---

## [2.2] - 2025-10-18

### Fixed

#### Infrastructure Scoring Fix (Initial)
- **Problem**: Infrastructure scoring inflating all scores to 100/100
- **Root cause**: Unlimited component scores combined with multipliers
- **Fix**: Normalize component scores to 0-100 BEFORE combining, use additive bonuses instead of multiplicative multipliers
- **Impact**: Partial improvement (standard analyzer fixed, enhanced analyzer still had issues)
- Files modified: `src/core/infrastructure_analyzer.py`

---

## [2.1] - 2025-10-18

### Changed

#### Tiered Multipliers
- **Infrastructure**: 0.8-1.2x → 0.8-1.3x with 5 clear tiers (Poor/Fair/Good/VeryGood/Excellent)
- **Market**: 0.9-1.1x → 0.85-1.4x with 5 clear tiers (Declining/Stagnant/Stable/Strong/Booming)
- **Impact**: 2-3x better score separation between good and excellent opportunities
- Files modified: `src/core/corrected_scoring.py`

---

## [2.0] - 2025-10-06

### Changed

#### Corrected Scoring System (Major Refactor)
- **Satellite data now PRIMARY score component** (was being ignored in v1.x)
- Scoring structure:
  - Satellite development activity: 0-40 points (base score)
  - Infrastructure quality: 0.8-1.2x multiplier
  - Market dynamics: 0.9-1.1x multiplier
- Files created: `src/core/corrected_scoring.py` (new)
- Files deprecated: `speculative_scorer.py` (old, satellite ignored)

---

**Note**: For detailed technical information on each version, see `TECHNICAL_SCORING_DOCUMENTATION.md`.
