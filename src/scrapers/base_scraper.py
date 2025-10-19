"""
Base web scraper for Indonesian real estate sites
CloudClearingAPI - October 19, 2025

Provides caching, rate limiting, user-agent rotation, and error handling
"""

import logging
import time
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedListing:
    """Single real estate listing"""
    price_per_m2: float  # IDR
    total_price: float  # IDR
    size_m2: float
    location: str
    listing_date: Optional[str]
    source_url: str
    listing_type: str  # 'land', 'residential', etc.


@dataclass
class ScrapeResult:
    """Result of a scraping operation"""
    region_name: str
    average_price_per_m2: float
    median_price_per_m2: float
    listing_count: int
    listings: List[ScrapedListing]
    source: str  # 'lamudi', 'rumah.com', etc.
    scraped_at: datetime
    success: bool
    error_message: Optional[str] = None


class BaseLandPriceScraper(ABC):
    """
    Base class for real estate scrapers with caching and rate limiting
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_expiry_hours: int = 24):
        """
        Initialize scraper with caching
        
        Args:
            cache_dir: Directory to store cached results
            cache_expiry_hours: Hours before cache expires
        """
        self.cache_dir = cache_dir or Path('output/scraper_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry_hours = cache_expiry_hours
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # seconds between requests
        
        # User agents for rotation (avoid detection)
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Request timeout
        self.request_timeout = 15  # seconds
        
        logger.info(f"Initialized {self.__class__.__name__} with cache at {self.cache_dir}")
    
    def get_price_data(self, region_name: str, max_listings: int = 20) -> ScrapeResult:
        """
        Get land price data for a region with cache-first approach
        
        Args:
            region_name: Name of region to search
            max_listings: Maximum number of listings to scrape
            
        Returns:
            ScrapeResult with average prices or cached data
        """
        # Step 1: Check cache first
        cached_result = self._load_from_cache(region_name)
        if cached_result:
            logger.info(f"Using cached price data for {region_name} (age: {self._get_cache_age(cached_result):.1f}h)")
            return cached_result
        
        # Step 2: Attempt live scraping
        logger.info(f"No valid cache found. Attempting live scrape for {region_name}")
        try:
            scrape_result = self._scrape_live(region_name, max_listings)
            
            if scrape_result.success:
                # Cache successful result
                self._save_to_cache(scrape_result)
                logger.info(f"Successfully scraped {scrape_result.listing_count} listings for {region_name}")
                return scrape_result
            else:
                logger.warning(f"Live scrape failed for {region_name}: {scrape_result.error_message}")
                return scrape_result
                
        except Exception as e:
            logger.error(f"Exception during scraping for {region_name}: {str(e)}")
            return ScrapeResult(
                region_name=region_name,
                average_price_per_m2=0,
                median_price_per_m2=0,
                listing_count=0,
                listings=[],
                source=self.get_source_name(),
                scraped_at=datetime.now(),
                success=False,
                error_message=str(e)
            )
    
    @abstractmethod
    def _scrape_live(self, region_name: str, max_listings: int) -> ScrapeResult:
        """
        Implement site-specific scraping logic
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source name (e.g., 'lamudi', 'rumah.com')"""
        pass
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """
        Make HTTP request with rate limiting and user-agent rotation
        
        Args:
            url: URL to request
            
        Returns:
            BeautifulSoup object or None if failed
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        # Random user agent
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            self.last_request_time = time.time()
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.debug(f"Successfully fetched {url}")
            return soup
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None
    
    def _load_from_cache(self, region_name: str) -> Optional[ScrapeResult]:
        """
        Load cached scrape result if exists and not expired
        
        Args:
            region_name: Name of region
            
        Returns:
            ScrapeResult if valid cache exists, None otherwise
        """
        cache_file = self._get_cache_filename(region_name)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check expiry
            scraped_at = datetime.fromisoformat(data['scraped_at'])
            age_hours = (datetime.now() - scraped_at).total_seconds() / 3600
            
            if age_hours > self.cache_expiry_hours:
                logger.debug(f"Cache expired for {region_name} (age: {age_hours:.1f}h)")
                return None
            
            # Reconstruct ScrapeResult
            listings = [ScrapedListing(**listing) for listing in data['listings']]
            
            result = ScrapeResult(
                region_name=data['region_name'],
                average_price_per_m2=data['average_price_per_m2'],
                median_price_per_m2=data['median_price_per_m2'],
                listing_count=data['listing_count'],
                listings=listings,
                source=data['source'],
                scraped_at=scraped_at,
                success=data['success'],
                error_message=data.get('error_message')
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to load cache for {region_name}: {str(e)}")
            return None
    
    def _save_to_cache(self, result: ScrapeResult):
        """
        Save scrape result to cache
        
        Args:
            result: ScrapeResult to cache
        """
        cache_file = self._get_cache_filename(result.region_name)
        
        try:
            # Convert to dict
            data = {
                'region_name': result.region_name,
                'average_price_per_m2': result.average_price_per_m2,
                'median_price_per_m2': result.median_price_per_m2,
                'listing_count': result.listing_count,
                'listings': [asdict(listing) for listing in result.listings],
                'source': result.source,
                'scraped_at': result.scraped_at.isoformat(),
                'success': result.success,
                'error_message': result.error_message
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Cached result for {result.region_name} at {cache_file}")
            
        except Exception as e:
            logger.error(f"Failed to save cache for {result.region_name}: {str(e)}")
    
    def _get_cache_filename(self, region_name: str) -> Path:
        """Get cache filename for a region"""
        # Sanitize region name for filename
        safe_name = region_name.lower().replace(' ', '_').replace('/', '_')
        return self.cache_dir / f"{self.get_source_name()}_{safe_name}.json"
    
    def _get_cache_age(self, result: ScrapeResult) -> float:
        """Get age of cached result in hours"""
        age = datetime.now() - result.scraped_at
        return age.total_seconds() / 3600
    
    def _calculate_statistics(self, listings: List[ScrapedListing]) -> Dict[str, float]:
        """
        Calculate average and median prices from listings
        
        Args:
            listings: List of scraped listings
            
        Returns:
            Dict with 'average' and 'median' prices per m²
        """
        if not listings:
            return {'average': 0, 'median': 0}
        
        prices = [listing.price_per_m2 for listing in listings if listing.price_per_m2 > 0]
        
        if not prices:
            return {'average': 0, 'median': 0}
        
        average = sum(prices) / len(prices)
        
        # Calculate median
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        if n % 2 == 0:
            median = (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
        else:
            median = sorted_prices[n//2]
        
        return {'average': average, 'median': median}
    
    def clear_cache(self, region_name: Optional[str] = None):
        """
        Clear cached data
        
        Args:
            region_name: If provided, clear only this region. Otherwise clear all.
        """
        if region_name:
            cache_file = self._get_cache_filename(region_name)
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for {region_name}")
        else:
            for cache_file in self.cache_dir.glob(f"{self.get_source_name()}_*.json"):
                cache_file.unlink()
            logger.info(f"Cleared all cache for {self.get_source_name()}")
