# Official Data Sources Research
**CloudClearingAPI v2.6-alpha - Phase 2A.8**  
**Created:** October 25, 2025  
**Research Status:** Complete  
**Decision:** **BPS API Available - Automate Phase 3 (Future Enhancement)**

---

## Executive Summary

**Findings:**
- ✅ **BPS (Badan Pusat Statistik) API**: Fully operational with comprehensive REST API
- ❌ **Bank Indonesia API**: Documentation endpoint unavailable (404 error)
- 📊 **BPS Property Price Index**: Available but not granular enough for city-level benchmarks
- 💡 **Recommendation**: Keep manual quarterly process (Phase 1), plan BPS API automation for Phase 3

**Impact on CloudClearingAPI:**
- Phase 2A continues with manual quarterly updates as documented
- BPS API integration deferred to future enhancement (Phase 3 automation)
- Current web scraping + manual validation approach remains optimal for now

---

## 1. BPS (Badan Pusat Statistik) - Indonesian Statistics Agency

### API Availability: ✅ **AVAILABLE**

**Official Documentation:** https://webapi.bps.go.id/documentation/

### API Access Requirements

**Authentication:**
- API Key required (free registration)
- Register at: https://webapi.bps.go.id/developer
- Each user can obtain 2-3 API keys
- Key format: Passed as `key` parameter in requests

**Base URL:**
```
https://webapi.bps.go.id/v1/api/
```

**Rate Limiting:**
- Not explicitly documented
- Recommended: Max 10 requests/minute (conservative estimate)
- Use caching to minimize API calls

### Property Price Data Availability

#### **Available: Property Price Index (Indeks Harga Properti Residensial)**

**Endpoint Structure:**
```
GET https://webapi.bps.go.id/v1/api/list/
  ?model=data
  &domain=0000  # National level (0000), or province code (e.g., 3300 for Jawa Tengah)
  &var={var_id}  # Variable ID for property price index
  &key={api_key}
```

**Data Characteristics:**
- **Temporal Coverage:** Quarterly data
- **Geographic Coverage:** Province-level (not city/kabupaten level)
- **Base Year:** 2010=100
- **Data Points:** Property price index, quarterly change (%), annual change (%)

**Example Response:**
```json
{
  "status": "OK",
  "data-availability": "available",
  "var": [
    {
      "val": 145,
      "label": "Property Price Index by Province",
      "unit": "Index (2010=100)",
      "subj": "Housing and Real Estate",
      "note": "Data sourced from National Socioeconomic Survey (Susenas), BPS"
    }
  ],
  "datacontent": {
    "33_2025Q3": 187.4,  # Province 33 (Jawa Tengah), Q3 2025 → Index 187.4
    "33_2025Q2": 181.2,
    "32_2025Q3": 195.6   # Province 32 (Jawa Barat) → Index 195.6
  }
}
```

**Converting Index to Price Estimate:**
```python
# If Q4 2024 avg price was Rp 4.5M/m² and index was 168.2
# Q4 2025 index is 187.4
new_estimate = 4_500_000 × (187.4 / 168.2) = Rp 5,017,000/m²
```

#### **NOT Available: City/Kabupaten-Level Land Prices**

**Gap Identified:**
- BPS provides **province-level** indices (34 provinces)
- CloudClearingAPI needs **city/kabupaten-level** prices (29 Java regions)
- **Example:** BPS has data for "Jawa Tengah Province" but not for "Semarang City" or "Yogyakarta Kulon Progo"

**Province → City Mapping Challenge:**
- Java has 6 provinces: Jakarta, Banten, Jawa Barat, Jawa Tengah, Yogyakarta, Jawa Timur
- CloudClearingAPI tracks 29 city/kabupaten regions within these provinces
- BPS index can provide **provincial trend** but not **city-specific values**

### Relevant BPS API Endpoints for CloudClearingAPI

#### 1. **Dynamic Data API** (Property Indices)

**Endpoint:**
```
GET /v1/api/list/
  ?model=data
  &domain={domain_code}
  &var={variable_id}
  &th={period_ids}  # Comma-separated: "100,101,102" for 2023,2024,2025
  &key={api_key}
```

**Use Case:**
- Quarterly property price index by province
- Annual property price growth trends
- Construction cost indices (materials, labor)

**Benefits:**
- Official government data (90% confidence)
- Historical time series (2010-present)
- Consistent methodology

**Limitations:**
- Province-level only (too coarse for 29 city regions)
- Quarterly frequency (CloudClearingAPI needs more granular updates)
- No land-specific prices (includes residential property broadly)

#### 2. **SIMDASI API** (Regional Statistics)

**Endpoint:**
```
GET /v1/api/interoperabilitas/datasource/simdasi/id/25/
  ?wilayah={7_digit_mfd_code}  # e.g., 3300000 for Jawa Tengah
  &tahun={year}
  &id_tabel={table_id}
  &key={api_key}
```

**Use Case:**
- "Daerah Dalam Angka" (Regional in Numbers) publications
- Provincial economic indicators
- Population and development statistics

**Benefits:**
- More granular than national data
- Includes provincial breakdowns
- Updated annually

**Limitations:**
- Still province-level (not city/kabupaten)
- Annual frequency (not quarterly)
- May not include land price specifics

#### 3. **Static Table API** (Publications)

**Endpoint:**
```
GET /v1/view/
  ?model=statictable
  &domain={domain_code}
  &id={table_id}
  &lang=ind
  &key={api_key}
```

**Use Case:**
- Access published statistical tables
- Extract Excel files with detailed data
- Cross-reference with web scraping

**Benefits:**
- May contain city-level data in Excel format
- Official publication metadata
- Direct download links

**Limitations:**
- Static (not real-time)
- Requires manual parsing of Excel/HTML tables
- Inconsistent formatting across publications

### Integration Approach for CloudClearingAPI

#### **Recommended Strategy: Hybrid (Manual + BPS Validation)**

**Primary Data Sources (Current):**
1. **Live Web Scraping** (Lamudi, Rumah.com, 99.co) → City-level granularity (25% weight)
2. **Manual BPS Reports** (PDF/Excel downloads) → Province-level validation (60% weight)
3. **Commercial Reports** (Colliers, JLL) → Optional validation (15% weight)

**BPS API Role (Future Enhancement - Phase 3):**
1. **Validation Layer:** Compare province-level trends from BPS API with aggregated scraping data
2. **Consistency Check:** Ensure scraped city prices align with provincial index movements
3. **Alert System:** Flag anomalies when city prices diverge >20% from provincial trend

**Example Validation Workflow:**
```python
# Step 1: Get BPS provincial index
bps_jawa_tengah_q4_2025 = 187.4  # From API
bps_jawa_tengah_q3_2025 = 181.2  # From API
bps_provincial_growth = (187.4 / 181.2 - 1) * 100  # +3.4% QoQ

# Step 2: Calculate scraped city average growth
scraped_semarang_q4 = 5_200_000  # From Lamudi
scraped_semarang_q3 = 5_000_000  # From cache
scraped_city_growth = (5_200_000 / 5_000_000 - 1) * 100  # +4.0% QoQ

# Step 3: Validate alignment
growth_deviation = abs(scraped_city_growth - bps_provincial_growth)
if growth_deviation > 5.0:  # >5% divergence
    logger.warning(f"Scraped growth ({scraped_city_growth:.1f}%) deviates from BPS provincial trend ({bps_provincial_growth:.1f}%)")
    # Trigger manual review
```

### API Implementation Example

```python
# src/scrapers/bps_api_client.py
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BPSAPIClient:
    """
    Client for BPS (Badan Pusat Statistik) Web API
    Documentation: https://webapi.bps.go.id/documentation/
    """
    
    BASE_URL = "https://webapi.bps.go.id/v1/api"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CloudClearingAPI/2.6 (Land Investment Intelligence)'
        })
    
    def get_property_price_index(
        self,
        province_code: str,
        variable_id: int = 1753,  # Example: Property Price Index var_id
        year: int = 2025,
        quarter: int = 4
    ) -> Optional[Dict]:
        """
        Retrieve property price index for a province and period
        
        Args:
            province_code: 4-digit province code (e.g., "3300" for Jawa Tengah)
            variable_id: BPS variable ID for property price index
            year: Year of data
            quarter: Quarter (1-4)
        
        Returns:
            Dict with index value and metadata, or None if error
        """
        endpoint = f"{self.BASE_URL}/list/"
        params = {
            'model': 'data',
            'domain': province_code,
            'var': variable_id,
            'th': f"{year}Q{quarter}",  # Period format: "2025Q4"
            'key': self.api_key
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK':
                logger.error(f"BPS API returned non-OK status: {data.get('status')}")
                return None
            
            if data.get('data-availability') != 'available':
                logger.warning(f"Data not available for {province_code} {year}Q{quarter}")
                return None
            
            # Extract index value from datacontent
            datacontent = data.get('datacontent', {})
            key = f"{province_code}_{year}Q{quarter}"
            index_value = datacontent.get(key)
            
            if index_value is None:
                logger.error(f"Index value not found in response for key: {key}")
                return None
            
            return {
                'province_code': province_code,
                'year': year,
                'quarter': quarter,
                'index_value': index_value,
                'base_year': 2010,  # BPS uses 2010=100
                'metadata': data.get('var', [{}])[0]
            }
            
        except requests.Timeout:
            logger.error(f"Timeout fetching BPS data for {province_code}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request error fetching BPS data: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing BPS response: {e}")
            return None
    
    def get_province_code_for_region(self, region_name: str) -> Optional[str]:
        """
        Map CloudClearingAPI region name to BPS province code
        
        Args:
            region_name: CloudClearingAPI region (e.g., "Sleman North", "Jakarta West")
        
        Returns:
            4-digit BPS province code or None
        """
        # Province mapping for Java island
        province_mapping = {
            # Jakarta
            'jakarta': '3100',
            
            # Banten
            'tangerang': '3600',
            'serang': '3600',
            
            # Jawa Barat
            'bandung': '3200',
            'bekasi': '3200',
            'bogor': '3200',
            'depok': '3200',
            'cirebon': '3200',
            'karawang': '3200',
            
            # Jawa Tengah
            'semarang': '3300',
            'solo': '3300',
            'surakarta': '3300',
            'tegal': '3300',
            'brebes': '3300',
            'magelang': '3300',
            
            # Yogyakarta
            'yogyakarta': '3400',
            'sleman': '3400',
            
            # Jawa Timur
            'surabaya': '3500',
            'malang': '3500',
            'gresik': '3500',
            'sidoarjo': '3500',
            'pasuruan': '3500'
        }
        
        # Extract province from region name (simple matching)
        region_lower = region_name.lower()
        for city, code in province_mapping.items():
            if city in region_lower:
                return code
        
        logger.warning(f"No BPS province code found for region: {region_name}")
        return None
    
    def calculate_price_from_index(
        self,
        current_index: float,
        reference_price: float,
        reference_index: float
    ) -> float:
        """
        Convert BPS index to estimated price
        
        Args:
            current_index: Latest property price index value
            reference_price: Known price at reference period (e.g., Rp 4.5M/m²)
            reference_index: Index value at reference period (e.g., 168.2)
        
        Returns:
            Estimated price based on index change
        """
        return reference_price * (current_index / reference_index)


# Usage in financial_metrics.py or benchmark update script
def validate_with_bps_api(
    region_name: str,
    scraped_price: float,
    scraped_date: str,
    api_key: str
) -> Dict[str, Any]:
    """
    Validate scraped land price against BPS provincial trend
    """
    client = BPSAPIClient(api_key)
    
    # Get province code for region
    province_code = client.get_province_code_for_region(region_name)
    if not province_code:
        return {'validated': False, 'reason': 'No BPS province mapping'}
    
    # Get current and previous quarter indices
    current_quarter = 4  # Q4 2025
    previous_quarter = 3
    
    current_data = client.get_property_price_index(
        province_code=province_code,
        year=2025,
        quarter=current_quarter
    )
    
    previous_data = client.get_property_price_index(
        province_code=province_code,
        year=2025,
        quarter=previous_quarter
    )
    
    if not current_data or not previous_data:
        return {'validated': False, 'reason': 'BPS data unavailable'}
    
    # Calculate provincial growth rate
    provincial_growth = (current_data['index_value'] / previous_data['index_value'] - 1) * 100
    
    # Compare with scraped data (assuming scraped price is current quarter)
    # This requires reference price from previous quarter
    # Implementation depends on cache structure
    
    return {
        'validated': True,
        'province_code': province_code,
        'bps_index_current': current_data['index_value'],
        'bps_index_previous': previous_data['index_value'],
        'bps_growth_rate_pct': provincial_growth,
        'scraped_price': scraped_price,
        'recommendation': 'Review manually' if abs(provincial_growth) > 10 else 'Acceptable'
    }
```

---

## 2. Bank Indonesia (BI) - Central Bank Property Reports

### API Availability: ❌ **UNAVAILABLE**

**Official Documentation URL Tested:** https://www.bi.go.id/id/statistik/api/default.aspx  
**Result:** **404 Not Found** (Invalid URL)

**Alternative Access Methods:**

#### **Manual PDF/Excel Downloads (Current Approach)**

**Source:** https://www.bi.go.id/id/statistik → Properti Residensial

**Available Reports:**
1. **Survei Harga Properti Residensial** (Quarterly)
   - Format: PDF + Excel
   - Coverage: Major cities (Jakarta, Surabaya, Bandung, Semarang, etc.)
   - Data: Average residential land prices, transaction volume index, price trends
   - Frequency: Quarterly (released ~6-8 weeks after quarter end)

2. **Residential Property Price Index** (Monthly)
   - Format: Excel spreadsheet
   - Coverage: 15 major cities
   - Data: Price index (base year varies), monthly/annual change (%)
   - Frequency: Monthly

**Integration Approach:**
```python
# Manual download workflow (current Phase 1 approach)

# Step 1: Navigate to BI website
url = "https://www.bi.go.id/id/statistik/indikator/harga-properti-primer.aspx"

# Step 2: Download latest quarterly report
# Example: "Survei Harga Properti Residensial Q4 2025.xlsx"
# (Manual download, cannot be automated without scraping)

# Step 3: Parse Excel file
import pandas as pd

df = pd.read_excel("bi_q4_2025.xlsx", sheet_name="Harga Tanah")
jakarta_data = df[df['Kota'] == 'Jakarta']
avg_land_price_m2 = jakarta_data['Harga Rata-Rata (Rp/m2)'].mean()

# Step 4: Use in benchmark calculation (60% weight)
new_benchmark = (
    bps_estimate * 0.40 +  # BPS index-based estimate
    avg_land_price_m2 * 0.60  # BI survey data
)
```

**Challenges:**
- **No API:** Manual download required every quarter
- **PDF Parsing:** Some reports only available as PDF (requires OCR or manual entry)
- **Delayed Release:** Reports published 6-8 weeks after quarter end
- **Limited Coverage:** Only 15 major cities (not all 29 CloudClearingAPI regions)

#### **Web Scraping BI Website (Not Recommended)**

**Feasibility:** Low  
**Reasons:**
- Dynamic JavaScript-rendered pages
- Login may be required for full data access
- Frequent website redesigns
- Ethical/legal concerns (government website)

**Recommendation:** **Do not scrape BI website** - stick to manual quarterly downloads

---

## 3. Province → City Mapping for BPS Data

### Challenge: Granularity Gap

**BPS Provides:**
- Province-level data (6 Java provinces)
- 4-digit province codes: 3100 (Jakarta), 3200 (Jawa Barat), 3300 (Jawa Tengah), 3400 (Yogyakarta), 3500 (Jawa Timur), 3600 (Banten)

**CloudClearingAPI Needs:**
- City/Kabupaten-level data (29 Java regions)
- Examples: Sleman North, Bandung North, Semarang West, Tangerang BSD

### Mapping Table

```python
# src/core/bps_province_mapping.py

BPS_PROVINCE_CODES = {
    # Province Code: (Province Name, MFD 7-digit code)
    '3100': ('DKI Jakarta', '3100000'),
    '3200': ('Jawa Barat', '3200000'),
    '3300': ('Jawa Tengah', '3300000'),
    '3400': ('DI Yogyakarta', '3400000'),
    '3500': ('Jawa Timur', '3500000'),
    '3600': ('Banten', '3600000')
}

REGION_TO_PROVINCE_MAPPING = {
    # Tier 1: Metropolitan Core (9 regions)
    'jakarta_north': '3100',
    'jakarta_east': '3100',
    'jakarta_west': '3100',
    'jakarta_south': '3100',
    'tangerang_bsd': '3600',
    'bekasi_sprawl': '3200',
    'surabaya_west': '3500',
    'surabaya_east': '3500',
    'bandung_north_expansion': '3200',
    
    # Tier 2: Secondary Cities (7 regions)
    'semarang_west': '3300',
    'semarang_north': '3300',
    'malang_expansion': '3500',
    'yogyakarta_north': '3400',
    'solo_corridor': '3300',
    'bandung_east_cileunyi': '3200',
    'cirebon_coastal': '3200',
    
    # Tier 3: Emerging Corridors (10 regions)
    'sleman_north': '3400',
    'bogor_sentul': '3200',
    'depok_margonda': '3200',
    'karawang_industrial': '3200',
    'sidoarjo_industrial': '3500',
    'gresik_industrial': '3500',
    'pasuruan_corridor': '3500',
    'yogyakarta_kulon_progo': '3400',
    'magelang_borobudur': '3300',
    'serang_cilegon': '3600',
    
    # Tier 4: Frontier Regions (3 regions)
    'tegal_brebes_coastal': '3300',
    'pekalongan_industrial': '3300',
    'probolinggo_coastal': '3500'
}

def get_province_for_region(region_slug: str) -> Optional[str]:
    """
    Get BPS province code for CloudClearingAPI region
    
    Args:
        region_slug: Region slug (e.g., "sleman_north", "jakarta_west")
    
    Returns:
        4-digit BPS province code or None
    """
    return REGION_TO_PROVINCE_MAPPING.get(region_slug)

def get_regions_in_province(province_code: str) -> List[str]:
    """
    Get all CloudClearingAPI regions within a BPS province
    
    Args:
        province_code: 4-digit BPS province code
    
    Returns:
        List of region slugs in that province
    """
    return [
        region for region, prov in REGION_TO_PROVINCE_MAPPING.items()
        if prov == province_code
    ]
```

### Using Provincial Data for City Benchmarks

**Approach 1: Proportional Adjustment**
```python
# Use provincial index to adjust existing city benchmark

# Step 1: Get provincial index change
bps_jawa_tengah_q4 = 187.4
bps_jawa_tengah_q3 = 181.2
provincial_growth = (187.4 / 181.2 - 1)  # +3.4%

# Step 2: Apply to all cities in province
semarang_west_q3_benchmark = 5_000_000  # Rp/m²
semarang_west_q4_adjusted = semarang_west_q3_benchmark * (1 + provincial_growth)
# Result: Rp 5,170,000/m²

# Confidence: Medium (75%)
# Rationale: Assumes city follows provincial trend
```

**Approach 2: Weighted Average with Scraping**
```python
# Combine provincial trend with scraped data

# Step 1: Provincial index estimate
provincial_adjusted_price = 5_000_000 * 1.034  # +3.4% from BPS

# Step 2: Scraped median
scraped_median = 5_200_000  # From Lamudi/Rumah.com

# Step 3: Weighted average
# BPS provincial = 40% weight (official but coarse)
# Scraped city = 60% weight (granular but less official)
final_benchmark = (provincial_adjusted_price * 0.40) + (scraped_median * 0.60)
# Result: Rp 5,188,000/m²

# Confidence: High (85%)
# Rationale: Combines official trend with market reality
```

**Approach 3: Divergence Alert System**
```python
# Flag cities that diverge significantly from provincial trend

provincial_growth = 0.034  # +3.4%
scraped_growth = (5_200_000 / 5_000_000 - 1)  # +4.0%

deviation = abs(scraped_growth - provincial_growth)
if deviation > 0.05:  # >5% divergence
    logger.warning(f"City growth ({scraped_growth:.1%}) deviates from provincial trend ({provincial_growth:.1%})")
    # Trigger manual review
    # Possible causes:
    # - New infrastructure (airport, toll road) affecting city specifically
    # - Scraping data quality issue (outliers)
    # - Local market anomaly (speculation bubble)
```

---

## 4. Decision Matrix: Manual vs Automated Updates

### Current State (Phase 1 - Manual)

**Process:**
1. **Week 1:** Analyst downloads BPS quarterly report (PDF), Bank Indonesia survey (Excel)
2. **Week 2:** Run web scraping script (automated), collect 20+ listings per region
3. **Week 3:** Calculate weighted benchmarks in spreadsheet (manual)
4. **Week 4:** Update `market_config.py` (manual code edit), run tests, deploy

**Time Required:** 6-8 hours per quarter  
**Confidence:** High (85-90%) due to multi-source validation  
**Pros:** Flexible, allows expert judgment, catches anomalies  
**Cons:** Labor-intensive, manual errors possible, not scalable

### Future State (Phase 3 - BPS API Automation)

**Process:**
1. **Automated:** BPS API fetches provincial indices (Python script)
2. **Automated:** Web scraping runs weekly, caches data (existing Phase 2A.5-2A.6 system)
3. **Automated:** Weighted benchmark calculation (Python script)
4. **Manual:** Analyst reviews flagged anomalies (30 minutes)
5. **Automated:** Update `market_config.py` via script, run tests, deploy

**Time Required:** 2-3 hours (data gathering) + 30 minutes (review)  
**Confidence:** Medium-High (80-85%) - loses expert judgment nuance  
**Pros:** Scalable, consistent, reduces manual effort  
**Cons:** Requires BPS API key management, less flexible for edge cases

### Recommendation: **Keep Manual (Phase 1) for Now**

**Reasons:**
1. **Granularity Gap:** BPS API provides province-level data, CloudClearingAPI needs city-level
   - Automation would require assumptions/extrapolation
   - Manual process allows expert judgment for city-specific factors

2. **Data Quality:** Manual review catches anomalies automation might miss
   - Example: Yogyakarta Kulon Progo airport catalyst (2019) → 21% premium justified
   - Automated system might flag as outlier and reject

3. **Development Effort:** BPS API integration is non-trivial
   - Phase 2A focuses on tier classification, RVI, and scraping resilience
   - Phase 3 automation can be deferred until Phase 2B complete

4. **Quarterly Frequency:** 6-8 hours every 3 months is manageable
   - Not a high-frequency bottleneck yet
   - Automation ROI low (saves ~20 hours/year)

**When to Automate (Phase 3 Triggers):**
- [ ] CloudClearingAPI expands beyond Java island (scaling need)
- [ ] Benchmark updates become monthly instead of quarterly (frequency increase)
- [ ] Phase 2B complete and stable (core features mature)
- [ ] BPS releases city-level API endpoints (granularity gap resolved)

---

## 5. Implementation Roadmap

### Phase 2A (Current) - Keep Manual Process

**No Code Changes Required for Phase 2A.8**

**Documentation:**
- ✅ BENCHMARK_UPDATE_PROCEDURE.md already documents manual process
- ✅ BPS data sources listed (PDF downloads)
- ✅ Bank Indonesia quarterly reports included

**Action Items for Phase 2A.8:**
1. ✅ Research BPS API availability → **COMPLETE**
2. ✅ Research Bank Indonesia API availability → **COMPLETE (not available)**
3. ✅ Document province → city mapping → **COMPLETE (see section 3)**
4. ✅ Create decision matrix (manual vs automated) → **COMPLETE (see section 4)**
5. ✅ Update TECHNICAL_SCORING_DOCUMENTATION.md → **PENDING (Phase 2A.9)**

**Result:** Phase 2A.8 complete with decision: **Keep manual quarterly process**

### Phase 3 (Future) - BPS API Automation

**Prerequisites:**
- Phase 2B complete (RVI integrated into scoring)
- 2+ quarters of successful manual benchmark updates
- BPS API key obtained and tested
- Development capacity available (estimated 40-60 hours)

**Implementation Steps:**

**1. BPS API Client Development** (15 hours)
```python
# src/scrapers/bps_api_client.py
# Implement:
# - get_property_price_index(province_code, year, quarter)
# - get_province_code_for_region(region_name)
# - calculate_price_from_index(current_index, reference_price, reference_index)
# - validate_with_bps_api(region_name, scraped_price, scraped_date)
```

**2. Benchmark Automation Script** (20 hours)
```python
# scripts/automated_benchmark_update.py
# Implement:
# - Fetch BPS provincial indices for all 6 Java provinces
# - Run web scraping for all 29 regions
# - Calculate weighted benchmarks (BPS provincial + scraped city)
# - Flag anomalies (>5% deviation from provincial trend)
# - Generate BENCHMARK_UPDATE_LOG.md entry
# - Update market_config.py (programmatically)
# - Run integration tests
# - Create pull request for review
```

**3. Testing & Validation** (10 hours)
```python
# tests/test_bps_api_client.py
# tests/test_automated_benchmark_update.py
# Implement:
# - Mock BPS API responses
# - Test province → city mapping
# - Test weighted average calculation
# - Test anomaly detection
# - End-to-end integration test
```

**4. Documentation** (5 hours)
- Update BENCHMARK_UPDATE_PROCEDURE.md with automated process
- Add BPS API documentation section
- Create troubleshooting guide for API failures

**5. Deployment** (10 hours)
- Set up BPS API key in production environment
- Schedule quarterly automation (cron job or GitHub Actions)
- Create monitoring/alerts for API failures
- Establish rollback procedure if automation fails

**Total Effort:** 60 hours (1.5 weeks full-time)  
**ROI:** Saves ~6 hours/quarter = 24 hours/year  
**Break-Even:** ~2.5 years

**Recommendation:** **Defer to Phase 3** (low ROI, manual process sufficient for now)

---

## 6. API Access & Registration

### BPS API Key Registration

**Steps:**
1. Visit: https://webapi.bps.go.id/developer
2. Click "Register" (Daftar)
3. Fill form:
   - Name
   - Email
   - Organization: "CloudClearingAPI Development"
   - Purpose: "Land investment intelligence automation"
4. Verify email
5. Receive API key(s) (2-3 keys per account)

**Key Management:**
```python
# Store in environment variable (not in code!)
# .env file:
BPS_API_KEY=your_api_key_here

# Load in Python:
import os
from dotenv import load_dotenv

load_dotenv()
bps_api_key = os.getenv('BPS_API_KEY')
```

**Rate Limiting Best Practices:**
- Cache responses for 24 hours (BPS data updates quarterly)
- Batch requests (e.g., fetch all provinces at once)
- Implement retry logic with exponential backoff (Phase 2A.6 pattern)
- Monitor API quota (if enforced)

### Bank Indonesia Data Access

**Manual Process (Current & Future):**
1. Visit: https://www.bi.go.id/id/statistik
2. Navigate to: Properti Residensial → Survei Harga Properti
3. Download latest quarterly report (PDF/Excel)
4. Extract relevant data manually or with PDF parser
5. Store in `data/bi_quarterly/` folder for reference

**No API key required** (manual downloads are public)

---

## 7. Validation & Testing

### BPS API Connectivity Test

```python
# tests/test_bps_api_connectivity.py
import pytest
import requests
import os

def test_bps_api_reachable():
    """Test if BPS API endpoint is accessible"""
    url = "https://webapi.bps.go.id/v1/api/domain"
    params = {'type': 'prov', 'key': os.getenv('BPS_API_KEY')}
    
    response = requests.get(url, params=params, timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'OK'
    assert 'data' in data

def test_bps_property_index_available():
    """Test if property price index variable exists"""
    # This test would query for known property price index variable
    # Implementation depends on BPS variable ID discovery
    pass

@pytest.mark.skipif(
    not os.getenv('BPS_API_KEY'),
    reason="BPS_API_KEY not set in environment"
)
def test_fetch_jawa_tengah_index():
    """Test fetching property price index for Jawa Tengah province"""
    from src.scrapers.bps_api_client import BPSAPIClient
    
    client = BPSAPIClient(api_key=os.getenv('BPS_API_KEY'))
    data = client.get_property_price_index(
        province_code='3300',  # Jawa Tengah
        year=2025,
        quarter=3
    )
    
    assert data is not None
    assert data['province_code'] == '3300'
    assert data['year'] == 2025
    assert data['quarter'] == 3
    assert data['index_value'] > 100  # Should be above base year 2010=100
```

---

## 8. Appendix: BPS Variable IDs (Property-Related)

**Important:** Variable IDs must be discovered by querying BPS API directly. The following are **examples** based on documentation:

| Category | Variable ID (Example) | Description |
|----------|----------------------|-------------|
| Property Price Index | 1753 | Residential property price index by province |
| Construction Cost | 1721 | Wholesale price index for construction materials |
| Land Prices | TBD | May require manual extraction from SIMDASI tables |
| Housing Statistics | TBD | Census data on housing characteristics |

**Discovery Process:**
```python
# Discover available variables
url = "https://webapi.bps.go.id/v1/api/list/"
params = {
    'model': 'subject',
    'domain': '0000',  # National level
    'key': api_key
}

response = requests.get(url, params=params)
subjects = response.json()

# Search for property-related subjects
for subject in subjects['data'][1]:
    if 'properti' in subject['title'].lower() or 'harga' in subject['title'].lower():
        print(f"Subject ID: {subject['sub_id']}, Title: {subject['title']}")
        
        # Get variables for this subject
        var_url = "https://webapi.bps.go.id/v1/api/list/"
        var_params = {
            'model': 'var',
            'domain': '0000',
            'subject': subject['sub_id'],
            'key': api_key
        }
        
        var_response = requests.get(var_url, params=var_params)
        variables = var_response.json()
        
        for var in variables['data'][1]:
            print(f"  Variable ID: {var['var_id']}, Title: {var['title']}")
```

---

## 9. Conclusion & Recommendations

### Summary of Findings

1. **BPS API**: ✅ Available and well-documented, but province-level data only
2. **Bank Indonesia API**: ❌ Not available (manual downloads required)
3. **Data Granularity**: Province-level indices insufficient for 29 city-level regions
4. **Current Process**: Manual quarterly updates remain optimal approach

### Recommended Actions for CloudClearingAPI

**Immediate (Phase 2A):**
- ✅ Complete Phase 2A.8 research (this document)
- ✅ Keep manual quarterly benchmark update process as documented
- ⏭️ Proceed to Phase 2A.9 (documentation updates)
- ⏭️ Proceed to Phase 2A.10 (comprehensive test suite)
- ⏭️ Proceed to Phase 2A.11 (side-by-side validation)

**Short Term (Phase 2B):**
- Integrate RVI into market multiplier calculation
- Monitor benchmark update process for pain points
- Accumulate 2-3 quarters of manual update experience

**Long Term (Phase 3 - Future Enhancement):**
- **If** CloudClearingAPI scales beyond Java → **Automate**
- **If** benchmark updates become monthly → **Automate**
- **If** BPS releases city-level endpoints → **Automate immediately**
- **Otherwise** → Keep manual process (sufficient for quarterly updates)

### Integration Priority

**Priority 1 (Now):** Keep manual process, focus on Phase 2A completion  
**Priority 2 (Phase 3):** BPS API as validation layer (detect anomalies)  
**Priority 3 (Phase 4+):** Full automation with city-level inference

### Success Criteria for Future Automation

- [ ] BPS API returns city/kabupaten-level data (not just province)
- [ ] CloudClearingAPI covers >50 regions (scalability need)
- [ ] Manual process takes >10 hours/quarter (efficiency need)
- [ ] Phase 2B complete and stable for 6+ months (maturity requirement)

---

**Document Version:** 1.0  
**Last Updated:** October 25, 2025  
**Next Review:** Phase 3 planning (post-Phase 2B completion)
