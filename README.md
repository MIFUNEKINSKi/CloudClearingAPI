# CloudClearingAPI: Land Development Investment Intelligence

**Version:** 2.17.0 (Trust + Friction Reduction — Weeks-at-Tier + Score Breakdown + Action Links)
**Status:** ✅ Production Ready | 65 Regions | Parallel Scoring (~4x faster) | GEE + OSM + Scraper Caching | Weekly Automated Reports with Email Delivery

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

## AWS infrastructure (Terraform) — portfolio / cost-conscious dev

Terraform defines **~70 resources** across **network, data lake, security, compute (ECS/ECR), monitoring, and Step Functions**. Nothing is required to stay running in AWS for you to **demonstrate DE skills** — the code in `infra/terraform/` is the artifact.

**Recommended for personal dev (lower monthly cost):**

- Set `enable_nat_gateway = false` in `terraform.tfvars` (see `infra/terraform/terraform.tfvars.example`). The stack then runs the weekly ECS task in **public subnets** with a **public IP** only while the task runs, avoiding NAT Gateway hourly charges (~\$32+/mo typical).
- When `enable_nat_gateway = true`, tasks use **private subnets** and `AssignPublicIp: DISABLED` (production-style), which requires NAT for outbound internet (GEE, scrapers, OSM).

**Docs:** [Cost-aware AWS deployment](docs/deployment/cost-aware-aws.md) · [Terraform guide](docs/deployment/terraform-guide.md) · [infra/terraform/README.md](infra/terraform/README.md)

**Local runs:** See [QUICKSTART.md](QUICKSTART.md) — no AWS spend.

---

## Changelog

### v2.17.0 (April 28, 2026) — Trust + Friction Reduction Release

Three coordinated additions to the weekly briefing, each addressing a distinct gap to the north-star ("see opportunities early and make money"):

**1. Weeks-at-tier tracking** (the "early" word in the goal):
```
🆕 NEW THIS WEEK at STRONG_BUY        (week 1 — fresh signal)
(2nd consecutive week at BUY)        (weeks 2-3)
📌 Held STRONG_BUY for 6 weeks       (4+ weeks — confirmed signal)
```
`_compute_weeks_at_tier` walks back through historical `weekly_monitoring_*.json` files (deduped by calendar date) and counts consecutive runs each region held its current tier.

**2. Score breakdown** (trust through visibility):
```
Score: 52.2/100 | Confidence: 100% | Market: booming
Breakdown: activity 32 × infra 1.15 × market 1.10 × conf 1.00 × news 1.05 × momentum 1.00 = 52.2
```
The investor sees every multiplier that produced the score, not just the final number.

**3. Action links** (friction reduction):
```
🔗 Listings: https://www.lamudi.co.id/tanah/jual/cikarang/?sort=newest
🛰️ Imagery:  https://www.google.com/maps/@-6.30000,107.15000,14z/data=!3m1!1e3
🗺️ OSM map:  https://www.openstreetmap.org/?bbox=107.0,-6.4,107.3,-6.2
```
Click-through due diligence — saves ~10 min of manual URL construction per recommendation × 8 STRONG_BUYs/run.

This closes the "trust + friction" gap I identified in the v2.16.12 audit. Track A is fully shipped (Phase 1+2+3 in v2.16.x); v2.17.0 makes the email more decisively actionable. Next valuable step is patience — let the backtest harness accumulate 4+ weeks of post-fix history.

### v2.16.12 (April 28, 2026) — Empirical Liquidity from Archived Listings (Phase 2 polish)

The static `liquidity_tier` field in `region_feasibility.py` was research-validated for 13 regions and tier-default-derived for the rest — but never sanity-checked against actual observed listing volumes. v2.16.12 adds that check using 8+ weeks of archived `listing_count` data per region.

**Components:**
- **`src/core/liquidity_estimator.py`** — `estimate_liquidity(region)` reads price-history JSONL, returns observed tier (very_low / low / moderate / cap_saturated). The scraper's `max_listings=20` cap means observations above ~15 hit a ceiling; below that, the count is real signal.
- **Asymmetric mismatch detection** — `liquidity_mismatch()` only fires when research overstates liquidity (research-rank > observed-rank by ≥2). Understatements are positive surprises, not warnings.
- **`tools/liquidity_audit.py`** — CLI for periodic review. `--thin` (avg < 10), `--mismatch` (research vs observed disagree).

**Findings on current data:**
- 5 mismatches: yogyakarta_urban_core, surabaya_east/west, cikarang_mega_industrial, gresik_port_industrial — all tier-1 metros where research expected `very_high` but Lamudi retail visibility is `moderate` (~10-13 listings/scrape). Institutional liquidity may be high but retail isn't.
- 5 genuinely thin markets: Jayapura (1.0/scrape), Ambon (4.7), Probolinggo (5.1), Yogyakarta urban core (7.8), Padang (8.8).

**Email integration:** each priority opportunity now shows a one-line liquidity-mismatch warning when research/observed disagree; YOUR PORTFOLIO section adds an "Observed liquidity" line per position.

### v2.16.11 (April 28, 2026) — Phase 3: Portfolio-Aware Action (Track A complete)

The weekly briefing now bridges "what's hot in the 65-region universe" with "what's missing from the investor's book". Three components:

**Position log** (`data/positions.jsonl`, manually maintained, gitignored as investor-private; schema in `docs/positions.jsonl.example`):
```json
{"region": "cikarang_mega_industrial", "size_m2": 500, "acquisition_date": "2025-12-01", "cost_per_m2": 2300000, "title_type": "HGB", "notes": "Lippo Cikarang plot"}
```

**`YOUR PORTFOLIO` section** at the top of the weekly email — only renders when positions exist:
- Cost basis + size + title type per position
- Current price + unrealized P&L (IDR, %, annualized)
- Feasibility line (✅⚠️🚫 + ownership pathway + zoning + liquidity)
- Per-position alerts: `EXIT_WATCH` (price decline >5% over 4 samples), `LIQUIDITY_RISK` (listing volume drop ≥50%), `TIER_DOWNGRADE` (picked up from tier_transitions)

**Correlation hints** in the priority-opportunities section: a STRONG_BUY in the same bucket as an existing holding gets a 📌 flag noting it adds correlation, not diversification.

**Track A complete**: Phase 1 (signal trustworthiness, v2.16.3-9) + Phase 2 (acquisition feasibility, v2.16.10) + Phase 3 (portfolio-aware action, this version) all shipped. Track B (AWS/dbt/CI-CD/observability) is now genuinely optional polish — the investment-alpha goal is fully addressed.

### v2.16.10 (April 28, 2026) — Phase 2: Acquisition Feasibility Layer

Indonesia's land system gates which regions are closeable. A STRONG_BUY in a region with Indigenous claims, military overlap, off-market trading, or contested zoning is wasted alert weight. This adds a per-region feasibility profile alongside the score.

**Three dimensions per region:**
1. **ownership_pathway** — `hgb_pt_pma` / `leasehold` / `hak_pakai` / `nominee_only` / `restricted` / `off_limits`
2. **zoning_class + overlays** — RTRW classification (industrial/tourism/residential/mixed) plus overlays (coastal_protection, indigenous_claim, psn_right_of_way, kspn_strict, sharia_qanun, hak_ulayat, etc.)
3. **liquidity_tier** — exit-speed proxy (very_high → very_low)

**Coverage**: 27 explicit profiles (13 deep-research-validated + 14 inferred from public regulatory data) + 38 tier-based defaults.

**Renders in email** as a one-line summary per STRONG_BUY/BUY entry, e.g.:
- `cikarang_mega_industrial`: ✅ HGB via PT PMA · industrial · very high liquidity
- `lake_toba_tourism_zone`: ⚠️ leasehold (25-30y) · tourism · shoreline_conservation, kspn_priority · very low liquidity
- `nusantara_capital_core`: 🚫 restricted access · mixed · indigenous_claim, contested_zoning, psn_right_of_way · very low liquidity

Soft annotation, not a hard filter — score is still shown so the investor sees signal AND friction together.

This is Phase 2 / Track A per the rewritten roadmap. Phase 3 (portfolio-aware action) is the natural follow-on.

### v2.16.9 (April 28, 2026) — Forecast Log + Backtest Harness (Phase 1 Mandatory Items Complete)

Adds two pieces of infrastructure that make "see opportunities early" measurable:

**`tools/backtest.py`** — admin tool reading historical `weekly_monitoring_*.json` runs + per-region price history. For each anchor run, reports per-tier mean price-change over 2/4/8-week windows + Spearman rank correlation between `investment_score` and realized delta. Methodology guards: frozen regions excluded; `listing_count` shift ≥2× flags suspect samples (scraper-coverage change vs real market move); pre-fix anchor banner prints when anchor pre-dates the last v2.16.x fix (2026-04-28).

Current backtest results: every available anchor pre-dates the last week of fixes (sar_only cap, outlier-resistant mean, 11 region-specific benchmarks, history-anchored clamp). The reported deltas are mostly scraper-fix artifacts (e.g., kulon_progo "dropped 81%" because we fixed its slug; semarang "dropped 41%" because v2.16.4 stripped misparsed listings). The numbers will become meaningful after 4+ weeks of stable post-2026-04-28 history. The harness is ready; the data isn't yet.

**`run_weekly_java_monitor.py`** — appends each run's BUY/STRONG_BUY/WATCH picks to `data/forecasts/forecast_log.jsonl` after scoring completes. Slim, schema-stable archive of "what we predicted at time T", immune to scoring-engine schema churn. Once 8+ weeks accumulate, becomes the canonical predictiveness oracle.

This closes the last mandatory Phase 1 item from the rewritten roadmap.

### v2.16.8 (April 28, 2026) — Per-Region History-Anchored Clamp (Phase 1 Close)

Closes the last mandatory item in the rewritten roadmap's Phase 1: when a region has ≥3 weeks of price-history samples (≥3 listings each), the region's own median-of-medians becomes the live clamp anchor instead of a static benchmark. Static benchmarks (region overrides from v2.16.7 + bucket fallback) become the floor; history must lie within 0.5–3× of static to be trusted.

Resolution chain (`_resolve_clamp_anchor`):
1. **Frozen regions** → no clamp (nusantara, labuan_bajo)
2. **History median** (≥3 samples, within 0.5–3× of static)
3. **Region-specific override** (research-validated, v2.16.7)
4. **Bucket benchmark**
5. unmapped → no clamp

The 0.5–3× sanity band is load-bearing — protects against history that's itself wrong. Examples: `banjarmasin_port_development` history Rp 17M (urban listings, 12.6× research Rp 1.35M, research wins); `bitung_port_industrial` history Rp 616K (SEZ-side dominated, 0.25× research Rp 2.5M, research wins); `lombok_mandalika_resort` history Rp 1.6M lower than research Rp 3.5M (0.46×, research wins).

Smoke-test across 18 known-tricky regions: 8 history-anchored (Jakarta/Cikarang/Anyer/Sidoarjo/Senggigi/Subang/Lake Toba — within reasonable bounds), 7 region-override, 2 bucket fallback, 2 frozen. 64 of 67 regions have ≥3 history samples available — near-universal eligibility for live calibration.

### v2.16.7 (April 28, 2026) — Benchmark Recalibration from Deep-Research Report

A 2026-04-28 deep-research report cross-checked Bank Indonesia SHPR Q3 2025, MAPPI/BPS, CBRE/Savills/Cushman institutional broker consensus, and 5 retail platforms across 13 target regions. Three concrete changes:

**Bucket benchmarks** (`scraper_orchestrator.regional_benchmarks`):
- medan: Rp 3.54M → **1.6M** (-54.8%) — was urban-Medan-Sunggal pricing routing wrong to Kuala Namu corridor. 3 institutional sources within ±15%.
- balikpapan: Rp 3.71M → **1.9M** (-48.7%) — research establishes Kariangau industrial Rp 1.65-2.1M.

**`_REGION_SPECIFIC_BENCHMARKS`** override map for regions where bucket routing was off by 2×+:
- `subang_patimban_megaport` → Rp 1.5M (was 5.85M); `cikarang_mega_industrial` → Rp 2.8M (was 8.56M); `karawang_industrial_corridor` → Rp 2.6M; `serang_cilegon_industrial` / `merak_port_corridor` → Rp 4.9M; `anyer_carita_coastal` → Rp 1.0M; `medan_kuala_namu_corridor` → Rp 1.6M; `bitung_port_industrial` → Rp 2.5M; `banjarmasin_port_development` → Rp 1.35M; `lombok_mandalika_resort` → Rp 3.5M; `lombok_senggigi_coast` → Rp 2.0M; `batang_industrial_sez` → Rp 1.2M.

**`_FROZEN_BENCHMARK_REGIONS`** — bypass clamp entirely (retail-platform data fundamentally unreliable per research):
- `nusantara_capital_core` / `nusantara_balikpapan_corridor` — IKN platform aggregates show 40× source disagreement and systemic per-meter calculation errors. Manual underwriter review only.
- `labuan_bajo_komodo_gateway` — KSPN-tier land trades off-market between hospitality conglomerates; single-data-point retail visibility.

Smoke-test against actual Apr 27 run extracts: Cikarang Rp 2.5M extracted → now PASS (was clamped to 8.56M); Serang/Cilegon Rp 4.5M extracted → now PASS (was clamped to 4.0M); Bitung Rp 616K extracted → now PASS (SEZ-side accepted). This is Track A / Phase 1 work per the rewritten roadmap.

### v2.16.6 (April 25, 2026) — News Dedup + Medan Corridor Slug Override

**News article dedup via title-bigram overlap.** Apr 27 run pulled 9 articles for `bekasi_industrial_belt` all about the same train accident (different paraphrasings). Pure Jaccard on tokens was too strict (13–23% overlap). Bigrams catch named-entity + event combos like "tabrakan kereta" or "bekasi timur" that reliably co-occur across paraphrases. Threshold ≥2 shared bigrams: drops 4 of 9 Bekasi rail articles, keeps separate LRT/MRT/Tol stories correctly distinct. Dedup runs after relevance-sort so the highest-scoring framing wins.

**Medan Kuala Namu corridor → 'deli-serdang' Lamudi slug.** The `medan` city slug returned urban-Medan premium listings (median Rp 18.5M/m² = 5.22× benchmark, triggering the 5× outlier clamp every run). `deli-serdang` regency contains Kuala Namu airport — listings reflect peripheral airport-corridor land: median Rp 9.9M/m² = 2.81× benchmark (within clamp threshold, will keep live data). A/B-tested 6 candidate regions; only Medan benefited (other cases documented in `REGION_SPECIFIC_SLUGS`).

**Cloud-cover handling — investigated, no code change.** The CRITICAL drift alerts on `lake_toba`/`lombok_mandalika`/`bitung` were PRICE-history drift artifacts (history held pre-clamp Rp 2.18B/m² values; current runs use post-clamp Rp 1.2M median → -99.9% drift). v2.16.4 fixes the source; alerts will self-clear over 4–8 weekly runs. Real cloud-cover regions correctly fell to SAR-only path with proper provenance flagging.

### v2.16.5 (April 25, 2026) — Lamudi Slug Refresh

`yogyakarta_kulon_progo_airport` had been hitting a Lamudi 404 every run (falling through to 99.co → benchmark fallback). Lamudi switched to hyphenated slugs: `kulonprogo` → `kulon-progo` and `gunungkidul` → `gunung-kidul`. Verified with smoke test — kulon-progo now extracts 10 listings at Rp 798K-892K/m². Probed all 31 known location_map slugs while in there; these were the only two stale ones.

### v2.16.4 (April 25, 2026) — Outlier-Resistant Price Mean + Brotli Bug Fix (Antara revival)

Two scraper-quality wins from the v2.16.3 audit cycle:

**Outlier-resistant Lamudi mean.** v2.16.3 audit found 22/65 regions hitting the orchestrator's 5×-benchmark outlier clamp. Root cause: 1–2 misparsed listings per scrape (e.g. Jakarta_north_sprawl extracted Rp 2.18 BILLION/m² for a few listings when the real price was Rp 9.7M/m²). The median was correct in every case — only the mean was polluted. Fix: median anchors the calculation; mean is computed only over listings ≤10× median. Sim against Jakarta data: old mean Rp 2.21B/m² (228× median, would clamp) → new mean Rp 9.71M/m² (1.00× median, no clamp). Many regions previously forced onto `_clamped` data_source (confidence 0.55) should now stay on live data (confidence 0.85).

**Brotli accept-encoding bug.** Both `base_scraper.py` and `news_scraper.py` advertised `Accept-Encoding: gzip, deflate, br` without having the `brotli` pip package installed. Sites preferring brotli (Antara was) returned bodies that `requests` couldn't decode, leaving raw brotli bytes that BeautifulSoup parsed as garbage HTML with 0 tags. **Antara had been silently returning 0 articles for at least two weeks.** Fix: drop `br` from accepted encodings. Verified: Antara now returns 25 articles per scrape (Bekasi rail, KAI, Menhub coverage flowing through).

### v2.16.3 (April 25, 2026) — sar_only Cap + Confidence Provenance Fix (Merak audit)

The v2.16.2 weekly run audit caught Merak (port_corridor) at score **61.7 / confidence 99%** despite `optical_changes==0` and 4.6M uncapped SAR pixels — two compounding bugs:

1. **`fuse_optical_and_sar` sar_only branch was uncapped.** Fusion mode already had a 20× SAR cap; sar_only mode (when optical returns zero) had none. Ports/coastal regions like Merak with 4–5M SAR pixels saturated the activity log-scale at ~38. Added `SAR_ONLY_MAX = 500_000` cap in sar_only mode (~comparable to post-cap fusion magnitude). Original count preserved in JSON for debugging.

2. **`satellite_data_source` provenance leak.** When fusion fell into sar_only mode, `region_data['data_source']` stayed `'optical'` (the optical detector ran successfully — it just found nothing). The SAR-only confidence cap (0.84 in `corrected_scoring.py:604`) keys off this string, so without the override these regions skipped the cap. Now resolves `effective_satellite_source` from `fusion_result['source']` and uses it for both scoring AND the `data_sources` JSON output.

**Net effect on Merak (recomputed against actual run data):** 61.7 → ~51.2. Still STRONG_BUY (>49) but the SAR-dominant warning is honestly visible and confidence capped at 0.84 — single-sensor data shouldn't claim 99%.

**Stat-calc timeout 60s → 120s.** 2/65 regions hit the 60s wall in the Apr 27 run; busy GEE periods can blow past 60s for vector aggregation.

### v2.16.2 (April 25, 2026) — Future-Work Batch (Drift Tests, News Supply, AWS Lifecycle, 99.co Revival)

**Drift tests:** 22 obsolete tier-only tests skipped with documented reason; suite is now clean (10 pass, 22 skip, 0 fail). The skipped tests still target the old tier-vs-tier benchmark model, which was replaced by per-region/tier fallback in v2.16.0.

**News supply expansion (4 → 5 sources):** Added Detik `finance.detik.com/berita-ekonomi-bisnis` (4 infra hits per probe, comparable density to /infrastruktur) and CNBC Indonesia (`cnbcindonesia.com/news` + `/market`). Raw articles per run: ~46 → ~79. Captures Yogya (Ratu Boko access), Aceh (Krueng Tingkeum bridge), and other secondary regions the prior 4-source pull missed.

**AWS Terraform — production-readiness pass:** `terraform validate` now passes cleanly. Fixed 5 deprecated S3 lifecycle rules missing required `filter{}` (raw, staging, curated, logs×2) — without the fix they become hard errors in a future AWS provider version. Recursive `terraform fmt` applied across all 6 modules.

**99.co revival via cloudscraper:** Replaces plain `requests` (always hit the CF JS challenge) with a `cloudscraper.create_scraper()` session. Verified working: `/jual/tanah/yogyakarta` returns HTTP 200 + 20-listing `__NEXT_DATA__`; smoke test extracted 10 yogya listings at Rp 8.4M/m² avg. Realistic ceiling: 0–1 regions per run before CF rate-limits the IP and the existing process-wide breaker trips. Added `cloudscraper>=1.2.71` to requirements.

### v2.16.1 (April 27, 2026) — SAR Fusion Cap + Threshold Recalibration + Tier Transitions

**SAR fusion bug + recalibration (the big one):**
- **SAR was 99% of the fused signal**, not the nominal 40%. SAR pixel counts run 100-1000× larger than optical (different per-pixel sensitivity, different counting units — pixels vs polygons), so the 60/40 weighting was meaningless. Capped SAR contribution at 20× optical when both available. Top scores dropped from 60+ to ~51 (the artificial amplification was real).
- **Thresholds recalibrated** for the honest scale: STRONG_BUY 58→49, BUY 50→42, WATCH 35→33. Restored the original "STRONG_BUY = top decile" intent. Apr 27 run: 5 STRONG_BUY / 12 BUY / 24 WATCH / 24 PASS.
- **SAR-dominant warning** in JSON + email when ratio > 20×: `⚠ Signal mostly SAR (radar 428× optical) — common at ports/coast where ship traffic + water surface change. Verify with satellite imagery before acting.`

**Tier transitions ("see opportunities early"):**
- New email section "📈 TIER CHANGES SINCE LAST RUN" surfaces upgrades / downgrades / new regions with score deltas. Sorted by destination tier (STRONG_BUY first), then score delta. The investor's stated north-star — catch a region the moment it crosses into BUY — is now front-and-center.

**OSM coverage metric correction:**
- Email body claimed "17/65 live infrastructure" — actually 65/65 (48 cache hits + 17 fresh queries, 0 fallbacks). The metric was excluding cached-OSM as if it were fallback. Fix: count any data_source containing 'osm' as live.

**Market-heat annualization noise cap:**
- `_calculate_price_trend` was multiplying short-history trends by up to 73× (5-day data) to "annualize". A 1% real trend became 73%/yr → "booming". Capped at 12.2× (= 365/30) so sub-30-day histories don't extrapolate noise.

**Low-listing-count confidence penalty:**
- Audit found 17/65 regions with Lamudi listing_count bouncing 5↔20 (pagination instability). New cascade: clamped → 0.55, listing_count <10 → 0.65, normal → 0.85.

**Detik infrastructure scraper added** — 4th source, real Indonesian-press infra news (Tol Yogyakarta-Bawen, KEK Batang, LRT Jakarta, Whoosh HSR).

### v2.16.0 (April 26, 2026) — Honest Math + STRONG_BUY Tier + Detik News + Confidence Caps

**Scoring (the math is now honest):**
- **Activity score: log scaling** — replaced step-function (cap 40 above 50K changes — saturated every region) with `5 + 5 × log10(changes)` clamped to [5, 40]. Top regions now spread 21–38 instead of all-tied at 40. STRONG_BUY tier no longer has 7 regions tied at the same score.
- **STRONG_BUY tier introduced** — score ≥58 with confidence ≥0.85; BUY ≥50 conf≥0.75; WATCH ≥35 conf≥0.50. Tighter than previous BUY≥40 (which caught 67% of regions). Now produces a 3-region elite shortlist + 15-region BUY pipeline.
- **Confidence caps now bite** — SAR-only regions cap at 0.84 (was masked by sensor-fusion +0.10 boost), market-clamped (avg >5× benchmark) caps at 0.80. Visible in PDF + email so the analyst sees the data-quality flag before acting.
- **Momentum math bug fixed** — `_ratio_to_multiplier(1.0)` was returning 0.85 instead of 1.0, depressing every score by 15% when momentum was steady. Switched to `1.0 + 0.20 × log2(ratio)` clamped to [0.85, 1.30]. Also tags `insufficient_baseline` so consumer drops momentum entirely until 8+ weeks of history exists (was firing fake "accelerating" for every region).
- **5Y vs 3Y ROI apples-to-oranges fixed** — email was rendering `land_only_roi_3yr` (no dev cost) for the 3Y number but `projected_roi_5yr` (with dev cost) for the 5Y. Added `land_only_roi_5yr` field; both horizons now show pure land appreciation.

**News pipeline activated:**
- **Detik infrastructure scraper added** — `finance.detik.com/infrastruktur` is the highest-density Indonesian-press source for named projects (Tol Yogyakarta-Bawen, KEK Batang, LRT Jakarta, Whoosh HSR). Government endpoints (PSN, Kemenperin) unreachable due to DNS/SSL issues.
- **City-direct matching** — accept articles mentioning any target city, not only generic infra keywords. Articles with no infra keyword stay sentiment=neutral so they count for `news_wow` WoW comparison without falsely boosting the catalyst multiplier.
- **Sentiment classifier loosened** — positive triggers on 1 high-relevance keyword OR 2+ any keywords (was strict ≥2). Multiple regions now get genuine 1.05x boost (Bandung, Jakarta, Yogyakarta, Batang).
- **News cache TTL: 7d → 2d** — was hitting same 12-article cache for 6 days at a time.
- **`_load_previous_news_counts` bug** — was checking `regions_analyzed` first (satellite-only entries with no news_catalyst), bailing if non-empty. Fixed: always read recommendation lists. `news_wow` now populates correctly.

**Drift monitoring fixed:**
- **Per-region benchmarks** — drift compares each region against its own ~4-week scraped median (was 5 coarse tier averages for 65 regions). Avg drift dropped from +94.5% to +19.1% (5× improvement).
- **Apples-to-apples comparison** — was using historical `median_price_m2` vs live `avg_price_m2` (current_price_per_m2 is the avg). Fixed: both use avg. Killed false positives like Tegal +291% where median was actually stable.
- **STRONG_BUY blind spot fixed** — drift_input was excluding `strong_buy_recommendations` (field didn't exist when that code shipped). Top-conviction regions now have drift tracking.

**Benchmark routing fixes:**
- **`_find_nearest_benchmark` substring bug** — `'bali' in 'balikpapan_port_industrial'` was True, routing every Kalimantan region to the Bali benchmark and silently inflating it. Switched to token-based matching on underscore-separated region names.
- **Banten + Denpasar buckets added** — Anyer/Cilegon/Serang/Merak no longer fall through to the yogyakarta default; Denpasar premium (Rp 15M/m²) preserved instead of being absorbed into the cheaper Bali bucket.
- **11 of 15 benchmarks refreshed** from real Lamudi medians.

**Reliability + log hygiene:**
- **Empty-composite + "no bands" warnings downgraded to DEBUG** — cloud-tier loop already retries with relaxed thresholds; per-attempt warnings were ~500/run noise.
- **OSM Overpass per-call + process-wide circuit breakers** — exit after 2 mirror failures, trip globally after 6 total.
- **99.co Cloudflare short-circuit** — single probe per run instead of 65 wasted retries (saves ~15 min/run).
- **GEE empty-composite root cause** — `find_best_dates` was relaxing cloud cover to 60% but `create_weekly_composite` re-filtered at hard-coded <30%. Threshold now passed through; progressive cloud-tier relaxation in `_analyze_region` rescues regions that would have gone SAR-only.

**Delivery:**
- **SMTP preflight at start of pipeline** — auth failures surface in 5s, not after 30 min.
- **Webhook (Slack) fallback** when email fails.
- **Subject prefixed `[LOW-CONF]`** when ≥20% benchmark fallback or ≥10% SAR-only.

### v2.14.0 (April 2026) — Parallel Scoring + News WoW + Caching + PDF Improvements

- **Parallel scoring with ThreadPoolExecutor** — scoring phase runs 4 regions concurrently; reduces total scoring time from ~50 min to ~15 min by overlapping OSM + scraper I/O across regions
- **News week-over-week rate of change** — compares article counts per region between current and previous run; feeds a 1.0-1.08x multiplier into momentum when news coverage is surging or increasing
- **GEE optical cache wired in** — `GEEImageCache` (14-day TTL) now integrated into `ChangeDetector.detect_weekly_changes`; subsequent runs skip expensive Google Earth Engine satellite analysis for cached regions
- **Lamudi province-level fallback** — when a city slug returns no listings, automatically retries with broader province slug (e.g., `toba-samosir` → `sumatera-utara`); improved slug mappings for Lombok, Lake Toba, Solo Raya
- **PDF decision matrix expanded** — added Market Heat and Data Quality columns; data quality shows ●● (both live), ●○ (partial), ○○ (fallback) at a glance
- **Email investment briefing upgraded** — now a full actionable briefing with portfolio overview, top 7 BUY details (entry price, ROI, RVI, momentum, news WoW, data source warnings), WATCH list with headroom, recommended next actions
- **Fixed corrupted PDF section header** encoding
- **Pre-scraped news** — news articles fetched once before parallel scoring loop (thread-safe)
- **Removed signal.alarm** — replaced process-global timeout with per-future timeout (thread-safe for parallel execution)

### v2.12.1 (April 2026) — Full 65-Region Run + Scoring & Market Fixes

- **First complete 65-region run** — all Java, Bali, Sumatra, Kalimantan, Sulawesi, Lombok/NTT, and Eastern Indonesia regions analyzed in a single `--all` pass
- **Infrastructure fallback database expanded to all 65 regions** — every monitored region now has a curated fallback score when OSM data is incomplete; sanity check rejects implausibly low OSM scores (< 60% of fallback) and substitutes the fallback automatically
- **Market heat differentiation fixed** — `historical_appreciation` benchmark values corrected from decimals to percentages (e.g., `0.15` -> `15.0`), producing accurate "Booming / Strong / Stable / Stagnant / Declining" classifications instead of uniform "stable"
- **Benchmark drift monitoring fixed** — drift monitor now receives scored regions (with financial projections) rather than raw satellite data, resolving the `'list' object has no attribute 'get'` error
- **Regional benchmark coverage expanded** — added price benchmarks for Medan, Palembang, Lampung, Batam, Makassar, Balikpapan, Nusantara/IKN, Lombok, and Denpasar with island-level nearest-benchmark fallback logic
- **Score clustering reduced** — improved infrastructure multiplier differentiation via the 65-region fallback database, giving each region a distinct infra multiplier rather than identical low-OSM defaults

### v2.12 (March 2026) — Decision Matrix + Expanded Coverage

- **Decision Matrix page in PDF** — all regions ranked in a single table with Score, BUY/WATCH/PASS action, Price/m², RVI valuation, Momentum trend, 3Y ROI, and Confidence
- **65 regions** (up from 51) — added Labuan Bajo (Komodo gateway), Nusa Dua/Bukit (Bali luxury), Senggigi (Lombok), Kupang (NTT), Karawang industrial corridor, Batang SEZ, Padang, Banda Aceh
- **Infrastructure fallback database updated** — all 31 Java regions now have correct fallback scores when OSM API fails
- **News scraper improvements** — added Kompas regional sections (Jawa Barat/Tengah/Timur), province-level article matching, fixed Antara relative URL handling

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

### Known Scoring Gaps (v2.12)

These are documented architectural limitations, not bugs. They work functionally but could be improved:

1. **Momentum applied post-hoc** — multiplied after `CorrectedInvestmentScorer.calculate_investment_score()` returns, rather than inside the scoring formula. Architecturally messy but produces correct results.

2. **Infrastructure construction projects detected but don't boost score** — OSM queries find construction sites, but the infrastructure multiplier only considers existing roads/airports/railways. A new highway under construction near a region should increase its score.

3. **No news sentiment trend over time** — news catalyst is snapshot-only (current week's articles). An investor would benefit from knowing "news coverage doubled this month" or "negative sentiment increasing."

4. **Infrastructure and news don't accumulate history** — market prices have JSONL archives and momentum uses historical JSONs, but infrastructure and news are snapshot-only. This is a gap worth noting but not critical for v1.

5. **News-driven discovery not implemented** — the system checks fixed regions. A smarter version could scan news for "new airport in X" and dynamically add that area to monitoring. The fixed-region approach works well as a foundation.

---

## 📊 System Output: The Investment Report

The primary output is a multi-page PDF report that provides a comprehensive overview of each region.

* **Page 1: Executive Summary** — Market status, key metrics, SAR/news data source coverage, scoring methodology
* **Page 2: Decision Matrix** — All regions ranked in a single table: Score, BUY/WATCH/PASS action, Price/m², RVI (Relative Value Index), Momentum trend, 3-Year ROI, Confidence. Color-coded for quick scanning.
* **Page 3: Top 5 Investment Opportunities** — Detailed breakdown of the highest-scoring BUY regions with price momentum, satellite changes, infrastructure quality, market heat, and data source transparency
* **Region Detail Pages:** Each region gets its own detailed analysis, including:
    1.  **Final Recommendation:** A clear **BUY**, **WATCH**, or **PASS** rating with score and confidence
    2.  **Financial Projection Summary:** ROI projections (3yr/5yr), land value estimates, development costs, bear/bull scenarios
    3.  **Satellite Imagery:** Before/after imagery, vegetation loss maps, construction hotspots
    4.  **Infrastructure Details:** Roads, airports, railways, ports with distance/quality scores
    5.  **News Catalyst:** Matched articles with clickable links, sentiment indicators, and keyword matches
    6.  **Momentum:** Recent vs baseline development velocity, acceleration/deceleration trend

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

1. **Python 3.10+** - [Download here](https://www.python.org/downloads/)
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

# 5. Run investment analysis (Java regions only, default)
python run_weekly_java_monitor.py

# Or run all 65 regions across Indonesia
python run_weekly_java_monitor.py --all --yes
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
│   │   ├── automated_monitor.py       # Orchestrates full 65-region pipeline
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
│   └── indonesia_expansion_regions.py # 65 monitored regions across Indonesia
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
├── run_weekly_java_monitor.py         # Main entry point — runs 31 Java (default) or all 65 regions (--all) + emails report
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

### Feature-Specific Documentation

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

**65 Regions Across Indonesia:**

| Island | Regions | Priority Focus |
|--------|---------|----------------|
| **Java** (31) | Jakarta Metro (6), Bandung (2), Central Java (8), East Java (8), Banten (3), Karawang, Batang SEZ, Bogor, Cirebon | Industrial corridors, urban expansion, SEZs |
| **Sumatra** (11) | Medan (2), Palembang (2), Lampung (2), Batam, Pekanbaru, Padang, Banda Aceh, Lake Toba | Ports, industrial, reconstruction |
| **Bali** (6) | Denpasar, Canggu-Seminyak, Sanur, Ubud, Tabanan, Nusa Dua/Bukit | Tourism, luxury development |
| **Lombok/NTT** (4) | Mataram, Mandalika, Senggigi, Labuan Bajo, Kupang | Tourism SEZs, gateway hubs |
| **Kalimantan** (6) | IKN Nusantara (2), Balikpapan, Samarinda, Banjarmasin, Pontianak | New capital, resource corridors |
| **Sulawesi** (4) | Makassar (2), Manado, Bitung | Port, tourism |
| **Papua/Maluku** (2) | Jayapura, Ambon | Urban, tourism |

**Total Monitored Area:** ~18,000 km²
**Analysis Frequency:** Weekly (Java primary), monthly (other islands)
**Average Processing Time:** ~45 seconds per region

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
