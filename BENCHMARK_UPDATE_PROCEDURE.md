# Benchmark Update Procedure
**CloudClearingAPI v2.6-alpha - Phase 2A.7**  
**Created:** October 25, 2025  
**Maintained By:** Investment Analysis Team  
**Update Frequency:** Quarterly (January, April, July, October)

---

## Purpose

This document establishes the process for maintaining accurate regional land price benchmarks used in the CloudClearingAPI financial projection system. Regular updates ensure RVI (Relative Value Index) calculations remain accurate and investment recommendations reflect current market conditions.

---

## Overview

### What Gets Updated

The benchmark update process maintains pricing data for **4 regional tiers** covering **29 Java regions**:

| Tier | Regions | Current Benchmark | Update Priority |
|------|---------|------------------|-----------------|
| **Tier 1 (Metros)** | 9 regions | Rp 8M/m² | High - every quarter |
| **Tier 2 (Secondary)** | 7 regions | Rp 5M/m² | High - every quarter |
| **Tier 3 (Emerging)** | 10 regions | Rp 3M/m² | Medium - every 6 months |
| **Tier 4 (Frontier)** | 3 regions | Rp 1.5M/m² | Low - annually |

### Data Sources Priority

1. **Official Government Data** (Primary - 60% weight)
   - BPS (Badan Pusat Statistik) property price indices
   - Bank Indonesia quarterly property reports
   - Confidence: High (90%)

2. **Live Web Scraping** (Secondary - 25% weight)
   - Lamudi.co.id, Rumah.com, 99.co
   - Average of 20+ listings per region
   - Confidence: Medium-High (85%)

3. **Commercial Reports** (Validation - 15% weight)
   - Colliers Indonesia Market Reports
   - JLL Property Pulse Indonesia
   - Confidence: High (90%) but expensive

4. **Manual Validation** (Quality Check)
   - Spot-check 5-10 listings per tier
   - Developer/agent consultation
   - Confidence: Variable

---

## Quarterly Update Process

### Timeline

**Quarter End → Update by 15th of following month**

- Q4 (Oct-Dec) → Update by January 15
- Q1 (Jan-Mar) → Update by April 15
- Q2 (Apr-Jun) → Update by July 15
- Q3 (Jul-Sep) → Update by October 15

### Step 1: Gather Official Data (Week 1)

#### 1A: BPS Property Price Index

**Source:** https://www.bps.go.id/ → Harga Properti Residensial

**Process:**
```bash
# Download quarterly property price reports
# Example: "Indeks Harga Properti Residensial Triwulan IV-2025"

# Key metrics to extract:
- Property Price Index (base year 2010=100)
- Quarterly change (%)
- Regional breakdowns for Java provinces
```

**Data Extraction:**
```python
# Example from BPS report
yogyakarta_q4_2025 = {
    'property_price_index': 187.4,  # 2010 base = 100
    'quarterly_change_pct': 2.8,
    'annual_change_pct': 11.2,
    'data_quality': 'official',
    'confidence': 0.90
}

# Convert index to price estimate
# If Q4 2024 avg price was Rp 4.5M/m²:
# New estimate = 4.5M × (187.4 / 168.2) = Rp 5.02M/m²
```

**Files to Update:**
- `src/core/market_config.py` - Update `avg_price_m2` in tier benchmarks
- Document source: "BPS Q4 2025 Property Index Report"

#### 1B: Bank Indonesia Property Reports

**Source:** https://www.bi.go.id/ → Statistik → Properti Residensial

**Process:**
```bash
# Download: "Survei Harga Properti Residensial"
# Quarterly report with regional price trends

# Key sections:
- Residential land prices by province
- Price growth rates (YoY and QoQ)
- Transaction volume trends
```

**Data Extraction:**
```python
# Example from BI report
jakarta_metro_q4_2025 = {
    'avg_residential_land_price_m2': 8_200_000,  # IDR
    'quarterly_change_pct': 3.2,
    'annual_change_pct': 14.8,
    'transaction_volume_index': 124,  # Increasing = high liquidity
    'data_quality': 'official',
    'confidence': 0.90
}
```

**Files to Update:**
- `src/core/market_config.py` - Validate against BPS data
- If >10% deviation from BPS: Flag for manual review

### Step 2: Run Live Web Scraping (Week 1-2)

#### 2A: Execute Scraping Campaign

**Command:**
```bash
# From project root
python scripts/update_regional_benchmarks.py --mode live_scraping

# This will:
# 1. Query Lamudi, Rumah.com, 99.co for all 29 regions
# 2. Collect 20+ listings per region
# 3. Calculate median prices per tier
# 4. Compare to current benchmarks
# 5. Flag significant deviations (>15%)
```

**Expected Output:**
```
Scraping Results Summary (Q4 2025)
=====================================

Tier 1 (Metros) - 9 regions scraped:
  Jakarta North: Rp 8,450,000/m² (current: Rp 8,000,000) +5.6% ⚠️
  Surabaya West: Rp 7,920,000/m² (current: Rp 8,000,000) -1.0% ✓
  ...

Tier 2 (Secondary) - 7 regions scraped:
  Bandung North: Rp 5,180,000/m² (current: Rp 5,000,000) +3.6% ✓
  ...

Flags for Review: 3 regions show >10% deviation
Recommended Action: Update Tier 1 benchmark to Rp 8,200,000/m²
```

#### 2B: Quality Check Scraped Data

**Validation Criteria:**
- Minimum 15 listings per region (reject if <10)
- Remove outliers (>2 standard deviations)
- Check listing dates (reject listings >90 days old)
- Verify location accuracy (listings must be within region bbox)

**Python Script:**
```python
# scripts/validate_scraped_prices.py
def validate_scraping_results(tier, regions):
    for region in regions:
        listings = load_cached_listings(region)
        
        # Quality checks
        if len(listings) < 15:
            print(f"⚠️ {region}: Only {len(listings)} listings (need 15+)")
        
        # Outlier detection
        prices = [l.price_per_m2 for l in listings]
        median = np.median(prices)
        std = np.std(prices)
        
        outliers = [p for p in prices if abs(p - median) > 2 * std]
        if len(outliers) > len(prices) * 0.2:
            print(f"⚠️ {region}: {len(outliers)} outliers (>20% of data)")
        
        # Calculate confidence
        confidence = calculate_confidence(
            listing_count=len(listings),
            std_dev=std / median,  # Coefficient of variation
            data_freshness_days=max([l.days_old for l in listings])
        )
        
        print(f"✓ {region}: Median Rp {median:,.0f}/m² (confidence: {confidence:.0%})")
```

### Step 3: Commercial Report Review (Week 2, Optional)

**Budget:** $500-1,000 per report (quarterly)

#### 3A: Colliers Indonesia Market Report

**Source:** Colliers.com → Research → Indonesia Property Market

**Key Sections:**
- Land price trends by region
- Transaction analysis (volume, velocity)
- Market outlook and forecasts

**Usage:**
- Validate Tier 1-2 regions (metros and secondary cities)
- Cross-check against BPS and scraped data
- Use forecasts to update `expected_growth` benchmarks

#### 3B: JLL Property Pulse Indonesia

**Source:** JLL.co.id → Research

**Key Sections:**
- Residential land market overview
- Supply and demand analysis
- Price appreciation trends

**Usage:**
- Validate liquidity ratings (high/moderate/low)
- Cross-check market_depth indicators
- Confirm infrastructure impact on pricing

### Step 4: Calculate Updated Benchmarks (Week 3)

#### 4A: Weighted Average Calculation

**Formula:**
```python
new_benchmark = (
    bps_estimate × 0.60 +          # Official data (primary)
    scraped_median × 0.25 +         # Live market data
    commercial_estimate × 0.15      # Professional reports (if available)
)

# Confidence calculation
confidence = min(
    bps_confidence × 0.60,
    scraping_confidence × 0.25,
    commercial_confidence × 0.15
)

# If no commercial report this quarter:
new_benchmark = (
    bps_estimate × 0.70 +           # Official data (higher weight)
    scraped_median × 0.30           # Live market data
)
```

#### 4B: Tier-Wide Adjustments

**Process:**
```python
# For each tier, calculate average adjustment across regions
tier_1_adjustment = calculate_average_change(tier_1_regions)
# Example: +4.2% average across 9 Tier 1 regions

# Apply to tier benchmark
old_tier_1_benchmark = 8_000_000
new_tier_1_benchmark = old_tier_1_benchmark × (1 + 0.042)
# Result: Rp 8,336,000/m² → Round to Rp 8,300,000/m²

# Update all Tier 1 regions
for region in tier_1_regions:
    update_region_benchmark(region, new_tier_1_benchmark)
```

#### 4C: Regional Overrides

**When to override tier benchmark:**
- **Region showing >15% deviation** from tier average → Investigate
- **Infrastructure catalyst** (new airport, toll road) → Premium justified
- **Known local factors** (land scarcity, zoning changes) → Adjust

**Example:**
```python
# Yogyakarta Kulon Progo (Tier 3) has new airport (opened 2019)
# Tier 3 benchmark: Rp 3,000,000/m²
# Scraped median: Rp 3,650,000/m² (+21.7%)

# Decision: Apply region-specific premium
yogyakarta_kulon_progo_benchmark = 3_650_000
rationale = "New international airport catalyst (2019), strong tourism growth"
confidence = 0.85  # High confidence due to known catalyst
```

### Step 5: Update Configuration Files (Week 3)

#### 5A: Update market_config.py

**File:** `src/core/market_config.py`

**Changes:**
```python
# OLD (Q3 2025):
REGIONAL_HIERARCHY = {
    'tier_1_metros': {
        'description': 'Metropolitan core - Jakarta + Surabaya metros',
        'benchmarks': {
            'avg_price_m2': 8_000_000,      # ← UPDATE THIS
            'expected_growth': 0.12,         # ← UPDATE IF CHANGED
            'liquidity': 'very_high',
            'market_depth': 'deep',
            'infrastructure_baseline': 75
        },
        # ...
    }
}

# NEW (Q4 2025):
REGIONAL_HIERARCHY = {
    'tier_1_metros': {
        'description': 'Metropolitan core - Jakarta + Surabaya metros',
        'benchmarks': {
            'avg_price_m2': 8_300_000,      # Updated from BPS +4.2% / BI +3.8%
            'expected_growth': 0.14,         # Revised up from 12% (strong momentum)
            'liquidity': 'very_high',
            'market_depth': 'deep',
            'infrastructure_baseline': 75
        },
        # ...
    }
}
```

#### 5B: Document Changes

**File:** `BENCHMARK_UPDATE_LOG.md` (create if doesn't exist)

**Format:**
```markdown
## Q4 2025 Update - January 15, 2026

### Summary
- **Tier 1 Benchmark:** Rp 8.0M → Rp 8.3M (+3.75%)
- **Tier 2 Benchmark:** Rp 5.0M → Rp 5.2M (+4.00%)
- **Tier 3 Benchmark:** Rp 3.0M → Rp 3.1M (+3.33%)
- **Tier 4 Benchmark:** Rp 1.5M → Rp 1.5M (no change)

### Data Sources
- BPS Q4 2025 Property Index: 187.4 (prev: 181.2, +3.4%)
- Bank Indonesia Q4 2025: Residential land +3.8% QoQ
- Web Scraping: 27/29 regions (Lamudi: 18, Rumah.com: 23, 99.co: 15)
- Colliers Q4 2025: "Sustained growth in Tier 1-2 markets"

### Regional Overrides
- **Yogyakarta Kulon Progo:** Rp 3.65M (Tier 3 benchmark: Rp 3.1M)
  - Rationale: New airport catalyst, +21% scraped median
  - Confidence: 85%

### Validation Results
- BPS vs Scraped Data: 94% correlation (excellent)
- Commercial Reports vs BPS: 97% alignment
- Outlier Regions: 2 flagged (under review)

### Next Review: April 15, 2026 (Q1 2026)
```

### Step 6: Testing & Validation (Week 4)

#### 6A: Run Integration Tests

**Command:**
```bash
# Test tier classification still works
python test_market_config.py

# Test RVI calculations with new benchmarks
python test_rvi_calculation.py

# Test financial projections
python test_tier_integration.py
```

**Expected Output:**
```
✅ All 29 regions classified correctly
✅ Tier benchmarks loaded successfully
✅ RVI calculations producing expected ranges
✅ Financial projections updated with Q4 2025 benchmarks
```

#### 6B: Spot-Check RVI Impact

**Before Update (Q3 2025):**
```python
# Yogyakarta Kulon Progo example
actual_price_m2 = 3_650_000
expected_price = 3_000_000 × 1.10 × 1.05 = 3_465_000
rvi = 3_650_000 / 3_465_000 = 1.053 (fairly valued)
```

**After Update (Q4 2025):**
```python
# With region-specific benchmark
actual_price_m2 = 3_650_000
expected_price = 3_650_000 × 1.10 × 1.05 = 4_214_250
rvi = 3_650_000 / 4_214_250 = 0.866 (moderately undervalued)
```

**Validation:**
- Ensure RVI changes are logical (new benchmarks should reduce false positives/negatives)
- Check that outlier regions now align better with market reality

#### 6C: Run Sample Monitoring

**Command:**
```bash
# Test with 3-5 representative regions
python run_weekly_java_monitor.py --regions 5 --test-mode

# Review PDF reports for:
# - Updated benchmark prices in financial section
# - RVI recalculations
# - Investment recommendations (should be more accurate)
```

### Step 7: Deployment (Week 4)

#### 7A: Commit Changes

```bash
git add src/core/market_config.py
git add BENCHMARK_UPDATE_LOG.md
git commit -m "chore: Q4 2025 benchmark update (Tier 1: +3.75%, Tier 2: +4.0%)"
git push origin main
```

#### 7B: Notify Stakeholders

**Email Template:**
```
Subject: CloudClearingAPI Q4 2025 Benchmark Update Complete

Team,

The quarterly benchmark update for CloudClearingAPI has been completed:

📊 Key Changes:
- Tier 1 (Metros): Rp 8.0M → Rp 8.3M (+3.75%)
- Tier 2 (Secondary): Rp 5.0M → Rp 5.2M (+4.00%)
- Tier 3 (Emerging): Rp 3.0M → Rp 3.1M (+3.33%)
- Tier 4 (Frontier): No change (annual review only)

📈 Data Sources:
- BPS Q4 2025 Property Index (+3.4% QoQ)
- Bank Indonesia Q4 2025 (+3.8% QoQ)
- Live web scraping (27/29 regions, 85% confidence avg)

✅ Validation:
- All integration tests passing
- 94% correlation between official and market data
- RVI calculations updated and validated

Next quarterly update: April 15, 2026

Details: BENCHMARK_UPDATE_LOG.md
Questions: [your-email]

Best,
[Your Name]
```

---

## Emergency Updates (Outside Quarterly Cycle)

### When to Trigger

Emergency benchmark updates should ONLY occur for:

1. **Major Infrastructure Completions**
   - New airport opening (e.g., Kulon Progo 2019)
   - Toll road completion connecting region to metro
   - Major port expansion announcement

2. **Economic Shocks**
   - >20% currency devaluation (IDR crash)
   - Government land policy changes (zoning, foreign ownership)
   - Natural disasters affecting region (earthquake, tsunami)

3. **Market Anomalies**
   - RVI showing >50% of regions "significantly overvalued" (system-wide issue)
   - Scraping detecting >30% price jump in single quarter (data quality issue?)
   - Multiple stakeholder reports of "wildly inaccurate" recommendations

### Emergency Process

**Faster timeline:** 1 week instead of 4

1. **Day 1-2:** Identify affected regions, gather emergency data
2. **Day 3-4:** Calculate adjusted benchmarks (focus on affected tier only)
3. **Day 5:** Update config, run tests
4. **Day 6-7:** Deploy with clear communication about emergency nature

**Documentation:**
```markdown
## EMERGENCY UPDATE - [Date]

**Trigger:** [Brief description of event]
**Affected Tier:** Tier X
**Regions Updated:** [List]
**Benchmark Change:** Rp X → Rp Y ([+/-]Z%)

**Rationale:** [1-2 paragraph explanation]
**Data Sources:** [Emergency sources used]
**Validation:** [Quick validation performed]

**Next Regular Update:** [Confirm still on quarterly schedule]
```

---

## Data Quality Standards

### Minimum Data Requirements

**Per Region:**
- BPS data: Available for 100% of provinces (may need city → province mapping)
- Web scraping: Minimum 10 listings (ideal: 20+)
- Listing freshness: <90 days old
- Geographic accuracy: >80% of listings within region bbox

**Per Tier:**
- Benchmark calculated from ≥70% of regions in tier
- Confidence level: ≥75% (medium-high)
- Variance: Standard deviation <20% of mean

### Confidence Scoring

```python
def calculate_benchmark_confidence(
    bps_available: bool,
    scraping_listing_count: int,
    commercial_report_available: bool,
    data_freshness_days: int
) -> float:
    """
    Calculate confidence score for a benchmark update
    
    Returns: 0.0-1.0 confidence score
    """
    confidence = 0.0
    
    # BPS data (0.60 max)
    if bps_available:
        confidence += 0.60
    
    # Web scraping (0.25 max)
    if scraping_listing_count >= 20:
        confidence += 0.25
    elif scraping_listing_count >= 15:
        confidence += 0.20
    elif scraping_listing_count >= 10:
        confidence += 0.15
    
    # Commercial report (0.15 max)
    if commercial_report_available:
        confidence += 0.15
    
    # Freshness penalty
    if data_freshness_days > 60:
        confidence *= 0.90  # -10% penalty for stale data
    elif data_freshness_days > 90:
        confidence *= 0.80  # -20% penalty for very stale data
    
    return min(1.0, confidence)
```

**Confidence Thresholds:**
- **≥0.85:** Excellent - use benchmark with high confidence
- **0.75-0.84:** Good - use benchmark, note moderate confidence
- **0.60-0.74:** Fair - use benchmark but flag for review
- **<0.60:** Poor - use previous quarter's benchmark, escalate

---

## Automation Opportunities

### Phase 1 (Manual - Current State)
- Analyst downloads BPS/BI reports (manual)
- Run scraping script (semi-automated)
- Calculate benchmarks in spreadsheet (manual)
- Update market_config.py (manual code edit)
- Run tests (automated)

**Time Required:** 6-8 hours per quarter

### Phase 2 (Scripted - Future Enhancement)
```bash
# Single command updates everything
python scripts/quarterly_benchmark_update.py \
  --bps-report data/bps_q4_2025.pdf \
  --bi-report data/bi_q4_2025.pdf \
  --run-scraping \
  --update-config \
  --run-tests
```

**Time Required:** 2-3 hours (data gathering) + 30 minutes (review/deploy)

### Phase 3 (Fully Automated - Future Vision)
- BPS/BI APIs integrated (if available)
- Automated scraping runs weekly
- Benchmark updates suggested automatically
- Human approves changes via web UI
- Auto-deployment to production

**Time Required:** 30 minutes review per quarter

---

## Troubleshooting

### Common Issues

**Issue 1: BPS Data Unavailable**
```
Problem: BPS hasn't published Q4 report by January 15
Solution: 
  1. Use Bank Indonesia data (70% weight) + scraping (30%)
  2. Flag benchmarks as "preliminary" in log
  3. Re-run update when BPS data available
  4. Typical delay: 2-4 weeks past quarter end
```

**Issue 2: Scraping Fails for Multiple Regions**
```
Problem: Lamudi/Rumah.com/99.co returning no results for 5+ regions
Solution:
  1. Check if sites changed HTML structure (update scrapers)
  2. Use cached data if <90 days old (reduce confidence)
  3. Fall back to tier-wide adjustment (use other regions in same tier)
  4. Escalate if affecting Tier 1-2 (critical regions)
```

**Issue 3: Large Deviations Between Data Sources**
```
Problem: BPS says +3%, scraping shows +15%, commercial reports say +5%
Solution:
  1. Investigate scraping data quality (outliers? wrong region?)
  2. Check BPS regional mapping (province vs city mismatch?)
  3. Use conservative estimate (weighted toward official data)
  4. Document uncertainty in log, flag for next quarter review
```

**Issue 4: Tests Fail After Update**
```
Problem: RVI tests failing, showing all regions "overvalued"
Solution:
  1. Check if benchmark update was too aggressive (>10% increase)
  2. Verify actual_price_m2 still being scraped correctly
  3. Recalculate expected_price with new benchmarks
  4. May need to adjust infrastructure/momentum premiums
```

---

## Contact & Escalation

**Quarterly Update Owner:** [Your Name/Team]  
**Email:** [your-email]  
**Slack:** #cloudclearingapi-updates  

**Escalation Path:**
1. Data quality issues → Data Engineering Team
2. Config file conflicts → DevOps Team
3. Market interpretation questions → Investment Analysis Team
4. Production deployment issues → Platform Team

**SLA:**
- Quarterly updates complete by 15th of month following quarter end
- Emergency updates deployed within 7 days of triggering event
- Documentation updates within 48 hours of deployment

---

## Appendix: Reference Data Sources

### Official Government Sources (Free)

**BPS (Badan Pusat Statistik):**
- Website: https://www.bps.go.id/
- Report: "Indeks Harga Properti Residensial" (Quarterly)
- Download: PDF + Excel formats available
- Coverage: Province-level data for all Indonesia

**Bank Indonesia:**
- Website: https://www.bi.go.id/
- Report: "Survei Harga Properti Residensial" (Quarterly)
- Download: PDF + interactive dashboard
- Coverage: Major cities + regional aggregates

### Commercial Sources (Paid)

**Colliers Indonesia:**
- Website: https://www.colliers.com/en-id/research
- Cost: ~$800/quarter for full market report
- Coverage: Tier 1-2 regions, institutional-grade data

**JLL Indonesia:**
- Website: https://www.jll.co.id/en/trends-and-insights/research
- Cost: ~$600/quarter for property pulse report
- Coverage: Jakarta, Surabaya, Bali focus

### Web Scraping Sources (Free)

**Lamudi.co.id:**
- Endpoint: `https://www.lamudi.co.id/tanah/buy/{location}/`
- Rate Limit: 2 requests/second
- Data Quality: High (professional listings)

**Rumah.com:**
- Endpoint: `https://www.rumah.com/properti/tanah/{location}`
- Rate Limit: 2 requests/second
- Data Quality: Medium-high (mix of agents + owners)

**99.co:**
- Endpoint: `https://www.99.co/id/jual/tanah/{province}`
- Rate Limit: 2 requests/second
- Data Quality: Medium (emerging platform)

---

**Document Version:** 1.0  
**Last Updated:** October 25, 2025  
**Next Review:** Q1 2026 (after first quarterly update cycle)
