"""
Indonesian Infrastructure News Scraper
CloudClearingAPI - v2.10

Scrapes development news from Indonesian media sources to detect
announced infrastructure projects, government contracts, and SEZs
near monitored investment regions.

Sources (priority order):
1. Jakarta Post (English, RSS + HTML)
2. Kompas (Indonesian, RSS + HTML)
3. Antara News (English, official wire service)

Output: List of NewsArticle objects matched to regions.
"""

import logging
import json
import re
import hashlib
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """A single news article relevant to infrastructure development"""
    title: str
    source: str              # 'jakarta_post', 'kompas', 'antara'
    url: str
    date: Optional[str]      # ISO date string
    snippet: str             # First 200 chars of article body
    matched_keywords: List[str]
    matched_region: str      # Region name this was matched to
    sentiment: str           # 'positive', 'negative', 'neutral'
    relevance_score: float   # 0.0–1.0


# Keywords for development activity detection (English + Indonesian)
INFRA_KEYWORDS = {
    # Transport infrastructure
    'toll road': 0.9, 'jalan tol': 0.9, 'highway': 0.7, 'expressway': 0.8,
    'airport': 0.9, 'bandara': 0.9, 'runway': 0.7,
    'port': 0.8, 'pelabuhan': 0.8, 'seaport': 0.8,
    'railway': 0.8, 'kereta api': 0.8, 'high-speed rail': 0.9, 'kereta cepat': 0.9,
    'mrt': 0.7, 'lrt': 0.7, 'brt': 0.6, 'transjakarta': 0.5,
    
    # Economic zones
    'sez': 0.9, 'special economic zone': 0.9, 'kawasan ekonomi khusus': 0.9,
    'industrial park': 0.8, 'kawasan industri': 0.8, 'industrial estate': 0.8,
    'free trade zone': 0.7, 'bonded zone': 0.6,
    
    # Construction & development
    'construction': 0.6, 'pembangunan': 0.6, 'development project': 0.7,
    'proyek strategis nasional': 0.9, 'psn': 0.8,
    'groundbreaking': 0.8, 'peresmian': 0.7,
    'new city': 0.7, 'kota baru': 0.7,
    'ikn': 0.6, 'nusantara': 0.6,  # New capital
    
    # Government & finance
    'government contract': 0.7, 'kontrak pemerintah': 0.7,
    'tender': 0.6, 'apbn': 0.6,
    'foreign investment': 0.7, 'investasi asing': 0.7, 'fdi': 0.7,
    'billion dollar': 0.8, 'miliar dolar': 0.8, 'trillion rupiah': 0.8, 'triliun rupiah': 0.8,
    
    # Real estate development
    'property development': 0.7, 'real estate': 0.5,
    'housing development': 0.6, 'perumahan': 0.5,
    'hotel': 0.4, 'resort': 0.5, 'tourism': 0.4, 'pariwisata': 0.4,
}

# Negative keywords (reduce score)
NEGATIVE_KEYWORDS = {
    'cancel': -0.5, 'batal': -0.5, 'cancelled': -0.5, 'dibatalkan': -0.5,
    'delay': -0.3, 'tunda': -0.3, 'delayed': -0.3, 'ditunda': -0.3,
    'dispute': -0.4, 'sengketa': -0.4, 'lawsuit': -0.4,
    'corruption': -0.5, 'korupsi': -0.5,
    'flood': -0.3, 'banjir': -0.3, 'landslide': -0.3, 'longsor': -0.3,
    'protest': -0.3, 'demonstrasi': -0.3,
}

# City → region mapping (reuses Lamudi's pattern)
CITY_TO_REGIONS = {
    'jakarta': ['jakarta_north_sprawl', 'jakarta_east_industrial', 'jakarta_south_premium', 'jakarta_west_tangerang'],
    'tangerang': ['tangerang_bsd_corridor', 'tangerang_industrial_corridor', 'jakarta_west_tangerang'],
    'bekasi': ['bekasi_east_expansion'],
    'bandung': ['bandung_north_expansion', 'bandung_south_development'],
    'yogyakarta': ['yogyakarta_urban', 'yogyakarta_periurban'],
    'jogja': ['yogyakarta_urban', 'yogyakarta_periurban'],
    'semarang': ['semarang_port_expansion', 'semarang_south_hills'],
    'solo': ['solo_raya_expansion'],
    'surakarta': ['solo_raya_expansion'],
    'surabaya': ['surabaya_east_industrial', 'surabaya_south_expansion', 'surabaya_west_corridor'],
    'malang': ['malang_batu_corridor'],
    'banyuwangi': ['banyuwangi_ferry_corridor'],
    'jember': ['jember_southern_coast'],
    'probolinggo': ['probolinggo_bromo_gateway'],
    'tegal': ['tegal_brebes_coastal'],
    'pekalongan': ['pekalongan_batang_corridor'],
    'purwokerto': ['purwokerto_south_expansion'],
    'cilacap': ['cilacap_industrial_port'],
    'serang': ['serang_banten_gateway'],
    'cilegon': ['cilegon_industrial_port'],
    'denpasar': ['denpasar_north_expansion'],
    'bali': ['denpasar_north_expansion'],
    'java': [],  # too broad to match specific region
    'jawa': [],
}


class NewsScraper:
    """
    Scrapes Indonesian infrastructure news and matches articles to regions.

    Uses a 7-day cache to avoid redundant requests.
    Adopts base_scraper patterns: User-Agent rotation, retry with backoff.
    """

    # User-Agent rotation pool (matches base_scraper.py pattern)
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    def __init__(self, cache_dir: str = "./cache/news", cache_ttl_days: int = 7,
                 max_retries: int = 2, request_timeout: int = 15):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(days=cache_ttl_days)
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

        logger.info(f"📰 News Scraper initialized (cache TTL: {cache_ttl_days}d, retries: {max_retries})")
    
    # ─── CACHE ───────────────────────────────────────────────────
    
    def _cache_key(self, source: str) -> str:
        week_id = datetime.now().strftime("%Y_W%U")
        return hashlib.md5(f"news_{source}_{week_id}".encode()).hexdigest()
    
    def _check_cache(self, source: str) -> Optional[List[Dict]]:
        key = self._cache_key(source)
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        if age > self.cache_ttl:
            path.unlink(missing_ok=True)
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            logger.info(f"✅ News cache HIT for {source} ({age.total_seconds()/3600:.0f}h old, {len(data)} articles)")
            return data
        except Exception:
            path.unlink(missing_ok=True)
            return None
    
    def _save_cache(self, source: str, articles: List[Dict]) -> None:
        key = self._cache_key(source)
        path = self.cache_dir / f"{key}.json"
        try:
            with open(path, 'w') as f:
                json.dump(articles, f, indent=2, default=str)
            logger.info(f"💾 News cache SAVED: {source} ({len(articles)} articles)")
        except Exception as e:
            logger.warning(f"News cache save failed for {source}: {e}")
    
    # ─── HTTP HELPERS ─────────────────────────────────────────────

    def _get_with_retry(self, url: str) -> Optional[requests.Response]:
        """GET request with User-Agent rotation and exponential backoff retry."""
        for attempt in range(self.max_retries + 1):
            try:
                self.session.headers['User-Agent'] = random.choice(self.USER_AGENTS)
                resp = self.session.get(url, timeout=self.request_timeout)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"HTTP {resp.status_code} for {url} (attempt {attempt + 1})")
            except requests.ConnectionError as e:
                logger.warning(f"Connection error for {url} (attempt {attempt + 1}): {e}")
            except requests.Timeout:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
            except requests.RequestException as e:
                logger.warning(f"Request error for {url} (attempt {attempt + 1}): {e}")

            if attempt < self.max_retries:
                backoff = min(30, (2 ** attempt) + random.uniform(0.5, 1.5))
                time.sleep(backoff)

        logger.warning(f"All {self.max_retries + 1} attempts failed for {url}")
        return None

    # ─── SCRAPING ────────────────────────────────────────────────

    def scrape_all_sources(self) -> List[Dict[str, Any]]:
        """Scrape all news sources and return raw article dicts."""
        all_articles = []
        
        for source_name, scrape_fn in [
            ('jakarta_post', self._scrape_jakarta_post),
            ('kompas', self._scrape_kompas),
            ('antara', self._scrape_antara),
        ]:
            cached = self._check_cache(source_name)
            if cached is not None:
                all_articles.extend(cached)
                continue
            
            try:
                articles = scrape_fn()
                self._save_cache(source_name, articles)
                all_articles.extend(articles)
                time.sleep(random.uniform(1.0, 2.5))  # politeness delay
            except Exception as e:
                logger.warning(f"📰 {source_name} scrape failed: {e}")
        
        logger.info(f"📰 Total raw articles: {len(all_articles)}")
        return all_articles
    
    def _scrape_jakarta_post(self) -> List[Dict]:
        """Scrape infrastructure articles from The Jakarta Post."""
        articles = []
        urls = [
            "https://www.thejakartapost.com/indonesia",
            "https://www.thejakartapost.com/business",
        ]
        
        seen_urls = set()
        for url in urls:
            try:
                resp = self._get_with_retry(url)
                if not resp:
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')

                # Find article links — Jakarta Post uses various card patterns
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    title_text = link.get_text(strip=True)

                    # Only article links (contain /news/ or /indonesia/ or /business/)
                    if not title_text or len(title_text) < 20:
                        continue
                    if not any(seg in href for seg in ['/news/', '/indonesia/', '/business/']):
                        continue

                    full_url = href if href.startswith('http') else f"https://www.thejakartapost.com{href}"
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    # Check if title matches any infrastructure keyword
                    matched = self._match_keywords(title_text)
                    if not matched:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'jakarta_post',
                        'url': full_url,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                    })

                logger.info(f"📰 Jakarta Post ({url.split('/')[-1]}): {len(articles)} infrastructure articles")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Jakarta Post scrape error ({url}): {e}")

        return articles[:30]  # Cap at 30 articles
    
    def _scrape_kompas(self) -> List[Dict]:
        """Scrape infrastructure articles from Kompas."""
        articles = []
        urls = [
            "https://properti.kompas.com/",
            "https://money.kompas.com/",
        ]
        
        seen_urls = set()
        for url in urls:
            try:
                resp = self._get_with_retry(url)
                if not resp:
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')

                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    title_text = link.get_text(strip=True)

                    if not title_text or len(title_text) < 15:
                        continue
                    if 'kompas.com/read' not in href:
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    matched = self._match_keywords(title_text)
                    if not matched:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'kompas',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                    })

                logger.info(f"📰 Kompas ({url.split('/')[-2]}): found matches")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Kompas scrape error: {e}")

        return articles[:30]
    
    def _scrape_antara(self) -> List[Dict]:
        """Scrape infrastructure articles from Antara News (English)."""
        articles = []
        urls = [
            "https://en.antaranews.com/economy",
            "https://en.antaranews.com/business",
        ]
        
        seen_urls = set()
        for url in urls:
            try:
                resp = self._get_with_retry(url)
                if not resp:
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')

                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    title_text = link.get_text(strip=True)

                    if not title_text or len(title_text) < 20:
                        continue
                    if 'antaranews.com/news' not in href:
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    matched = self._match_keywords(title_text)
                    if not matched:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'antara',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                    })

                logger.info(f"📰 Antara ({url.split('/')[-1]}): found matches")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Antara scrape error: {e}")

        return articles[:30]
    
    # ─── MATCHING ────────────────────────────────────────────────
    
    def _match_keywords(self, text: str) -> List[str]:
        """Check which infrastructure keywords appear in text."""
        text_lower = text.lower()
        matched = []
        for keyword in INFRA_KEYWORDS:
            if keyword in text_lower:
                matched.append(keyword)
        return matched
    
    def match_articles_to_region(self, articles: List[Dict], region_name: str) -> List[NewsArticle]:
        """
        Match raw articles to a specific region by checking if the article
        mentions any city associated with that region.
        
        Args:
            articles: Raw article dicts from scrape_all_sources()
            region_name: Region to match (e.g., 'yogyakarta_urban')
            
        Returns:
            List of NewsArticle objects matched to this region
        """
        matched = []
        
        # Build set of city names that map to this region
        target_cities = set()
        for city, regions in CITY_TO_REGIONS.items():
            if region_name in regions:
                target_cities.add(city)
        
        # Also extract city from region name directly
        region_tokens = region_name.lower().split('_')
        for token in region_tokens:
            if token in CITY_TO_REGIONS:
                target_cities.add(token)
        
        if not target_cities:
            # Fallback: use first token of region name
            target_cities.add(region_tokens[0])
        
        for article in articles:
            text = f"{article['title']} {article.get('snippet', '')}".lower()
            
            # Check if any target city is mentioned
            city_match = any(city in text for city in target_cities)
            if not city_match:
                continue
            
            # Determine sentiment
            sentiment, neg_count = self._analyze_sentiment(text)
            
            # Calculate relevance score
            keyword_scores = [INFRA_KEYWORDS.get(kw, 0.5) for kw in article.get('matched_keywords', [])]
            relevance = min(1.0, sum(keyword_scores) / max(1, len(keyword_scores)))
            if neg_count > 0:
                relevance *= 0.5  # Heavily discount negative articles
            
            matched.append(NewsArticle(
                title=article['title'],
                source=article['source'],
                url=article['url'],
                date=article.get('date'),
                snippet=article.get('snippet', '')[:200],
                matched_keywords=article.get('matched_keywords', []),
                matched_region=region_name,
                sentiment=sentiment,
                relevance_score=round(relevance, 3),
            ))
        
        # Sort by relevance
        matched.sort(key=lambda a: a.relevance_score, reverse=True)
        
        if matched:
            logger.info(f"📰 {region_name}: {len(matched)} news articles matched "
                       f"(top: '{matched[0].title[:60]}...')")
        
        return matched
    
    def _analyze_sentiment(self, text: str) -> Tuple[str, int]:
        """Simple keyword-based sentiment analysis."""
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
        pos_count = sum(1 for kw in INFRA_KEYWORDS if kw in text)
        
        if neg_count >= 2 or (neg_count > 0 and pos_count <= 1):
            return 'negative', neg_count
        elif pos_count >= 2:
            return 'positive', neg_count
        else:
            return 'neutral', neg_count
