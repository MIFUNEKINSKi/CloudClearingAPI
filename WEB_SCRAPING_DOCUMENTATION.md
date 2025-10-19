# Web Scraping System Documentation
**CloudClearingAPI - October 19, 2025**

## Overview

The web scraping system collects real-time land price data from Indonesian real estate portals with a sophisticated cascading fallback architecture:

**Priority 1:** Live scraping from Lamudi.co.id and Rumah.com  
**Priority 2:** Cached results (if < 24-48 hours old)  
**Priority 3:** Static regional benchmarks (last resort)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LandPriceOrchestrator                      │
│  Coordinates multiple scrapers with fallback logic          │
└─────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Lamudi    │  │  Rumah.com  │  │  Benchmark  │
│   Scraper   │  │   Scraper   │  │   Fallback  │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │
         ├───────────────┤
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cache Storage                            │
│  JSON files with 24-48h expiry (output/scraper_cache/)     │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Base Scraper (`base_scraper.py`)

**Purpose:** Provides common functionality for all scrapers

**Key Features:**
- ✅ **Cache-first architecture** - Always checks cache before scraping
- ✅ **User-agent rotation** - 5 different agents to avoid detection
- ✅ **Rate limiting** - 2 second minimum between requests
- ✅ **Request timeout** - 15 second timeout prevents hanging
- ✅ **Error handling** - Graceful degradation on failures

**Classes:**
- `ScrapedListing` - Single listing data structure
- `ScrapeResult` - Complete scrape operation result
- `BaseLandPriceScraper` - Abstract base class

**Example Usage:**
```python
from src.scrapers.base_scraper import BaseLandPriceScraper

# Subclass must implement:
# - _scrape_live(region_name, max_listings) -> ScrapeResult
# - get_source_name() -> str

class MyScraper(BaseLandPriceScraper):
    def get_source_name(self) -> str:
        return "my_site"
    
    def _scrape_live(self, region_name, max_listings):
        # Implement scraping logic
        pass
```

### 2. Lamudi Scraper (`lamudi_scraper.py`)

**Purpose:** Scrape land listings from Lamudi.co.id

**URL Structure:**
```
https://www.lamudi.co.id/tanah/buy/{location}/?sort=newest
```

**Parsing Strategy:**
- Uses flexible CSS selectors with regex patterns
- Handles Indonesian price formats (Miliar, Juta, Ribu)
- Extracts: price, size, location, listing date, URL
- Calculates price per m² automatically

**Price Parsing Examples:**
```
"Rp 1.500.000.000" → 1,500,000,000 IDR
"Rp 1,5 Miliar"    → 1,500,000,000 IDR
"Rp 500 Juta"      → 500,000,000 IDR
"1.5M"             → 1,500,000 IDR
```

**Size Parsing Examples:**
```
"1.000 m²"  → 1,000 m²
"500 m2"    → 500 m²
"1,5 ha"    → 15,000 m²
```

### 3. Rumah.com Scraper (`rumah_scraper.py`)

**Purpose:** Scrape land listings from Rumah.com

**URL Structure:**
```
https://www.rumah.com/properti/tanah/{location}?sort=terbaru
```

**Parsing Strategy:**
- Similar to Lamudi with site-specific selectors
- Handles "LT:" (Luas Tanah) prefixes
- Supports data attributes for size extraction
- Same Indonesian format handling

### 4. Scraper Orchestrator (`scraper_orchestrator.py`)

**Purpose:** Coordinate multiple scrapers with intelligent fallback

**Cascading Logic:**

```python
def get_land_price(region_name):
    # Phase 1: Live Scraping
    if live_scraping_enabled:
        result = lamudi.scrape(region_name)
        if result.success:
            return result
        
        result = rumah_com.scrape(region_name)
        if result.success:
            return result
    
    # Phase 2: Cache (even if expired)
    cache = check_cache(region_name)
    if cache:
        return cache
    
    # Phase 3: Static Benchmark
    return get_benchmark_fallback(region_name)
```

**Regional Benchmarks:**

| Region      | Price (IDR/m²) | Annual Appreciation | Liquidity |
|-------------|----------------|---------------------|-----------|
| Jakarta     | 8,500,000      | 15%                 | High      |
| Bali        | 12,000,000     | 20%                 | High      |
| Yogyakarta  | 4,500,000      | 12%                 | Moderate  |
| Surabaya    | 6,500,000      | 14%                 | High      |
| Bandung     | 5,000,000      | 13%                 | Moderate  |
| Semarang    | 3,500,000      | 11%                 | Moderate  |

## Integration with Financial Metrics

### Modified `_estimate_current_land_value()` Flow

**Before (Static Only):**
```python
def _estimate_current_land_value(region_name):
    benchmark = find_nearest_benchmark(region_name)
    base_value = benchmark['current_avg']
    return base_value * adjustments
```

**After (Live → Cache → Static):**
```python
def _estimate_current_land_value(region_name):
    # Try live scraping / cache
    if orchestrator:
        price_data = orchestrator.get_land_price(region_name)
        if price_data['success']:
            base_value = price_data['average_price_per_m2']
            source = price_data['data_source']  # 'lamudi', 'rumah_com', etc.
            return base_value * adjustments
    
    # Fallback to static
    benchmark = find_nearest_benchmark(region_name)
    base_value = benchmark['current_avg']
    return base_value * adjustments
```

## Configuration

### `config.yaml` Settings

```yaml
web_scraping:
  enabled: true                 # Enable/disable live scraping
  cache_expiry_hours: 24        # Cache validity (24-48h recommended)
  max_listings_per_site: 20     # Limit per scrape
  request_timeout: 15           # Request timeout (seconds)
  rate_limit_seconds: 2         # Min delay between requests
  
  sites:
    lamudi:
      enabled: true
      base_url: "https://www.lamudi.co.id"
    rumah_com:
      enabled: true
      base_url: "https://www.rumah.com"
```

### Environment Variables

None required - scrapers work without authentication.

## Usage Examples

### Basic Usage

```python
from src.scrapers.scraper_orchestrator import LandPriceOrchestrator

# Initialize orchestrator
orchestrator = LandPriceOrchestrator(
    cache_expiry_hours=24,
    enable_live_scraping=True
)

# Get land price data
result = orchestrator.get_land_price("Sleman Yogyakarta", max_listings=20)

print(f"Average: Rp {result['average_price_per_m2']:,.0f}/m²")
print(f"Source: {result['data_source']}")  # 'lamudi', 'rumah_com_cached', 'static_benchmark'
print(f"Listings: {result['listing_count']}")
```

### Financial Metrics Integration

```python
from src.core.financial_metrics import FinancialMetricsEngine

# Initialize with web scraping enabled
engine = FinancialMetricsEngine(
    enable_web_scraping=True,
    cache_expiry_hours=24
)

# Calculate projection (will use live prices if available)
projection = engine.calculate_financial_projection(
    region_name="Sleman North",
    satellite_data=satellite_data,
    infrastructure_data=infrastructure_data,
    market_data=market_data,
    scoring_result=scoring_result
)

# Data sources used are listed in projection
print(projection.data_sources)
# Example: ['satellite_sentinel2', 'lamudi', 'openstreetmap']
```

### Cache Management

```python
# Check cache status
from pathlib import Path
cache_dir = Path("output/scraper_cache")
cache_files = list(cache_dir.glob("*.json"))
print(f"Cached regions: {len(cache_files)}")

# Clear cache for specific region
orchestrator.lamudi.clear_cache("Sleman Yogyakarta")

# Clear all cache
orchestrator.lamudi.clear_cache()
orchestrator.rumah_com.clear_cache()
```

## Cache Structure

**Location:** `output/scraper_cache/`

**File Format:** `{source}_{region}.json`

**Example:** `lamudi_sleman_yogyakarta.json`

**Content Structure:**
```json
{
  "region_name": "Sleman Yogyakarta",
  "average_price_per_m2": 5250000,
  "median_price_per_m2": 4800000,
  "listing_count": 15,
  "listings": [
    {
      "price_per_m2": 5500000,
      "total_price": 825000000,
      "size_m2": 150,
      "location": "Sleman, Yogyakarta",
      "listing_date": "2 hari lalu",
      "source_url": "https://www.lamudi.co.id/...",
      "listing_type": "land"
    }
  ],
  "source": "lamudi",
  "scraped_at": "2025-10-19T14:30:00",
  "success": true,
  "error_message": null
}
```

## Error Handling

### Common Issues & Solutions

**1. No listings found**
```
Symptom: listing_count = 0, data_source = 'static_benchmark'
Cause: Site layout changed or region name doesn't match
Solution: System automatically falls back to benchmark
```

**2. Rate limiting / IP blocking**
```
Symptom: Request timeouts or HTTP 429 errors
Cause: Too many requests
Solution: 
  - Increase rate_limit_seconds in config
  - Use cache (already scraped data)
  - Wait 15-30 minutes before retrying
```

**3. Parsing failures**
```
Symptom: Listings found but price_per_m2 = 0
Cause: Site HTML structure changed
Solution:
  - Check logs for parsing errors
  - Update CSS selectors in scraper
  - Falls back to next source automatically
```

**4. Cache stale**
```
Symptom: data_source contains '_cached', cache_age_hours > 48
Cause: Live scraping failed, using old cache
Solution:
  - Normal operation during fallback
  - Will retry live scraping on next request
  - Consider clearing cache to force benchmark use
```

## Testing

### Run Test Suite

```bash
python3 test_web_scraping.py
```

**Test Coverage:**
1. ✅ Orchestrator cascading logic
2. ✅ Cache persistence and expiry
3. ✅ Fallback to static benchmark
4. ✅ Financial metrics integration
5. ✅ Error handling resilience

### Expected Output

```
TEST 1: Scraper Orchestrator
✓ Success: True
✓ Data Source: lamudi
✓ Average Price: Rp 4,750,000/m²
✓ Listings: 12

TEST 2: Cache Persistence
✓ Data Source: lamudi
✓ Cache is working!
✓ Cache Age: 0.02 hours

TEST 3: Fallback to Benchmark
✓ Data Source: static_benchmark
✓ Fallback working correctly!
```

## Performance Characteristics

| Operation              | Time    | Notes                           |
|------------------------|---------|----------------------------------|
| Live scraping          | 5-15s   | Depends on site response time    |
| Cache retrieval        | <0.1s   | Instant from disk                |
| Benchmark fallback     | <0.01s  | In-memory lookup                 |
| Full orchestration     | 5-15s   | First request (with scraping)    |
| Subsequent requests    | <0.1s   | Uses cache                       |

## Data Quality

### Confidence Levels

| Data Source           | Confidence | Notes                              |
|-----------------------|------------|------------------------------------|
| Live scraping         | 85%        | Real listings, current prices      |
| Cached (< 24h)        | 85%        | Recent real data                   |
| Cached (24-48h)       | 75%        | Slightly stale                     |
| Static benchmark      | 50%        | Historical averages only           |

### Listing Validation

Scrapers automatically filter out invalid listings:
- ✅ Price > 0
- ✅ Size > 0  
- ✅ Price per m² within reasonable range (100k - 100M IDR)
- ✅ Complete location information

## Maintenance

### Adding New Scraper

1. Create new scraper class inheriting from `BaseLandPriceScraper`
2. Implement `_scrape_live()` and `get_source_name()`
3. Add to orchestrator in `__init__()` method
4. Update orchestrator's cascading logic
5. Add site config to `config.yaml`

**Example:**
```python
# src/scrapers/newsite_scraper.py
from .base_scraper import BaseLandPriceScraper, ScrapeResult

class NewSiteScraper(BaseLandPriceScraper):
    def get_source_name(self) -> str:
        return "newsite"
    
    def _scrape_live(self, region_name, max_listings):
        # Implementation
        pass
```

### Updating Selectors

If site layout changes, update CSS selectors in respective scraper:

```python
# Old selector
listing_cards = soup.find_all('div', class_='listing-card')

# Update to new selector
listing_cards = soup.find_all('article', class_='property-item')
```

## Troubleshooting

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Debug output shows:
- URLs requested
- Listings found per page
- Parsing successes/failures
- Cache hits/misses
- Fallback triggers

### Check Cache Files

```bash
# View cache directory
ls -lh output/scraper_cache/

# View cache content
cat output/scraper_cache/lamudi_sleman_yogyakarta.json | jq
```

### Test Individual Scrapers

```bash
# Test Lamudi scraper
python3 src/scrapers/lamudi_scraper.py

# Test Rumah.com scraper
python3 src/scrapers/rumah_scraper.py

# Test orchestrator
python3 src/scrapers/scraper_orchestrator.py
```

## Future Enhancements

### Planned Features
- [ ] Proxy rotation for higher request volumes
- [ ] JavaScript rendering for dynamic sites (Selenium/Playwright)
- [ ] Historical price tracking database
- [ ] Price trend analysis from cached data
- [ ] Multi-city batch scraping
- [ ] Automated selector updates via ML

### Integration Opportunities
- [ ] DEM terrain data for development cost accuracy
- [ ] Government land registry data (BPN)
- [ ] Zoning and land use regulations
- [ ] Infrastructure development plans

## Dependencies

```bash
pip install requests beautifulsoup4 lxml
```

- **requests** - HTTP client
- **beautifulsoup4** - HTML parsing
- **lxml** - Fast XML/HTML parser

## License & Legal

**Important:** Web scraping must comply with:
1. ✅ `robots.txt` of target sites
2. ✅ Terms of Service
3. ✅ Reasonable rate limiting (2s minimum)
4. ✅ No circumvention of authentication

This system is designed for **personal research and investment analysis** only. Commercial use may require permission from site owners.

## Support

For issues or questions:
1. Check logs with DEBUG logging enabled
2. Review test suite output
3. Verify cache contents
4. Test with known-good region (e.g., "Sleman Yogyakarta")

## Changelog

**October 19, 2025** - Initial implementation
- ✅ Base scraper infrastructure
- ✅ Lamudi and Rumah.com scrapers
- ✅ Orchestrator with cascading fallback
- ✅ Cache persistence (24h expiry)
- ✅ Financial metrics integration
- ✅ Comprehensive test suite
