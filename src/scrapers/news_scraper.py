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
4. Detik (finance.detik.com — infrastructure, properti, ekonomi-bisnis)
5. CNBC Indonesia (cnbcindonesia.com/news — broad business/infra wire)

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


# Keywords for development activity detection (English + Indonesian).
# Expanded 2026-04-26: previous list missed common Indonesian-press shorthand
# (groundbreaking ceremonies, ministerial approvals, infra investment) which
# was producing 0 catalyst boosts despite real news coverage.
INFRA_KEYWORDS = {
    # Transport infrastructure
    'toll road': 0.9, 'jalan tol': 0.9, 'tol ': 0.7, 'highway': 0.7, 'expressway': 0.8,
    'airport': 0.9, 'bandara': 0.9, 'runway': 0.7, 'landasan pacu': 0.7,
    'port': 0.8, 'pelabuhan': 0.8, 'seaport': 0.8, 'terminal peti kemas': 0.8,
    'patimban': 0.9,  # specific megaport (so an article merely naming Patimban scores)
    'railway': 0.8, 'kereta api': 0.8, 'high-speed rail': 0.9, 'kereta cepat': 0.9,
    'whoosh': 0.8,  # Jakarta-Bandung HSR brand
    'mrt': 0.7, 'lrt': 0.7, 'brt': 0.6, 'transjakarta': 0.5,
    'jalan baru': 0.7, 'flyover': 0.7, 'jembatan': 0.6,

    # Economic zones
    'sez': 0.9, 'special economic zone': 0.9, 'kawasan ekonomi khusus': 0.9, 'kek ': 0.9,
    'industrial park': 0.8, 'kawasan industri': 0.8, 'industrial estate': 0.8,
    'free trade zone': 0.7, 'bonded zone': 0.6,

    # Construction & development (broadened — these matter most)
    'construction': 0.6, 'pembangunan': 0.6, 'dibangun': 0.6,
    'development project': 0.7, 'proyek pembangunan': 0.7,
    'proyek strategis nasional': 0.9, 'psn': 0.8,
    'groundbreaking': 0.8, 'peresmian': 0.8, 'diresmikan': 0.8, 'pencanangan': 0.7,
    'new city': 0.7, 'kota baru': 0.7,
    'ikn': 0.6, 'nusantara': 0.5,  # IKN/new capital (multiplier diluted — it's everywhere)

    # Government & finance
    'government contract': 0.7, 'kontrak pemerintah': 0.7,
    'tender': 0.6, 'apbn': 0.6, 'pemerintah pusat': 0.5,
    'foreign investment': 0.7, 'investasi asing': 0.7, 'fdi': 0.7,
    'billion dollar': 0.8, 'miliar dolar': 0.8, 'trillion rupiah': 0.8, 'triliun rupiah': 0.8,
    'investasi': 0.5, 'modal asing': 0.6,
    'kementerian pupr': 0.7, 'kementerian perhubungan': 0.7, 'kemenhub': 0.7, 'kemenperin': 0.7,

    # Real estate development
    'property development': 0.7, 'real estate': 0.5,
    'housing development': 0.6, 'perumahan': 0.5,
    'hotel': 0.4, 'resort': 0.5, 'tourism': 0.4, 'pariwisata': 0.4,
    'wisata': 0.4, 'destinasi wisata': 0.5,
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
    'jakarta': ['jakarta_north_sprawl', 'jakarta_south_suburbs'],
    'tangerang': ['tangerang_bsd_corridor'],
    'bekasi': ['bekasi_industrial_belt'],
    'cikarang': ['cikarang_mega_industrial'],
    'karawang': ['karawang_industrial_corridor'],
    'bandung': ['bandung_north_expansion', 'bandung_east_tech_corridor'],
    'yogyakarta': ['yogyakarta_urban_core', 'yogyakarta_kulon_progo_airport'],
    'jogja': ['yogyakarta_urban_core', 'yogyakarta_kulon_progo_airport'],
    'semarang': ['semarang_port_expansion', 'semarang_south_urban'],
    'solo': ['solo_raya_expansion'],
    'surakarta': ['solo_raya_expansion'],
    'surabaya': ['surabaya_west_expansion', 'surabaya_east_industrial'],
    'gresik': ['gresik_port_industrial'],
    'sidoarjo': ['sidoarjo_delta_development'],
    'malang': ['malang_south_highland'],
    'banyuwangi': ['banyuwangi_ferry_corridor'],
    'jember': ['jember_southern_coast'],
    'probolinggo': ['probolinggo_bromo_gateway'],
    'tegal': ['tegal_brebes_coastal'],
    'purwokerto': ['purwokerto_south_expansion'],
    'serang': ['serang_cilegon_industrial'],
    'cilegon': ['serang_cilegon_industrial'],
    'merak': ['merak_port_corridor'],
    'anyer': ['anyer_carita_coastal'],
    'cirebon': ['cirebon_port_industrial'],
    # v2.19.0: subang_patimban_megaport split — news routes to both halves
    # (subang token is too coarse to disambiguate from headlines alone).
    # Patimban-specific stories route preferentially to industrial sub-region.
    'subang': ['subang_patimban_industrial', 'subang_pantura_agrarian'],
    'patimban': ['subang_patimban_industrial'],
    'smartpolitan': ['subang_patimban_industrial'],
    'pantura': ['subang_pantura_agrarian'],
    'bogor': ['bogor_puncak_highland'],
    'magelang': ['magelang_borobudur_corridor'],
    'borobudur': ['magelang_borobudur_corridor'],
    'batang': ['batang_industrial_sez'],
    'labuan bajo': ['labuan_bajo_komodo_gateway'],
    'komodo': ['labuan_bajo_komodo_gateway'],
    'nusa dua': ['nusa_dua_bukit_peninsula'],
    'jimbaran': ['nusa_dua_bukit_peninsula'],
    'uluwatu': ['nusa_dua_bukit_peninsula'],
    'padang': ['padang_urban_coastal'],
    'banda aceh': ['banda_aceh_reconstruction'],
    'senggigi': ['lombok_senggigi_coast'],
    'kupang': ['kupang_urban_development'],
    # v2.19.0 — Bitung sub-region routing. KEK SEZ headlines route to the
    # SEZ side; bare 'bitung' covers both port and SEZ.
    'bitung': ['bitung_port_corridor', 'bitung_kek_sez_industrial'],
    'aertembaga': ['bitung_port_corridor'],
    'kek bitung': ['bitung_kek_sez_industrial'],
    'tanjung merah': ['bitung_kek_sez_industrial'],
    # v2.19.0 — Balikpapan sub-region routing. Kariangau (heavy industrial,
    # north) vs Sepinggan/Selatan (residential/airport, south).
    'balikpapan': ['balikpapan_kariangau_industrial', 'balikpapan_selatan_commercial'],
    'kariangau': ['balikpapan_kariangau_industrial'],
    'sepinggan': ['balikpapan_selatan_commercial'],

    # Province-level matching (articles mentioning province match all regions in it)
    'jawa barat': ['bandung_north_expansion', 'bandung_east_tech_corridor', 'cirebon_port_industrial',
                   'subang_patimban_industrial', 'subang_pantura_agrarian', 'bogor_puncak_highland', 'karawang_industrial_corridor'],
    'west java': ['bandung_north_expansion', 'bandung_east_tech_corridor', 'cirebon_port_industrial',
                  'subang_patimban_industrial', 'subang_pantura_agrarian', 'bogor_puncak_highland', 'karawang_industrial_corridor'],
    'jawa tengah': ['semarang_port_expansion', 'semarang_south_urban', 'solo_raya_expansion',
                    'tegal_brebes_coastal', 'purwokerto_south_expansion', 'magelang_borobudur_corridor',
                    'batang_industrial_sez'],
    'central java': ['semarang_port_expansion', 'semarang_south_urban', 'solo_raya_expansion',
                     'tegal_brebes_coastal', 'purwokerto_south_expansion', 'magelang_borobudur_corridor',
                     'batang_industrial_sez'],
    'jawa timur': ['surabaya_west_expansion', 'surabaya_east_industrial', 'gresik_port_industrial',
                   'sidoarjo_delta_development', 'malang_south_highland', 'banyuwangi_ferry_corridor',
                   'probolinggo_bromo_gateway', 'jember_southern_coast'],
    'east java': ['surabaya_west_expansion', 'surabaya_east_industrial', 'gresik_port_industrial',
                  'sidoarjo_delta_development', 'malang_south_highland', 'banyuwangi_ferry_corridor',
                  'probolinggo_bromo_gateway', 'jember_southern_coast'],
    'banten': ['serang_cilegon_industrial', 'merak_port_corridor', 'anyer_carita_coastal',
               'tangerang_bsd_corridor'],
    'diy': ['yogyakarta_urban_core', 'yogyakarta_kulon_progo_airport', 'magelang_borobudur_corridor'],
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

    def __init__(self, cache_dir: str = "./cache/news", cache_ttl_days: int = 2,
                 max_retries: int = 2, request_timeout: int = 15):
        # Default TTL lowered from 7d → 2d in 2026-04-25: weekly runs were
        # hitting the same 6-day-old 12-article cache and producing 0 region
        # matches. 2d ensures the news pulled is at most one run stale.
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(days=cache_ttl_days)
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            # 'br' (brotli) omitted — requests can't decode brotli without the
            # `brotli` pip package; an undecoded body silently produces garbage
            # HTML with 0 tags. Caught 2026-04-25 (Antara news = 0 articles).
            'Accept-Encoding': 'gzip, deflate',
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
            ('detik_infra', self._scrape_detik_infrastructure),
            ('cnbc_indonesia', self._scrape_cnbc_indonesia),
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
            "https://www.thejakartapost.com/business/economy",
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

                    # Keep article if it matches an infrastructure keyword OR
                    # mentions one of our target cities/regions directly.
                    matched = self._match_keywords(title_text)
                    cities = self._match_cities(title_text)
                    if not matched and not cities:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'jakarta_post',
                        'url': full_url,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                        'matched_cities': cities,
                    })

                logger.info(f"📰 Jakarta Post ({url.split('/')[-1]}): {len(articles)} infra/region articles so far")
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
            "https://www.kompas.com/jawa-tengah",
            "https://www.kompas.com/jawa-timur",
            "https://www.kompas.com/jawa-barat",
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
                    cities = self._match_cities(title_text)
                    if not matched and not cities:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'kompas',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                        'matched_cities': cities,
                    })

                logger.info(f"📰 Kompas ({url.split('/')[-2]}): {len(articles)} infra/region articles so far")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Kompas scrape error: {e}")

        return articles[:30]
    
    def _scrape_antara(self) -> List[Dict]:
        """Scrape infrastructure articles from Antara News.

        Antara's economy section publishes mostly commodity/financial news,
        which has near-zero infra-keyword density. Adding infrastructure-
        specific subsections (megapolitan, nasional, infografik) where toll
        roads, ports, airports actually get headline coverage.
        """
        articles = []
        urls = [
            "https://www.antaranews.com/ekonomi",
            "https://www.antaranews.com/ekonomi/bisnis",
            # /megapolitan returns 404 (site restructured); skipped.
            "https://www.antaranews.com/nasional",
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
                    # Accept absolute antaranews URLs or relative /berita/ paths
                    if 'antaranews.com/' not in href and not href.startswith('/berita/'):
                        continue
                    if href.startswith('/'):
                        href = 'https://www.antaranews.com' + href
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    matched = self._match_keywords(title_text)
                    cities = self._match_cities(title_text)
                    if not matched and not cities:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'antara',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                        'matched_cities': cities,
                    })

                logger.info(f"📰 Antara ({url.split('/')[-1]}): {len(articles)} infra/region articles so far")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Antara scrape error: {e}")

        return articles[:30]

    def _scrape_detik_infrastructure(self) -> List[Dict]:
        """Scrape infrastructure articles from finance.detik.com/infrastruktur.

        This is the highest-density real-infra-news source we found:
        live probe returned ~78 long-text headlines, 9 with infra keywords
        ("Tol Yogyakarta-Bawen", "KEK Batang", "LRT Jakarta", "Whoosh",
        "Pelabuhan Patimban"). These are the Indonesian-press project names
        the prior 3 sources (Jakarta Post / Kompas / Antara) were missing.
        """
        articles = []
        urls = [
            "https://finance.detik.com/infrastruktur",
            "https://finance.detik.com/properti",
            "https://www.detik.com/properti",
            # Added 2026-04-25: berita-ekonomi-bisnis returned 69 long-link
            # headlines on a probe with 4 infra hits — comparable density to
            # the dedicated /infrastruktur subsection.
            "https://finance.detik.com/berita-ekonomi-bisnis",
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

                    if not title_text or len(title_text) < 25:
                        continue
                    # Detik articles always have /d-{id}/ in the path
                    if 'detik.com' not in href or '/d-' not in href:
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    matched = self._match_keywords(title_text)
                    cities = self._match_cities(title_text)
                    if not matched and not cities:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'detik_infra',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                        'matched_cities': cities,
                    })

                logger.info(f"📰 Detik ({url.split('/')[-1]}): {len(articles)} infra/region articles so far")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"Detik scrape error ({url}): {e}")

        return articles[:30]

    def _scrape_cnbc_indonesia(self) -> List[Dict]:
        """Scrape infrastructure/business articles from CNBC Indonesia.

        Probe results (2026-04-25): cnbcindonesia.com/news returned 31 long-
        link headlines with 2 infra hits per page. Article URLs follow the
        pattern /news/<14-digit-stamp>-<digit>-<id>/<slug>. Lower density per
        page than Detik but covers macro/policy stories the others miss.
        """
        articles = []
        urls = [
            "https://www.cnbcindonesia.com/news",
            "https://www.cnbcindonesia.com/market",
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

                    if not title_text or len(title_text) < 25:
                        continue
                    # CNBC article URLs always carry /news/ or /market/ +
                    # a long timestamp-id segment.
                    if 'cnbcindonesia.com' not in href:
                        continue
                    if not re.search(r'/(news|market)/\d{8,}-', href):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Strip listing-card metadata that bleeds into link text:
                    # "News4 jam yang lalu", "Market2 hari yang lalu", etc.
                    title_text = re.sub(
                        r'(News|Market|Bisnis|Investment)\d+\s*(jam|menit|detik|hari)\s+yang\s+lalu$',
                        '', title_text, flags=re.IGNORECASE).strip()

                    matched = self._match_keywords(title_text)
                    cities = self._match_cities(title_text)
                    if not matched and not cities:
                        continue

                    articles.append({
                        'title': title_text[:200],
                        'source': 'cnbc_indonesia',
                        'url': href,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': title_text[:200],
                        'matched_keywords': matched,
                        'matched_cities': cities,
                    })

                logger.info(f"📰 CNBC Indonesia ({url.split('/')[-1]}): {len(articles)} infra/region articles so far")
                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.warning(f"CNBC Indonesia scrape error ({url}): {e}")

        return articles[:30]

    # ─── MATCHING ────────────────────────────────────────────────
    
    def _match_keywords(self, text: str) -> List[str]:
        """Check which infrastructure keywords appear in text (word boundary match)."""
        import re as _re
        text_lower = text.lower()
        matched = []
        for keyword in INFRA_KEYWORDS:
            # Use word boundaries to avoid false positives like "port" in "support"
            if _re.search(r'\b' + _re.escape(keyword) + r'\b', text_lower):
                matched.append(keyword)
        return matched

    # Indonesian stopwords + journalistic noise that adds nothing to topic identity
    _DEDUPE_STOPWORDS = frozenset({
        'di', 'ke', 'dan', 'yang', 'untuk', 'pada', 'dengan', 'dari',
        'oleh', 'akan', 'sebagai', 'jadi', 'lebih', 'sudah', 'masih',
        'tak', 'tidak', 'ada', 'itu', 'ini', 'juga', 'atau', 'bisa',
        'foto', 'video', 'live', 'breaking', 'news',
        'the', 'a', 'an', 'in', 'on', 'at', 'of', 'and', 'or', 'to',
    })

    @classmethod
    def _title_bigrams(cls, title: str) -> set:
        """Adjacent token bigrams from a normalized title.

        Bigrams (rather than unigrams) catch named-entity + event combos
        like "tabrakan kereta" or "bekasi timur" — paraphrased headlines
        about the same story share these multi-word phrases reliably even
        when single-word Jaccard is low (13–23% on our test corpus).
        """
        import re as _re
        cleaned = _re.sub(r"[^\w\s]", " ", title.lower())
        toks = [t for t in cleaned.split() if len(t) >= 4 and t not in cls._DEDUPE_STOPWORDS]
        return {f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)}

    @classmethod
    def _dedupe_articles(cls, articles: List["NewsArticle"], min_shared_bigrams: int = 2) -> List["NewsArticle"]:
        """Drop near-duplicate articles by shared title-bigram count.

        Two headlines are treated as duplicates when they share at least
        ``min_shared_bigrams`` 2-word phrases (post-stopword removal).

        The Apr 27 run pulled 9 articles for bekasi_industrial_belt all about
        the same train accident (different paraphrasings of the same event).
        Dedupe keeps the first occurrence in input order — relevance-sorted
        upstream means the highest-scoring framing wins.
        """
        kept: List["NewsArticle"] = []
        kept_bigram_sets: List[set] = []
        for art in articles:
            bigrams = cls._title_bigrams(art.title)
            if not bigrams:
                kept.append(art)
                kept_bigram_sets.append(bigrams)
                continue
            is_dup = any(
                len(bigrams & prev) >= min_shared_bigrams
                for prev in kept_bigram_sets if prev
            )
            if not is_dup:
                kept.append(art)
                kept_bigram_sets.append(bigrams)
        return kept

    def _match_cities(self, text: str) -> List[str]:
        """Return any CITY_TO_REGIONS keys mentioned in text (word-boundary).

        A headline that mentions one of our target cities/sub-regions is
        worth keeping even without a generic infrastructure keyword — the
        fact that a city we monitor is in the news IS the signal.
        """
        import re as _re
        text_lower = text.lower()
        return [city for city in CITY_TO_REGIONS
                if _re.search(r'\b' + _re.escape(city) + r'\b', text_lower)]
    
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

            # Check if any target city is mentioned (word boundary match).
            # Prefer the precomputed matched_cities (set at scrape time) but
            # fall back to live regex for old cached articles without it.
            import re as _re
            article_cities = article.get('matched_cities')
            if article_cities is not None:
                city_match = bool(set(article_cities) & target_cities)
            else:
                city_match = any(_re.search(r'\b' + _re.escape(city) + r'\b', text) for city in target_cities)
            if not city_match:
                continue

            # Determine sentiment
            sentiment, neg_count = self._analyze_sentiment(text)

            # Relevance: average keyword weight, with a city-direct bonus when
            # the article mentions a target city (region IS in the news →
            # higher signal than generic infra mention).
            keyword_scores = [INFRA_KEYWORDS.get(kw, 0.5) for kw in article.get('matched_keywords', [])]
            if keyword_scores:
                relevance = sum(keyword_scores) / len(keyword_scores)
            else:
                # No infra keywords — purely a region mention. Treat as 0.6
                # baseline (lower than a strong infra story but not noise).
                relevance = 0.6
            relevance = min(1.0, relevance)
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
        
        # Sort by relevance, then dedupe near-duplicates by title-token Jaccard.
        # Sorting first ensures the highest-scoring framing of a duplicate
        # event is the one we keep (e.g. an "infrastructure-keywords-rich"
        # take wins over a generic news framing of the same Bekasi rail story).
        matched.sort(key=lambda a: a.relevance_score, reverse=True)
        pre_dedupe = len(matched)
        matched = self._dedupe_articles(matched)

        if matched:
            dropped = pre_dedupe - len(matched)
            dedupe_note = f", deduped {dropped}" if dropped else ""
            logger.info(f"📰 {region_name}: {len(matched)} news articles matched"
                       f"{dedupe_note} (top: '{matched[0].title[:60]}...')")

        return matched
    
    def _analyze_sentiment(self, text: str) -> Tuple[str, int]:
        """Simple keyword-based sentiment analysis.

        2026-04-26: Lowered the positive threshold. Was `pos_count >= 2`,
        which produced 0 positives across 65 regions on the prior run even
        when titles like "Pelabuhan Patimban Phase 2" had 1 strong keyword.
        Now: 1 high-relevance (>=0.7) keyword OR 2+ any keywords → positive.
        """
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
        pos_keywords = [kw for kw in INFRA_KEYWORDS if kw in text]
        pos_count = len(pos_keywords)
        has_strong_signal = any(INFRA_KEYWORDS.get(kw, 0) >= 0.7 for kw in pos_keywords)

        if neg_count >= 2 or (neg_count > 0 and pos_count <= 1):
            return 'negative', neg_count
        elif pos_count >= 2 or has_strong_signal:
            return 'positive', neg_count
        else:
            return 'neutral', neg_count
