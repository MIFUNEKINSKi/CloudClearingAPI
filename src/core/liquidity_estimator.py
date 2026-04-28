"""
Empirical liquidity estimation from archived Lamudi listing counts.

Track A / Phase 2 polish — replaces the tier-based ``liquidity_tier`` default
with an observed estimate from each region's price-history JSONL.

Important caveat: the scraper caps at ``max_listings=20`` per scrape (set by
the orchestrator). A region returning 20 listings/run means "scraper hit the
cap; actual supply is unknown but ≥20". Regions below the cap are where the
real signal lives — those reflect genuinely thin retail markets.

So the mapping is asymmetric:
  - avg listings < 5    → 'very_low'   (genuinely dead retail market)
  - avg listings 5-9    → 'low'        (thin but functional)
  - avg listings 10-15  → 'moderate'   (visible activity, not saturated)
  - avg listings ≥ 15   → 'cap_saturated' (scraper hits cap; static
                                         tier from research is more reliable)

The observed tier is *advisory* — it sits alongside the research-validated
``liquidity_tier`` rather than overriding it. When the two disagree we
surface that as a flag (e.g., "research says high but observed avg 4.7
listings/scrape — verify before acting"). Disagreement is information.
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PRICE_HISTORY_DIR = Path("output/scraper_cache/price_history")

# Scraper saturation point — set in orchestrator's max_listings; if a region's
# avg observed listings is at-or-near this, the scraper saw "plenty" but
# couldn't measure ceiling.
_SCRAPER_CAP = 20


@dataclass
class LiquidityEstimate:
    region: str
    n_samples: int
    avg_listings: float
    median_listings: float
    min_listings: int
    max_listings: int
    observed_tier: str             # 'very_low' | 'low' | 'moderate' | 'cap_saturated' | 'unknown'
    scraper_saturated: bool        # True when median ≥ cap; observed tier is unreliable
    confidence: str                # 'high' | 'low' | 'unknown'


def _volume_to_tier(avg_listings: float, scraper_saturated: bool) -> str:
    if scraper_saturated:
        return 'cap_saturated'
    if avg_listings < 5:
        return 'very_low'
    if avg_listings < 10:
        return 'low'
    if avg_listings < 15:
        return 'moderate'
    return 'cap_saturated'


def estimate_liquidity(region: str, n_recent: int = 8) -> LiquidityEstimate:
    """Compute empirical liquidity tier for a region from its price history.

    Reads the last ``n_recent`` samples (with at least 1 listing) and
    classifies into observed_tier. Returns a "unknown" estimate when no
    history is available.
    """
    f = PRICE_HISTORY_DIR / f"{region}.jsonl"
    if not f.exists():
        return LiquidityEstimate(
            region=region, n_samples=0, avg_listings=0, median_listings=0,
            min_listings=0, max_listings=0, observed_tier='unknown',
            scraper_saturated=False, confidence='unknown',
        )

    listings: List[int] = []
    try:
        with open(f) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lc = rec.get('listing_count') or 0
                if lc > 0:
                    listings.append(int(lc))
    except OSError:
        pass

    if not listings:
        return LiquidityEstimate(
            region=region, n_samples=0, avg_listings=0, median_listings=0,
            min_listings=0, max_listings=0, observed_tier='unknown',
            scraper_saturated=False, confidence='unknown',
        )

    recent = listings[-n_recent:]
    avg = statistics.mean(recent)
    med = statistics.median(recent)
    saturated = med >= _SCRAPER_CAP
    confidence = 'high' if len(recent) >= 4 else 'low'
    return LiquidityEstimate(
        region=region,
        n_samples=len(recent),
        avg_listings=avg,
        median_listings=med,
        min_listings=min(recent),
        max_listings=max(recent),
        observed_tier=_volume_to_tier(avg, saturated),
        scraper_saturated=saturated,
        confidence=confidence,
    )


# Mapping between research-validated qualitative tiers (from
# region_feasibility._PROFILES) and an ordering for mismatch detection.
_RESEARCH_TIER_ORDER = {
    'very_high': 4,
    'high': 3,
    'moderate': 2,
    'low': 1,
    'very_low': 0,
}

_OBSERVED_TIER_ORDER = {
    'cap_saturated': 4,
    'moderate': 2,
    'low': 1,
    'very_low': 0,
}


def liquidity_mismatch(research_tier: str, observed: LiquidityEstimate) -> Optional[str]:
    """Return a short mismatch message if research tier and observation disagree
    by 2+ levels. Returns None for matched/close tiers or when one side is unknown.
    """
    if observed.observed_tier in ('unknown',) or observed.confidence == 'unknown':
        return None
    if observed.scraper_saturated:
        # Scraper-saturated observations don't contradict 'high'/'very_high' —
        # they confirm "plenty of supply" without measuring a ceiling.
        return None
    research_rank = _RESEARCH_TIER_ORDER.get(research_tier)
    observed_rank = _OBSERVED_TIER_ORDER.get(observed.observed_tier)
    if research_rank is None or observed_rank is None:
        return None
    if research_rank - observed_rank >= 2:
        return (f"⚠ liquidity below research expectation: research said "
                f"'{research_tier}' but observed avg {observed.avg_listings:.1f} "
                f"listings/scrape ({observed.observed_tier})")
    return None


def liquidity_summary_label(observed: LiquidityEstimate) -> str:
    """Short human-readable label for the email/PDF rendering.

    'cap_saturated' is rendered as the friendly "ample" since investors
    don't need to know about scraper internals.
    """
    if observed.observed_tier == 'unknown':
        return 'no listing history'
    if observed.scraper_saturated:
        return f"ample (~{int(observed.median_listings)}+ listings/scrape)"
    return f"{observed.avg_listings:.1f} listings/scrape avg ({observed.observed_tier})"
