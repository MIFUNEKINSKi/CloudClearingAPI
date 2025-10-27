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
        """
        Scrape live land prices from Lamudi
        
        Args:
            region_name: Region to search (e.g., "Sleman Yogyakarta")
            max_listings: Maximum listings to scrape
            
        Returns:
            ScrapeResult with scraped listings
        """
        logger.info(f"Starting live scrape of Lamudi for {region_name}")
        
        # Build search URL for land listings
        search_url = self._build_search_url(region_name)
        logger.debug(f"Search URL: {search_url}")
        
        # Fetch search results page
        soup = self._make_request(search_url)
        if not soup:
            return ScrapeResult(
                region_name=region_name,
                average_price_per_m2=0,
                median_price_per_m2=0,
                listing_count=0,
                listings=[],
                source=self.get_source_name(),
                scraped_at=datetime.now(),
                success=False,
                error_message="Failed to fetch search results page"
            )
        
        # Parse listings from search results
        listings = self._parse_search_results(soup, region_name, max_listings)
        
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
        
        # Calculate statistics
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
            'surakarta': 'solo',  # Solo is also known as Surakarta
            'malang': 'malang',
            'bogor': 'bogor',
            'depok': 'depok',
            'tangerang': 'tangerang',
            'bekasi': 'bekasi',
            'cirebon': 'cirebon',
            'tegal': 'tegal',
            'pekalongan': 'pekalongan',
            'purwokerto': 'purwokerto',
            
            # Yogyakarta Special Region
            'sleman': 'sleman',
            'bantul': 'bantul',
            'gunungkidul': 'gunungkidul',
            'kulonprogo': 'kulonprogo',
            'kulon progo': 'kulonprogo',
            
            # Central Java
            'magelang': 'magelang',
            'salatiga': 'salatiga',
            'purwokerto': 'purwokerto',
            'cilacap': 'cilacap',
            'brebes': 'brebes',
            
            # West Java
            'cimahi': 'cimahi',
            'tasikmalaya': 'tasikmalaya',
            'cianjur': 'cianjur',
            'sukabumi': 'sukabumi',
            'karawang': 'karawang',
            'purwakarta': 'purwakarta',
            
            # Banten
            'serang': 'serang',
            'cilegon': 'cilegon',
            
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
            'bali': 'denpasar',  # Bali region defaults to Denpasar
            'badung': 'badung',
            'gianyar': 'gianyar',
            'tabanan': 'tabanan',
            'sanur': 'sanur',
            'ubud': 'ubud',
            'seminyak': 'seminyak',
            'kuta': 'kuta',
        }
        
        # Try exact match first (for simple region names)
        if normalized in location_map:
            return location_map[normalized]
        
        # Extract first meaningful word from region identifier
        # Handle both underscore format (jakarta_north_sprawl) and space format (Jakarta North)
        parts = normalized.replace('_', ' ').split()
        
        # Try each part starting from the beginning
        for part in parts:
            if part in location_map:
                return location_map[part]
        
        # If no match found, try to extract the first word (likely the city)
        # and return it as-is (fallback for unmapped cities)
        first_word = parts[0] if parts else normalized
        
        logger.warning(f"No location mapping found for '{region_name}', using first word: '{first_word}'")
        return first_word
    
    def _build_search_url(self, region_name: str) -> str:
        """
        Build Lamudi search URL for land in region
        
        Args:
            region_name: Region to search
            
        Returns:
            Full search URL
        """
        # Lamudi URL structure: /tanah/jual/{location}/ (Indonesian "jual" = sell/sale)
        # Fixed Oct 26, 2025: Changed from /buy/ to /jual/ (Indonesian language requirement)
        # Fixed Oct 26, 2025: Added location mapping to extract city from region identifier
        
        # Extract city slug from region name (e.g., "jakarta_north_sprawl" → "jakarta")
        location_slug = self._extract_city_from_region(region_name)
        
        logger.debug(f"Mapped region '{region_name}' → city slug '{location_slug}'")
        
        # Search for land (tanah) listings
        search_url = f"{self.base_url}/tanah/jual/{location_slug}/"
        
        # Add filters: sort by newest, land only
        search_url += "?sort=newest"
        
        return search_url
    
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
        
        # PRIORITY 1: Try JSON-LD structured data (Lamudi includes this in initial HTML)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                
                # Handle both single objects and arrays
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'about' in item:
                            # "about" contains array of Accommodation objects
                            accommodations = item.get('about', [])
                            for accommodation in accommodations[:max_listings]:
                                listing = self._parse_json_ld_listing(accommodation, region_name)
                                if listing:
                                    listings.append(listing)
                elif isinstance(data, dict) and 'about' in data:
                    accommodations = data.get('about', [])
                    for accommodation in accommodations[:max_listings]:
                        listing = self._parse_json_ld_listing(accommodation, region_name)
                        if listing:
                            listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD: {str(e)}")
                continue
        
        if listings:
            logger.info(f"Extracted {len(listings)} listings from JSON-LD structured data")
            return listings[:max_listings]
        
        # FALLBACK: Try HTML parsing (legacy method - may not work with JS rendering)
        logger.debug("No JSON-LD found, trying HTML parsing...")
        
        # Try primary selector
        listing_cards = soup.find_all('div', class_=re.compile(r'ListingCard|PropertyCard|listing-item', re.I))
        
        if not listing_cards:
            # Try alternative selectors
            listing_cards = soup.find_all('article', class_=re.compile(r'listing|property', re.I))
        
        if not listing_cards:
            # Try data attributes
            listing_cards = soup.find_all(attrs={'data-listing-id': True})
        
        logger.debug(f"Found {len(listing_cards)} potential listing cards")
        
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
