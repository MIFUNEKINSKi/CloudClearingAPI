"""
Lamudi.co.id scraper for Indonesian land prices
CloudClearingAPI - October 19, 2025

Scrapes land listings from Lamudi Indonesia real estate portal
"""

import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from .base_scraper import BaseLandPriceScraper, ScrapedListing, ScrapeResult

logger = logging.getLogger(__name__)


class LamudiScraper(BaseLandPriceScraper):
    """
    Scraper for Lamudi.co.id land listings
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.lamudi.co.id"
    
    def get_source_name(self) -> str:
        return "lamudi"
    
    def _scrape_live(self, region_name: str, max_listings: int) -> ScrapeResult:
        """Scrape live land prices from Lamudi with automatic province-level fallback."""
        logger.info(f"Starting live scrape of Lamudi for {region_name}")
        
        search_url = self._build_search_url(region_name)
        logger.debug(f"Search URL: {search_url}")
        
        soup = self._make_request(search_url)
        listings = []
        if soup:
            listings = self._parse_search_results(soup, region_name, max_listings)
        
        # If no listings, try province-level fallback slug
        if not listings:
            fallback_slug = self._get_fallback_slug(region_name)
            if fallback_slug:
                logger.info(f"  Retrying {region_name} with province slug '{fallback_slug}'")
                fb_url = self._build_search_url(region_name, slug_override=fallback_slug)
                fb_soup = self._make_request(fb_url)
                if fb_soup:
                    listings = self._parse_search_results(fb_soup, region_name, max_listings)
        
        if not listings:
            logger.warning(f"No listings found for {region_name}")
            return ScrapeResult(
                region_name=region_name,
                average_price_per_m2=0,
                median_price_per_m2=0,
                listing_count=0,
                listings=[],
                source=self.get_source_name(),
                scraped_at=datetime.now(),
                success=False,
                error_message="No listings found in search results"
            )
        
        stats = self._calculate_statistics(listings)
        
        return ScrapeResult(
            region_name=region_name,
            average_price_per_m2=stats['average'],
            median_price_per_m2=stats['median'],
            listing_count=len(listings),
            listings=listings,
            source=self.get_source_name(),
            scraped_at=datetime.now(),
            success=True
        )
    
    def _extract_city_from_region(self, region_name: str) -> str:
        """
        Extract city/location slug from internal region name
        
        Maps internal region identifiers to Lamudi-compatible city slugs.
        
        Args:
            region_name: Internal region identifier (e.g., "jakarta_north_sprawl", "Sleman North")
            
        Returns:
            City slug for Lamudi (e.g., "jakarta", "sleman")
            
        Examples:
            jakarta_north_sprawl → jakarta
            bandung_north_expansion → bandung
            yogyakarta_periurban → yogyakarta
            tegal_brebes_coastal → tegal
            Sleman North → sleman
            Bantul South → bantul
        """
        # Normalize to lowercase
        normalized = region_name.lower()
        
        # Location mapping dictionary (internal region name prefix → Lamudi city slug)
        # Maps our region identifiers to Indonesian city names that Lamudi recognizes
        location_map = {
            # Java - Major Cities
            'jakarta': 'jakarta',
            'bandung': 'bandung',
            'surabaya': 'surabaya',
            'semarang': 'semarang',
            'yogyakarta': 'yogyakarta',
            'solo': 'solo',
            'surakarta': 'solo',
            'malang': 'malang',
            'bogor': 'bogor',
            'depok': 'depok',
            'tangerang': 'tangerang',
            'bekasi': 'bekasi',
            'cirebon': 'cirebon',
            'tegal': 'tegal',
            'pekalongan': 'pekalongan',
            'purwokerto': 'banyumas',
            'batang': 'batang',
            
            # Yogyakarta Special Region
            'sleman': 'sleman',
            'bantul': 'bantul',
            'gunungkidul': 'gunung-kidul',  # Lamudi slug is hyphenated
            # Lamudi switched to hyphenated 'kulon-progo' slug; the no-hyphen
            # form returns 404. Verified 2026-04-25: the hyphen-form URL
            # returned a 766KB listing page; the no-hyphen form returned the
            # 145KB 404 template.
            'kulonprogo': 'kulon-progo',
            'kulon progo': 'kulon-progo',
            'kulon_progo': 'kulon-progo',

            # Central Java
            'magelang': 'magelang',
            'salatiga': 'salatiga',
            'cilacap': 'cilacap',
            'brebes': 'brebes',
            
            # West Java
            'cikarang': 'cikarang',
            'subang': 'subang',
            'cimahi': 'cimahi',
            'tasikmalaya': 'tasikmalaya',
            'cianjur': 'cianjur',
            'sukabumi': 'sukabumi',
            'karawang': 'karawang',
            'purwakarta': 'purwakarta',
            
            # Banten
            'serang': 'serang',
            'cilegon': 'cilegon',
            'merak': 'serang',
            'anyer': 'serang',
            'bakauheni': 'lampung',
            
            # East Java
            'gresik': 'gresik',
            'sidoarjo': 'sidoarjo',
            'mojokerto': 'mojokerto',
            'pasuruan': 'pasuruan',
            'probolinggo': 'probolinggo',
            'banyuwangi': 'banyuwangi',
            'jember': 'jember',
            'kediri': 'kediri',
            'madiun': 'madiun',
            'blitar': 'blitar',
            
            # Bali
            'denpasar': 'denpasar',
            'bali': 'denpasar',
            'badung': 'badung',
            'gianyar': 'gianyar',
            'tabanan': 'tabanan',
            'sanur': 'badung',
            'ubud': 'gianyar',
            'seminyak': 'badung',
            'canggu': 'badung',
            'kuta': 'kuta',
            
            # Sumatra
            'medan': 'medan',
            'belawan': 'medan',
            'palembang': 'palembang',
            'jakabaring': 'palembang',
            'lampung': 'lampung',
            'padang': 'padang',
            'aceh': 'banda-aceh',
            'batam': 'batam',
            'pekanbaru': 'pekanbaru',
            'toba': 'toba-samosir',
            'samosir': 'toba-samosir',
            
            # Lombok / NTB — 'lombok-barat' has more listings than bare 'lombok'
            'lombok': 'lombok-barat',
            'mataram': 'mataram',
            'mandalika': 'lombok-tengah',
            'senggigi': 'lombok-barat',
            
            # Kalimantan
            'nusantara': 'penajam-paser-utara',
            'balikpapan': 'balikpapan',
            'samarinda': 'samarinda',
            'banjarmasin': 'banjarmasin',
            'pontianak': 'pontianak',
            
            # Sulawesi
            'makassar': 'makassar',
            'manado': 'manado',
            'bitung': 'bitung',
            
            # NTT / Papua / Maluku
            'labuan': 'manggarai-barat',
            'kupang': 'kupang',
            'jayapura': 'jayapura',
            'ambon': 'ambon',
        }
        
        # Compound name mappings (checked before single-word)
        compound_map = {
            'nusa dua': 'badung',
            'banda aceh': 'banda-aceh',
            'bandar lampung': 'lampung',
            'lake toba': 'toba-samosir',
            'solo raya': 'sukoharjo',
            'kulon progo': 'kulon-progo',  # Lamudi slug is hyphenated
            'labuan bajo': 'manggarai-barat',
        }
        
        if normalized in location_map:
            return location_map[normalized]
        
        parts = normalized.replace('_', ' ').split()
        
        # Try compound name matches (2-word combinations)
        for i in range(len(parts) - 1):
            compound = parts[i] + ' ' + parts[i + 1]
            if compound in compound_map:
                return compound_map[compound]
        
        # Try each single word
        for part in parts:
            if part in location_map:
                return location_map[part]
        
        # If no match found, try to extract the first word (likely the city)
        # and return it as-is (fallback for unmapped cities)
        first_word = parts[0] if parts else normalized
        
        logger.warning(f"No location mapping found for '{region_name}', using first word: '{first_word}'")
        return first_word
    
    # Province-level fallback slugs for regions with thin or missing Lamudi coverage
    PROVINCE_FALLBACKS = {
        'samosir': 'sumatera-utara',
        'toba-samosir': 'sumatera-utara',
        'lombok': 'nusa-tenggara-barat',
        'lombok-barat': 'nusa-tenggara-barat',
        'lombok-tengah': 'nusa-tenggara-barat',
        'kupang': 'nusa-tenggara-timur',
        'manggarai-barat': 'nusa-tenggara-timur',
        'jayapura': 'papua',
        'ambon': 'maluku',
        'bitung': 'sulawesi-utara',
        'sukoharjo': 'jawa-tengah',
    }

    def _build_search_url(self, region_name: str, slug_override: str = None) -> str:
        """Build Lamudi search URL for land in region."""
        location_slug = slug_override or self._extract_city_from_region(region_name)
        logger.debug(f"Mapped region '{region_name}' → city slug '{location_slug}'")
        search_url = f"{self.base_url}/tanah/jual/{location_slug}/?sort=newest"
        return search_url

    def _get_fallback_slug(self, region_name: str) -> Optional[str]:
        """Return a broader province-level slug when a city slug has no listings."""
        primary_slug = self._extract_city_from_region(region_name)
        return self.PROVINCE_FALLBACKS.get(primary_slug)
    
    def _parse_search_results(self, soup, region_name: str, max_listings: int) -> List[ScrapedListing]:
        """
        Parse listings from Lamudi search results page
        
        FIXED Oct 26, 2025: Lamudi now uses JavaScript rendering for listing cards,
        but includes JSON-LD structured data in the initial HTML. We extract from that.
        
        Args:
            soup: BeautifulSoup object of search results
            region_name: Region being searched
            max_listings: Maximum listings to extract
            
        Returns:
            List of ScrapedListing objects
        """
        listings = []
        
        # PRIORITY 1: Try JSON-LD @graph → mainEntity → itemListElement path (2026 structure)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)

                # Navigate 2026 structure: [{@graph: [{mainEntity: [ItemList...]}]}]
                graph_items = []
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and '@graph' in item:
                            graph_items.extend(item['@graph'])
                        elif isinstance(item, dict) and 'about' in item:
                            # Legacy 2025 structure
                            accommodations = item.get('about', [])
                            for acc in accommodations[:max_listings]:
                                listing = self._parse_json_ld_listing(acc, region_name)
                                if listing:
                                    listings.append(listing)

                for graph_item in graph_items:
                    main_entity = graph_item.get('mainEntity', [])
                    if not isinstance(main_entity, list):
                        main_entity = [main_entity]
                    for entity in main_entity:
                        if isinstance(entity, dict) and entity.get('@type') == 'ItemList':
                            elements = entity.get('itemListElement', [])
                            for el in elements[:max_listings]:
                                acc = el.get('item', el)
                                listing = self._parse_json_ld_listing(acc, region_name)
                                if listing:
                                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD: {str(e)}")
                continue

        if len(listings) >= 5:
            logger.info(f"Extracted {len(listings)} listings from JSON-LD structured data")
            return listings[:max_listings]

        # PRIORITY 2: HTML snippet parsing (2026 Lamudi uses snippet__content__* classes)
        # Also used when JSON-LD returns <5 listings (common — JSON-LD often lacks prices)
        logger.debug("JSON-LD had no prices, trying HTML snippet parsing...")

        price_divs = soup.find_all('div', class_='snippet__content__price')

        for pd in price_divs[:max_listings]:
            try:
                parent_a = pd.find_parent('a')
                if not parent_a:
                    continue

                # Price (Indonesian format: "Rp 12Jt", "Rp 282,57M", "Rp 5,30Jt/m²")
                price_text = pd.get_text(strip=True)
                price_idr = self._parse_indonesian_price(price_text)
                if not price_idr or price_idr <= 0:
                    continue

                # Detect if price is per-m² (contains /m or per m)
                is_per_m2 = bool(re.search(r'/m|per\s*m', price_text, re.IGNORECASE))

                # Area (m²) from snippet__content__properties
                area_div = parent_a.find('div', class_='snippet__content__properties')
                area_m2 = 0.0
                if area_div:
                    area_text = area_div.get_text(strip=True)
                    # Parse "1.600 m²" or "1600 m²"
                    area_match = re.search(r'([\d.]+(?:,\d+)?)\s*m', area_text)
                    if area_match:
                        area_str = area_match.group(1).replace('.', '').replace(',', '.')
                        area_m2 = float(area_str)

                if area_m2 <= 0:
                    continue

                if is_per_m2:
                    price_per_m2 = price_idr
                    price_idr = price_idr * area_m2  # Calculate total
                else:
                    price_per_m2 = price_idr / area_m2
                    # Sanity check: if price/m² is suspiciously low (<100k IDR),
                    # the "total" price might actually be per-m²
                    if price_per_m2 < 100_000 and price_idr > 1_000_000:
                        price_per_m2 = price_idr  # Treat as per-m²
                        price_idr = price_per_m2 * area_m2

                # Title + location
                title_div = parent_a.find('div', class_='snippet__content__title__container')
                title = title_div.get_text(strip=True) if title_div else ''
                loc_div = parent_a.find('div', class_='snippet__content__location')
                location = loc_div.get_text(strip=True) if loc_div else ''

                href = parent_a.get('href', '')
                if href and not href.startswith('http'):
                    href = self.base_url + href

                listing = ScrapedListing(
                    total_price=price_idr,
                    price_per_m2=price_per_m2,
                    size_m2=area_m2,
                    location=location or title or region_name,
                    source_url=href,
                    listing_date=None,
                    listing_type='land',
                )
                listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse snippet card: {str(e)}")
                continue

        if listings:
            logger.info(f"Extracted {len(listings)} listings from HTML snippets")
            return listings[:max_listings]

        # FALLBACK 3: Legacy HTML parsing
        listing_cards = soup.find_all('div', class_=re.compile(r'ListingCard|PropertyCard|listing-item', re.I))
        if not listing_cards:
            listing_cards = soup.find_all('article', class_=re.compile(r'listing|property', re.I))
        if not listing_cards:
            listing_cards = soup.find_all(attrs={'data-listing-id': True})

        for card in listing_cards[:max_listings]:
            try:
                listing = self._parse_listing_card(card, region_name)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse listing card: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(listings)} listings from {len(listing_cards)} cards")
        return listings
    
    def _parse_indonesian_price(self, price_text: str) -> float:
        """
        Parse Indonesian price format to IDR value.

        Examples:
            "Rp 12Jt"        → 12,000,000 (12 Juta)
            "Rp 282,57M"     → 282,570,000,000 (wait, that's too much)
            "Rp 1,5M"        → 1,500,000,000 (1.5 Miliar)
            "Rp 6,10Jt"      → 6,100,000 (6.1 Juta)
            "Rp 850Jt"       → 850,000,000

        Returns:
            Price in IDR, or 0 if parsing fails
        """
        import re
        text = price_text.strip().replace('Rp', '').replace('.', '').strip()

        # Match number + suffix (Jt/Juta = million, M/Miliar = billion)
        match = re.match(r'([\d,]+(?:,\d+)?)\s*(Jt|Juta|M|Miliar|Rb|Ribu)?', text, re.IGNORECASE)
        if not match:
            return 0

        num_str = match.group(1).replace(',', '.')  # Convert comma decimal to dot
        suffix = (match.group(2) or '').lower()

        try:
            value = float(num_str)
        except ValueError:
            return 0

        if suffix in ('jt', 'juta'):
            return value * 1_000_000
        elif suffix in ('m', 'miliar'):
            return value * 1_000_000_000
        elif suffix in ('rb', 'ribu'):
            return value * 1_000
        else:
            return value  # Already in IDR

    def _parse_json_ld_listing(self, accommodation: dict, region_name: str) -> Optional[ScrapedListing]:
        """
        Parse listing from JSON-LD Accommodation object

        JSON-LD structure from Lamudi:
        {
            "@type": "Accommodation",
            "name": "Land Dijual di...",
            "description": "...",
            "floorSize": {"@type": "QuantitativeValue", "value": "498", "unitCode": "MTK"},
            "geo": {"@type": "GeoCoordinates", "latitude": "-7.757521", "longitude": "110.453468"},
            "address": {...},
            "url": "https://www.lamudi.co.id/jual/..."
        }
        
        Args:
            accommodation: JSON-LD Accommodation object
            region_name: Region name
            
        Returns:
            ScrapedListing or None if parsing fails
        """
        try:
            # Extract floor size (land area in m²)
            floor_size_obj = accommodation.get('floorSize', {})
            if not isinstance(floor_size_obj, dict):
                return None
            
            size_str = floor_size_obj.get('value', '0')
            try:
                land_area_m2 = float(size_str)
            except (ValueError, TypeError):
                return None
            
            if land_area_m2 == 0:
                return None
            
            # Lamudi JSON-LD doesn't include price directly
            # We need to extract from description or use default estimation
            # For now, we'll extract what we can and mark price as needing fallback
            
            description = accommodation.get('description', '')
            name = accommodation.get('name', '')
            
            # Try to extract price from description (common patterns)
            price_per_m2 = 0
            total_price = 0
            
            # Pattern 1: "Harga 3,75jt/m2" or "3.75 juta/m"
            import re
            price_patterns = [
                r'(?:harga|price)?\s*(\d+[,.]\d+)\s*(?:jt|juta|million)(?:/| per )?m',  # 3.75 juta/m
                r'(\d+[,.]\d+)\s*(?:jt|juta|million)(?:/| per )?m²?',  # 3.75jt/m2
                r'(\d+[,.]\d+)\s*(?:miliar|milyar|billion)',  # Total price in billions
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, description + ' ' + name, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(',', '.')
                    try:
                        price_value = float(price_str)
                        # Determine if it's price/m2 or total
                        if 'jt' in match.group(0).lower() or 'juta' in match.group(0).lower():
                            if '/m' in match.group(0).lower() or ' per m' in match.group(0).lower():
                                price_per_m2 = price_value * 1_000_000  # Convert juta to rupiah
                                total_price = price_per_m2 * land_area_m2
                            else:
                                total_price = price_value * 1_000_000  # Total price in juta
                                price_per_m2 = total_price / land_area_m2 if land_area_m2 > 0 else 0
                        elif 'miliar' in match.group(0).lower() or 'milyar' in match.group(0).lower():
                            total_price = price_value * 1_000_000_000  # Convert miliar to rupiah
                            price_per_m2 = total_price / land_area_m2 if land_area_m2 > 0 else 0
                        
                        if price_per_m2 > 0:
                            break
                    except (ValueError, ZeroDivisionError):
                        continue
            
            # If we couldn't extract price, skip this listing
            if price_per_m2 == 0 and total_price == 0:
                logger.debug(f"Skipping listing '{name}' - no price found in JSON-LD")
                return None
            
            # Create listing with correct dataclass fields
            listing = ScrapedListing(
                price_per_m2=price_per_m2,
                total_price=total_price,
                size_m2=land_area_m2,
                location=name,  # Use property name as location
                listing_date=None,  # JSON-LD doesn't include date
                source_url=accommodation.get('url', ''),
                listing_type='land'
            )
            
            logger.debug(f"Parsed JSON-LD listing: {name[:50]}... - {land_area_m2}m² @ Rp{price_per_m2:,.0f}/m²")
            return listing
            
        except Exception as e:
            logger.debug(f"Failed to parse JSON-LD listing: {str(e)}")
            return None
    
    def _parse_listing_card(self, card, region_name: str) -> Optional[ScrapedListing]:
        """
        Parse individual listing card
        
        Args:
            card: BeautifulSoup element for listing card
            region_name: Region name
            
        Returns:
            ScrapedListing or None if parsing fails
        """
        # Extract price
        price_elem = card.find(class_=re.compile(r'price', re.I))
        if not price_elem:
            price_elem = card.find('span', attrs={'data-price': True})
        
        if not price_elem:
            return None
        
        price_text = price_elem.get_text(strip=True)
        total_price = self._parse_price(price_text)
        
        if total_price == 0:
            return None
        
        # Extract size (land area)
        size_elem = card.find(class_=re.compile(r'land.*area|area.*land|luas.*tanah', re.I))
        if not size_elem:
            # Try finding in specs list
            specs = card.find_all(class_=re.compile(r'spec|attribute|feature', re.I))
            for spec in specs:
                text = spec.get_text(strip=True).lower()
                if 'tanah' in text or 'land' in text or 'm²' in text or 'm2' in text:
                    size_elem = spec
                    break
        
        size_m2 = self._parse_size(size_elem.get_text(strip=True) if size_elem else "")
        
        if size_m2 == 0:
            # Try data attributes
            size_data = card.get('data-land-size') or card.get('data-area')
            if size_data:
                size_m2 = self._parse_size(str(size_data))
        
        if size_m2 == 0:
            return None
        
        # Calculate price per m²
        price_per_m2 = total_price / size_m2
        
        # Extract location
        location_elem = card.find(class_=re.compile(r'location|address|lokasi', re.I))
        location = location_elem.get_text(strip=True) if location_elem else region_name
        
        # Extract URL
        link_elem = card.find('a', href=True)
        listing_url = link_elem['href'] if link_elem else ""
        if listing_url and not listing_url.startswith('http'):
            listing_url = self.base_url + listing_url
        
        # Extract listing date (if available)
        date_elem = card.find(class_=re.compile(r'date|posted|published', re.I))
        listing_date = date_elem.get_text(strip=True) if date_elem else None
        
        return ScrapedListing(
            price_per_m2=price_per_m2,
            total_price=total_price,
            size_m2=size_m2,
            location=location,
            listing_date=listing_date,
            source_url=listing_url,
            listing_type='land'
        )
    
    def _parse_price(self, price_text: str) -> float:
        """
        Parse Indonesian price format to float
        
        Examples:
            "Rp 1.500.000.000" -> 1500000000
            "Rp 1,5 Miliar" -> 1500000000
            "Rp 500 Juta" -> 500000000
            "1.5M" -> 1500000
            
        Args:
            price_text: Price string
            
        Returns:
            Price as float (IDR)
        """
        if not price_text:
            return 0
        
        # Remove currency symbols and whitespace
        price_text = price_text.replace('Rp', '').replace('IDR', '').strip()
        
        # Handle Indonesian abbreviations
        multipliers = {
            'miliar': 1_000_000_000,
            'milyar': 1_000_000_000,
            'billion': 1_000_000_000,
            'b': 1_000_000_000,
            'juta': 1_000_000,
            'million': 1_000_000,
            'm': 1_000_000,
            'ribu': 1_000,
            'thousand': 1_000,
            'k': 1_000
        }
        
        price_lower = price_text.lower()
        multiplier = 1
        
        for keyword, mult in multipliers.items():
            if keyword in price_lower:
                multiplier = mult
                price_text = price_text.lower().replace(keyword, '').strip()
                break
        
        # Extract numeric part
        # Remove dots (thousand separators in Indonesian)
        price_text = price_text.replace('.', '')
        # Replace comma with dot (decimal separator in Indonesian)
        price_text = price_text.replace(',', '.')
        
        # Extract first number
        match = re.search(r'[\d.]+', price_text)
        if not match:
            return 0
        
        try:
            price = float(match.group(0)) * multiplier
            return price
        except ValueError:
            return 0
    
    def _parse_size(self, size_text: str) -> float:
        """
        Parse land size from text
        
        Examples:
            "1.000 m²" -> 1000
            "500 m2" -> 500
            "1,5 ha" -> 15000
            
        Args:
            size_text: Size string
            
        Returns:
            Size in m²
        """
        if not size_text:
            return 0
        
        # Handle hectares
        if 'ha' in size_text.lower() or 'hektar' in size_text.lower():
            # Extract number and convert to m² (1 ha = 10,000 m²)
            match = re.search(r'[\d.,]+', size_text)
            if match:
                try:
                    ha = float(match.group(0).replace('.', '').replace(',', '.'))
                    return ha * 10_000
                except ValueError:
                    return 0
        
        # Handle m² / m2
        # Remove m², m2, etc.
        size_text = re.sub(r'm[²2]', '', size_text, flags=re.I)
        
        # Remove thousand separators (dots in Indonesian)
        size_text = size_text.replace('.', '')
        # Replace comma with dot (decimal)
        size_text = size_text.replace(',', '.')
        
        # Extract number
        match = re.search(r'[\d.]+', size_text)
        if not match:
            return 0
        
        try:
            size = float(match.group(0))
            return size
        except ValueError:
            return 0


# Standalone test
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    scraper = LamudiScraper()
    result = scraper.get_price_data("Sleman Yogyakarta", max_listings=10)
    
    print(f"\n{'='*60}")
    print(f"LAMUDI SCRAPE RESULT - {result.region_name}")
    print(f"{'='*60}")
    print(f"Success: {result.success}")
    print(f"Listings Found: {result.listing_count}")
    print(f"Average Price: Rp {result.average_price_per_m2:,.0f}/m²")
    print(f"Median Price: Rp {result.median_price_per_m2:,.0f}/m²")
    print(f"Source: {result.source}")
    print(f"Scraped At: {result.scraped_at}")
    
    if result.error_message:
        print(f"Error: {result.error_message}")
    
    if result.listings:
        print(f"\nSample Listings:")
        for i, listing in enumerate(result.listings[:3], 1):
            print(f"\n  {i}. {listing.location}")
            print(f"     Price: Rp {listing.total_price:,.0f} (Rp {listing.price_per_m2:,.0f}/m²)")
            print(f"     Size: {listing.size_m2:,.0f} m²")
            print(f"     URL: {listing.source_url}")
