"""
99.co scraper for Indonesian land prices
CloudClearingAPI - October 25, 2025 (Phase 2A.5)
Updated March 2026: Use __NEXT_DATA__ JSON instead of CSS selectors
Updated April 2026: Detect Cloudflare JS challenge and short-circuit the
    rest of the run instead of paying ~15s/region on a guaranteed failure.

Scrapes land listings from 99.co Indonesia real estate portal
Third-tier fallback in multi-source scraping strategy.

NOTE on 99.co status (2026-04): 99.co sits behind Cloudflare's
"Just a moment..." JavaScript challenge. Plain HTTP scraping
(requests + BeautifulSoup) cannot solve it. Reviving live 99.co
scraping requires either Playwright/Selenium with stealth, the
cloudscraper library, or a 99.co API/data partnership.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime
from typing import List, Optional

from .base_scraper import BaseLandPriceScraper, ScrapedListing, ScrapeResult

logger = logging.getLogger(__name__)

# Process-wide short-circuit flag. Once we detect the Cloudflare challenge
# (or the operator forces it via env), every remaining region in the run
# skips 99.co immediately rather than paying ~15s of HTTP + retries each.
_NINETY_NINE_BLOCKED = threading.Event()
if os.environ.get("CC_99CO_DISABLED", "").lower() in ("1", "true", "yes"):
    _NINETY_NINE_BLOCKED.set()
    logger.info("99.co disabled via CC_99CO_DISABLED env var")

# Markers that mean the response is the Cloudflare challenge page, not real
# listings. Any of these → flip the breaker and treat the call as failed.
_CF_CHALLENGE_MARKERS = (
    'Just a moment...',
    'challenges.cloudflare.com',
    'cf-challenge',
    'cf_chl_opt',
)


class NinetyNineScraper(BaseLandPriceScraper):
    """
    Scraper for 99.co land listings (Indonesia)

    99.co is a Next.js app. All listing data is embedded in a
    <script id="__NEXT_DATA__"> JSON blob, so we parse that directly
    instead of trying to match CSS selectors.

    Process-wide breaker: if any region's response is the Cloudflare JS
    challenge, we skip live 99.co for the rest of the run.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.99.co"

    def get_source_name(self) -> str:
        return "99.co"

    # ------------------------------------------------------------------
    # Region → city slug mapping (same approach as Lamudi / Rumah.com)
    # ------------------------------------------------------------------

    _LOCATION_MAP = {
        'jakarta': 'jakarta', 'bandung': 'bandung', 'surabaya': 'surabaya',
        'semarang': 'semarang', 'yogyakarta': 'yogyakarta', 'solo': 'solo',
        'surakarta': 'solo', 'malang': 'malang', 'bogor': 'bogor',
        'tangerang': 'tangerang', 'bekasi': 'bekasi', 'cirebon': 'cirebon',
        'tegal': 'tegal', 'purwokerto': 'purwokerto', 'sleman': 'sleman',
        'bantul': 'bantul', 'gunungkidul': 'gunungkidul', 'kulonprogo': 'kulon-progo',
        'magelang': 'magelang', 'serang': 'serang', 'cilegon': 'cilegon',
        'gresik': 'gresik', 'sidoarjo': 'sidoarjo', 'probolinggo': 'probolinggo',
        'banyuwangi': 'banyuwangi', 'jember': 'jember', 'cikarang': 'cikarang',
        'subang': 'subang', 'karawang': 'karawang', 'depok': 'depok',
        'merak': 'merak', 'anyer': 'anyer',
    }

    def _extract_city_slug(self, region_name: str) -> str:
        """Map internal region name → 99.co city slug."""
        normalized = region_name.lower()

        if normalized in self._LOCATION_MAP:
            return self._LOCATION_MAP[normalized]

        # Split compound names like "jakarta_north_sprawl"
        parts = normalized.replace('_', ' ').split()
        for part in parts:
            if part in self._LOCATION_MAP:
                return self._LOCATION_MAP[part]

        first_word = parts[0] if parts else normalized
        logger.warning(f"No 99.co location mapping for '{region_name}', using: '{first_word}'")
        return first_word

    # ------------------------------------------------------------------
    # Core scrape logic
    # ------------------------------------------------------------------

    def _scrape_live(self, region_name: str, max_listings: int) -> ScrapeResult:
        # Process-wide short-circuit: if 99.co is known-blocked for this run
        # (Cloudflare challenge already detected, or env-disabled), don't
        # waste 15s+ per region.
        if _NINETY_NINE_BLOCKED.is_set():
            return self._empty_result(
                region_name,
                "99.co disabled for this run (Cloudflare challenge or CC_99CO_DISABLED)",
            )

        # Lazy one-shot CF probe: hit the 99.co homepage with raw requests so
        # we can inspect status + body even when CF returns 403 (base scraper
        # would swallow that). This runs only on the first region per run.
        self._probe_cloudflare_once()
        if _NINETY_NINE_BLOCKED.is_set():
            return self._empty_result(region_name, "99.co Cloudflare challenge (probe)")

        logger.info(f"Starting live scrape of 99.co for {region_name}")

        search_url = self._build_search_url(region_name)
        logger.debug(f"Search URL: {search_url}")

        soup = self._make_request(search_url)
        if not soup:
            return self._empty_result(region_name, "Failed to fetch search results page")

        # Cloudflare-challenge detection: trip the breaker so the remaining
        # regions skip 99.co for the rest of the run.
        body_text = soup.decode() if hasattr(soup, 'decode') else str(soup)
        if any(marker in body_text for marker in _CF_CHALLENGE_MARKERS):
            if not _NINETY_NINE_BLOCKED.is_set():
                _NINETY_NINE_BLOCKED.set()
                logger.warning(
                    f"⛔ 99.co served Cloudflare JS challenge for {region_name} — "
                    "tripping breaker; remaining regions will skip 99.co. "
                    "Reviving requires Playwright/cloudscraper or a data partnership."
                )
            return self._empty_result(region_name, "99.co Cloudflare challenge")

        listings = self._parse_search_results(soup, region_name, max_listings)

        if not listings:
            logger.warning(f"No listings found on 99.co for {region_name}")
            return self._empty_result(region_name, "No listings found in search results")

        stats = self._calculate_statistics(listings)

        return ScrapeResult(
            region_name=region_name,
            average_price_per_m2=stats['average'],
            median_price_per_m2=stats['median'],
            listing_count=len(listings),
            listings=listings,
            source=self.get_source_name(),
            scraped_at=datetime.now(),
            success=True,
        )

    def _empty_result(self, region_name: str, error: str) -> ScrapeResult:
        return ScrapeResult(
            region_name=region_name,
            average_price_per_m2=0,
            median_price_per_m2=0,
            listing_count=0,
            listings=[],
            source=self.get_source_name(),
            scraped_at=datetime.now(),
            success=False,
            error_message=error,
        )

    def _build_search_url(self, region_name: str) -> str:
        city_slug = self._extract_city_slug(region_name)
        return f"{self.base_url}/id/jual/tanah/{city_slug}"

    _probed_once = False

    def _probe_cloudflare_once(self) -> None:
        """Hit 99.co homepage once per run to detect CF challenge.

        Uses raw ``requests`` (not the BaseScraper helper) so we can inspect
        the body even when CF returns HTTP 403 — the BaseScraper raises and
        discards the body.
        """
        if NinetyNineScraper._probed_once or _NINETY_NINE_BLOCKED.is_set():
            return
        NinetyNineScraper._probed_once = True
        try:
            import requests
            resp = requests.get(
                f"{self.base_url}/id",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                },
                timeout=10,
            )
            body = resp.text
            cf_detected = (
                resp.status_code == 403
                or any(marker in body for marker in _CF_CHALLENGE_MARKERS)
            )
            if cf_detected:
                _NINETY_NINE_BLOCKED.set()
                logger.warning(
                    f"⛔ 99.co probe: Cloudflare challenge detected (HTTP {resp.status_code}) — "
                    "skipping 99.co for the rest of this run"
                )
            else:
                logger.info(f"✅ 99.co probe: HTTP {resp.status_code}, no CF challenge — proceeding")
        except Exception as e:
            logger.warning(f"99.co probe failed ({type(e).__name__}: {e}); will still attempt scraping")

    # ------------------------------------------------------------------
    # Parsing — __NEXT_DATA__ JSON (primary) with HTML fallback
    # ------------------------------------------------------------------

    def _parse_search_results(self, soup, region_name: str, max_listings: int) -> List[ScrapedListing]:
        """Parse listings from 99.co search results page."""
        listings: List[ScrapedListing] = []

        # PRIORITY 1: __NEXT_DATA__ JSON (Next.js data blob)
        next_data_tag = soup.find('script', id='__NEXT_DATA__')
        if next_data_tag and next_data_tag.string:
            try:
                nd = json.loads(next_data_tag.string)
                raw_listings = (
                    nd.get('props', {})
                      .get('pageProps', {})
                      .get('data', {})
                      .get('listings', [])
                )
                for group in raw_listings[:max_listings]:
                    items = group.get('data', [])
                    for item in items:
                        listing = self._parse_next_data_item(item, region_name)
                        if listing:
                            listings.append(listing)
                            if len(listings) >= max_listings:
                                break
                    if len(listings) >= max_listings:
                        break

                if listings:
                    logger.info(f"Extracted {len(listings)} listings from 99.co __NEXT_DATA__")
                    return listings[:max_listings]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Failed to parse __NEXT_DATA__: {e}")

        # PRIORITY 2: JSON-LD @graph → ItemList
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '{}')
                graphs = data.get('@graph', [data])
                for graph in graphs:
                    if graph.get('@type') != 'ItemList':
                        continue
                    for elem in graph.get('itemListElement', [])[:max_listings]:
                        item = elem.get('item', elem)
                        listing = self._parse_jsonld_item(item, region_name)
                        if listing:
                            listings.append(listing)
                            if len(listings) >= max_listings:
                                break
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        if listings:
            logger.info(f"Extracted {len(listings)} listings from 99.co JSON-LD")

        return listings[:max_listings]

    def _parse_next_data_item(self, item: dict, region_name: str) -> Optional[ScrapedListing]:
        """Parse a single listing from __NEXT_DATA__ JSON."""
        try:
            # Price (exact numeric IDR)
            price_data = item.get('price', {})
            total_price = price_data.get('price', 0)
            if not total_price or total_price <= 0:
                return None

            # Land area
            attrs = item.get('attributes', {})
            land_area_info = attrs.get('land_area', {})
            area_str = str(land_area_info.get('value', '0')).replace(',', '')
            try:
                size_m2 = float(area_str)
            except ValueError:
                return None

            if size_m2 <= 0:
                return None

            price_per_m2 = total_price / size_m2

            # Location
            full_address = (item.get('full_address', '') or '').strip()
            location_info = item.get('location', {})
            district = ''
            if location_info:
                district_info = location_info.get('district', {})
                if isinstance(district_info, dict):
                    district = district_info.get('name', '')

            location = full_address or district or region_name

            # URL
            url_slug = item.get('url', '')
            listing_url = f"{self.base_url}/id/properti/{url_slug}" if url_slug else ''

            # Date
            timestamps = item.get('timestamps', {})
            published = timestamps.get('published', 0)
            listing_date = None
            if published:
                try:
                    listing_date = datetime.fromtimestamp(published).strftime('%Y-%m-%d')
                except (OSError, ValueError):
                    pass

            return ScrapedListing(
                price_per_m2=price_per_m2,
                total_price=total_price,
                size_m2=size_m2,
                location=location,
                listing_date=listing_date,
                source_url=listing_url,
                listing_type='land',
            )
        except Exception as e:
            logger.debug(f"Failed to parse __NEXT_DATA__ item: {e}")
            return None

    def _parse_jsonld_item(self, item: dict, region_name: str) -> Optional[ScrapedListing]:
        """Parse a single listing from JSON-LD structured data."""
        try:
            # Price
            offers = item.get('offers', {})
            price = offers.get('price', 0)
            if isinstance(price, str):
                price = float(price.replace(',', '').replace('.', ''))
            if not price or price <= 0:
                return None

            # Land area
            floor_size = item.get('floorSize', {})
            area_str = str(floor_size.get('value', '0')).replace(',', '')
            try:
                size_m2 = float(area_str)
            except ValueError:
                return None

            if size_m2 <= 0:
                return None

            price_per_m2 = price / size_m2

            # Location
            address = item.get('address', {})
            location = address.get('streetAddress', '') or address.get('addressLocality', '') or region_name

            # URL
            listing_url = item.get('url', '')
            if listing_url and not listing_url.startswith('http'):
                listing_url = self.base_url + listing_url

            return ScrapedListing(
                price_per_m2=price_per_m2,
                total_price=price,
                size_m2=size_m2,
                location=location,
                listing_date=None,
                source_url=listing_url,
                listing_type='land',
            )
        except Exception as e:
            logger.debug(f"Failed to parse JSON-LD item: {e}")
            return None


# Standalone test
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = NinetyNineScraper(cache_expiry_hours=24)

    print(f"\n{'='*70}")
    print(f"TESTING 99.CO SCRAPER")
    print(f"{'='*70}")

    for test_region in ['tangerang', 'yogyakarta', 'bandung', 'jakarta', 'surabaya']:
        result = scraper.get_price_data(test_region, max_listings=10)
        status = "OK" if result.success else result.error_message
        print(f"  {test_region:20s} → {result.listing_count:2d} listings, "
              f"Avg Rp {result.average_price_per_m2:>12,.0f}/m², "
              f"Median Rp {result.median_price_per_m2:>12,.0f}/m²  [{status}]")

        if result.listings:
            for i, listing in enumerate(result.listings[:2], 1):
                print(f"    {i}. {listing.location[:50]} - "
                      f"Rp {listing.price_per_m2:,.0f}/m² "
                      f"({listing.size_m2:,.0f}m²)")
