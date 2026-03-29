"""
News Catalyst Scoring Module
CloudClearingAPI - v2.10

Converts matched news articles into a scoring multiplier.
Regions with announced infrastructure projects receive a boost;
negative coverage (cancellations, disputes) receives a penalty.

Multiplier range: 0.95x–1.20x
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class NewsCatalystResult:
    """Result of news catalyst analysis for a single region"""
    region_name: str
    multiplier: float            # 0.95–1.20
    articles_found: int
    positive_count: int
    negative_count: int
    neutral_count: int
    top_keywords: List[str]      # Most frequent keywords
    top_article_title: str       # Highest relevance article title
    summary: str                 # Human-readable description
    article_links: List[dict] = None  # [{title, url, source, sentiment}]

    def __post_init__(self):
        if self.article_links is None:
            self.article_links = []


class NewsCatalyst:
    """
    Converts news article matches into a scoring multiplier.
    
    Multiplier logic:
    - 0 articles: 1.00x (neutral, no news signal)
    - 1-2 positive: 1.05x (early development signals)
    - 3-5 positive: 1.10x (active development zone)
    - 6+ positive: 1.15x–1.20x (major development hub)
    - Negative news reduces multiplier below 1.00x
    """
    
    def __init__(self):
        logger.info("📰 News Catalyst engine initialized")
    
    def calculate_catalyst(self, region_name: str, articles: List[Any]) -> NewsCatalystResult:
        """
        Convert matched news articles to a scoring multiplier.
        
        Args:
            region_name: Region name
            articles: List of NewsArticle objects matched to this region
            
        Returns:
            NewsCatalystResult with multiplier and breakdown
        """
        if not articles:
            return NewsCatalystResult(
                region_name=region_name,
                multiplier=1.0,
                articles_found=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                top_keywords=[],
                top_article_title='',
                summary='No development news found for this region'
            )
        
        # Count sentiment
        positive = [a for a in articles if a.sentiment == 'positive']
        negative = [a for a in articles if a.sentiment == 'negative']
        neutral = [a for a in articles if a.sentiment == 'neutral']
        
        pos_count = len(positive)
        neg_count = len(negative)
        
        # Calculate base multiplier from positive articles
        if pos_count >= 6:
            base_mult = 1.15 + min(0.05, (pos_count - 6) * 0.01)  # Cap at 1.20
        elif pos_count >= 3:
            base_mult = 1.10
        elif pos_count >= 1:
            base_mult = 1.05
        else:
            base_mult = 1.00
        
        # Apply negative penalty
        if neg_count >= 3:
            base_mult *= 0.92  # Strong negative signal
        elif neg_count >= 1:
            base_mult *= 0.97  # Mild negative signal
        
        # Clamp to range
        multiplier = round(max(0.95, min(1.20, base_mult)), 3)
        
        # Collect top keywords
        all_keywords = []
        for a in articles:
            all_keywords.extend(a.matched_keywords)
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        top_keywords = sorted(keyword_counts.keys(), key=lambda k: keyword_counts[k], reverse=True)[:5]
        
        # Best article
        top_article = max(articles, key=lambda a: a.relevance_score)
        
        # Generate summary
        summary = self._generate_summary(multiplier, pos_count, neg_count, len(articles), top_keywords)
        
        logger.info(f"📰 {region_name}: News catalyst {multiplier:.2f}x "
                    f"({pos_count}+ / {neg_count}- / {len(neutral)} neutral, "
                    f"{len(articles)} total articles)")
        
        # Build article links list (sorted by relevance)
        sorted_articles = sorted(articles, key=lambda a: a.relevance_score, reverse=True)
        article_links = [
            {
                'title': a.title[:120],
                'url': a.url,
                'source': a.source,
                'sentiment': a.sentiment,
            }
            for a in sorted_articles[:10]  # Cap at 10 most relevant
        ]

        return NewsCatalystResult(
            region_name=region_name,
            multiplier=multiplier,
            articles_found=len(articles),
            positive_count=pos_count,
            negative_count=neg_count,
            neutral_count=len(neutral),
            top_keywords=top_keywords,
            top_article_title=top_article.title[:100],
            summary=summary,
            article_links=article_links,
        )
    
    def _generate_summary(self, multiplier: float, pos: int, neg: int, total: int, keywords: List[str]) -> str:
        """Generate human-readable summary."""
        kw_str = ', '.join(keywords[:3]) if keywords else 'general development'
        
        if multiplier >= 1.15:
            return f"Major development hub: {total} articles ({pos} positive) covering {kw_str}"
        elif multiplier >= 1.10:
            return f"Active development zone: {total} articles ({pos} positive) on {kw_str}"
        elif multiplier >= 1.05:
            return f"Early development signals: {total} articles ({pos} positive) mentioning {kw_str}"
        elif multiplier < 1.0:
            return f"Cautionary news: {neg} negative articles found alongside {pos} positive"
        else:
            return f"No significant development news ({total} articles scanned)"
