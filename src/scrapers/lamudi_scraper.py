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
    
    def _build_search_url(self, region_name: str) -> str:
        """
        Build Lamudi search URL for land in region
        
        Args:
            region_name: Region to search
            
        Returns:
            Full search URL
        """
        # Extract key location terms
        # Examples: "Sleman North" -> "Sleman", "Bantul Yogyakarta" -> "Bantul Yogyakarta"
        
        # Lamudi URL structure: /tanah/jual/{location}/ (Indonesian "jual" = sell/sale)
        # Fixed Oct 26, 2025: Changed from /buy/ to /jual/ (Indonesian language requirement)
        # URL encode the location
        location_slug = region_name.lower().replace(' ', '-')
        
        # Search for land (tanah) listings
        search_url = f"{self.base_url}/tanah/jual/{location_slug}/"
        
        # Add filters: sort by newest, land only
        search_url += "?sort=newest"
        
        return search_url
    
    def _parse_search_results(self, soup, region_name: str, max_listings: int) -> List[ScrapedListing]:
        """
        Parse listings from Lamudi search results page
        
        Args:
            soup: BeautifulSoup object of search results
            region_name: Region being searched
            max_listings: Maximum listings to extract
            
        Returns:
            List of ScrapedListing objects
        """
        listings = []
        
        # Lamudi typically uses class names like 'listing-card' or 'property-card'
        # Structure varies, so we try multiple selectors
        
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
