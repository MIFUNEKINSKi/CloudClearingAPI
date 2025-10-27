"""
99.co scraper for Indonesian land prices
CloudClearingAPI - October 25, 2025 (Phase 2A.5)

Scrapes land listings from 99.co Indonesia real estate portal
Third-tier fallback in multi-source scraping strategy
"""

import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from .base_scraper import BaseLandPriceScraper, ScrapedListing, ScrapeResult

logger = logging.getLogger(__name__)


class NinetyNineScraper(BaseLandPriceScraper):
    """
    Scraper for 99.co land listings (Indonesia)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.99.co"
    
    def get_source_name(self) -> str:
        return "99.co"
    
    def _scrape_live(self, region_name: str, max_listings: int) -> ScrapeResult:
        """
        Scrape live land prices from 99.co
        
        Args:
            region_name: Region to search (e.g., "Sleman Yogyakarta")
            max_listings: Maximum listings to scrape
            
        Returns:
            ScrapeResult with scraped listings
        """
        logger.info(f"Starting live scrape of 99.co for {region_name}")
        
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
            logger.warning(f"No listings found on 99.co for {region_name}")
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
        Build 99.co search URL for land in region
        
        Args:
            region_name: Region to search
            
        Returns:
            Formatted search URL
        """
        # 99.co uses format: https://www.99.co/id/jual/tanah/yogyakarta
        # Extract city/province from region name
        region_parts = region_name.lower().replace('-', ' ').split()
        
        # Try to identify province/city
        province = None
        for part in region_parts:
            if part in ['yogyakarta', 'jakarta', 'bandung', 'surabaya', 'semarang', 'bali']:
                province = part
                break
        
        if not province:
            # Try partial matches
            region_lower = ' '.join(region_parts)
            if 'yogya' in region_lower or 'sleman' in region_lower or 'bantul' in region_lower:
                province = 'yogyakarta'
            elif 'jakarta' in region_lower or 'tangerang' in region_lower or 'bekasi' in region_lower:
                province = 'jakarta'
            elif 'bandung' in region_lower:
                province = 'bandung'
            elif 'surabaya' in region_lower or 'sidoarjo' in region_lower:
                province = 'surabaya'
            elif 'semarang' in region_lower or 'solo' in region_lower:
                province = 'jawa-tengah'
            elif 'bali' in region_lower or 'denpasar' in region_lower:
                province = 'bali'
            else:
                province = 'jakarta'  # Default to Jakarta
        
        # 99.co URL format: /id/jual/tanah/{province}
        search_url = f"{self.base_url}/id/jual/tanah/{province}"
        
        return search_url
    
    def _parse_search_results(self, soup, region_name: str, max_listings: int) -> List[ScrapedListing]:
        """
        Parse search results page for land listings
        
        Args:
            soup: BeautifulSoup object of search results page
            region_name: Region name for context
            max_listings: Maximum listings to parse
            
        Returns:
            List of ScrapedListing objects
        """
        listings = []
        
        # 99.co uses various card/listing selectors
        # Try multiple selectors to maximize compatibility
        listing_cards = (
            soup.find_all('div', class_=re.compile(r'listing.*card', re.I)) or
            soup.find_all('div', class_=re.compile(r'property.*card', re.I)) or
            soup.find_all('article', class_=re.compile(r'listing', re.I)) or
            soup.find_all('div', {'data-testid': re.compile(r'listing', re.I)})
        )
        
        logger.info(f"Found {len(listing_cards)} potential listing cards on 99.co")
        
        for card in listing_cards[:max_listings]:
            try:
                listing = self._parse_listing_card(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse listing card: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(listings)} listings from 99.co")
        return listings
    
    def _parse_listing_card(self, card) -> Optional[ScrapedListing]:
        """
        Parse individual listing card
        
        Args:
            card: BeautifulSoup element for listing card
            
        Returns:
            ScrapedListing or None if parsing fails
        """
        try:
            # Extract price (try multiple formats)
            price_elem = (
                card.find(class_=re.compile(r'price', re.I)) or
                card.find('span', string=re.compile(r'Rp|IDR', re.I)) or
                card.find('div', {'data-testid': 'listing-price'})
            )
            
            if not price_elem:
                logger.debug("No price element found in card")
                return None
            
            price_text = price_elem.get_text(strip=True)
            total_price = self._extract_price(price_text)
            
            if total_price == 0:
                logger.debug(f"Could not extract price from: {price_text}")
                return None
            
            # Extract size (land area)
            size_elem = (
                card.find(class_=re.compile(r'land.*area|size', re.I)) or
                card.find('span', string=re.compile(r'm²|m2|sqm', re.I)) or
                card.find('div', {'data-testid': 'land-area'})
            )
            
            size_m2 = 0
            if size_elem:
                size_text = size_elem.get_text(strip=True)
                size_m2 = self._extract_size(size_text)
            
            # If no size found, try to find it in the entire card text
            if size_m2 == 0:
                card_text = card.get_text()
                size_match = re.search(r'(\d+[\d,]*)\s*m[²2]', card_text, re.I)
                if size_match:
                    size_str = size_match.group(1).replace(',', '')
                    try:
                        size_m2 = float(size_str)
                    except ValueError:
                        pass
            
            # Skip if no size (can't calculate price per m²)
            if size_m2 == 0:
                logger.debug("No size found, skipping listing")
                return None
            
            # Calculate price per m²
            price_per_m2 = total_price / size_m2
            
            # Extract location
            location_elem = (
                card.find(class_=re.compile(r'location|address', re.I)) or
                card.find('span', class_=re.compile(r'area|district', re.I)) or
                card.find('div', {'data-testid': 'listing-location'})
            )
            
            location = location_elem.get_text(strip=True) if location_elem else "Unknown Location"
            
            # Extract URL
            link_elem = card.find('a', href=True)
            listing_url = link_elem['href'] if link_elem else ""
            if listing_url and not listing_url.startswith('http'):
                listing_url = self.base_url + listing_url
            
            # Extract date (if available)
            date_elem = card.find(class_=re.compile(r'date|time', re.I))
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
            
        except Exception as e:
            logger.debug(f"Error parsing listing card: {e}")
            return None
    
    def _extract_price(self, price_text: str) -> float:
        """
        Extract numeric price from text
        
        Args:
            price_text: Price text (e.g., "Rp 2.5 Miliar")
            
        Returns:
            Price in IDR
        """
        if not price_text:
            return 0
        
        # Remove currency symbols and whitespace
        price_clean = price_text.replace('Rp', '').replace('IDR', '').strip()
        
        # Handle Indonesian number format
        # Miliar = billion (10^9), Juta = million (10^6), Ribu = thousand (10^3)
        multiplier = 1
        if 'miliar' in price_clean.lower() or 'billion' in price_clean.lower():
            multiplier = 1_000_000_000
            price_clean = re.sub(r'miliar|billion', '', price_clean, flags=re.I)
        elif 'juta' in price_clean.lower() or 'million' in price_clean.lower():
            multiplier = 1_000_000
            price_clean = re.sub(r'juta|million', '', price_clean, flags=re.I)
        elif 'ribu' in price_clean.lower() or 'thousand' in price_clean.lower():
            multiplier = 1_000
            price_clean = re.sub(r'ribu|thousand', '', price_clean, flags=re.I)
        
        # Extract number (handle decimal point/comma as decimal separator)
        number_match = re.search(r'(\d+[.,]?\d*)', price_clean.replace(',', '.'))
        if number_match:
            try:
                number = float(number_match.group(1).replace(',', '.'))
                return number * multiplier
            except ValueError:
                return 0
        
        return 0
    
    def _extract_size(self, size_text: str) -> float:
        """
        Extract land size from text
        
        Args:
            size_text: Size text (e.g., "250 m²")
            
        Returns:
            Size in square meters
        """
        if not size_text:
            return 0
        
        # Extract number
        size_match = re.search(r'(\d+[\d,]*)', size_text.replace('.', ','))
        if size_match:
            try:
                size_str = size_match.group(1).replace(',', '')
                return float(size_str)
            except ValueError:
                return 0
        
        return 0


# Standalone test
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = NinetyNineScraper(cache_expiry_hours=24)
    
    # Test region
    test_region = "Sleman Yogyakarta"
    
    print(f"\n{'='*70}")
    print(f"TESTING 99.CO SCRAPER")
    print(f"{'='*70}")
    print(f"Region: {test_region}\n")
    
    # Get price data
    result = scraper.get_price_data(test_region, max_listings=10)
    
    print(f"\n{'='*70}")
    print(f"RESULT")
    print(f"{'='*70}")
    print(f"Success: {result.success}")
    print(f"Source: {result.source}")
    print(f"Listing Count: {result.listing_count}")
    
    if result.success:
        print(f"Average Price: Rp {result.average_price_per_m2:,.0f}/m²")
        print(f"Median Price: Rp {result.median_price_per_m2:,.0f}/m²")
        print(f"Scraped At: {result.scraped_at}")
        
        if result.listings:
            print(f"\nSample Listings (top 3):")
            for i, listing in enumerate(result.listings[:3], 1):
                print(f"\n  {i}. {listing.location}")
                print(f"     Price: Rp {listing.price_per_m2:,.0f}/m²")
                print(f"     Size: {listing.size_m2:,.0f} m²")
                print(f"     Total: Rp {listing.total_price:,.0f}")
    else:
        print(f"Error: {result.error_message}")
