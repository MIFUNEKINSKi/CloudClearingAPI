"""
Portfolio-aware action layer — Track A / Phase 3.

The weekly briefing tells the investor what's hot in the 65-region universe
but never tells them what's missing from their book. A STRONG_BUY in a region
they already own adds correlation, not diversification. A 4-week price decline
on an owned position is more actionable than a generic STRONG_BUY they have
no relationship to.

This module bridges that gap with three components:

  1. Position log — JSONL file at ``data/positions.jsonl``, manually
     maintained by the investor. One line per acquired position.

  2. P&L computation — for each position, compute current value from
     ``output/scraper_cache/price_history/<region>.jsonl`` and report the
     unrealized gain/loss.

  3. Alerts — flag positions where:
       * price has declined >5% over the last 4 weekly samples (EXIT_WATCH)
       * listing volume has crashed (>=50% drop) suggesting illiquidity
         (LIQUIDITY_RISK)
       * tier has downgraded vs prior runs (TIER_DOWNGRADE) — surfaced
         from automated_monitor.tier_transitions

Position log format (JSONL, one position per line)::

    {"region": "cikarang_mega_industrial",
     "size_m2": 500,
     "acquisition_date": "2025-12-01",
     "cost_per_m2": 2300000,
     "title_type": "HGB",
     "notes": "Lippo Cikarang plot"}

See ``docs/positions.jsonl.example`` for the schema reference. The
``data/`` directory is gitignored (positions are investor-private).
Copy the example file to ``data/positions.jsonl`` to activate this
feature.

The position log is OPTIONAL. If the file doesn't exist, the email renders
exactly as before — Phase 3 only activates when the investor has populated
positions to track.
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


PRICE_HISTORY_DIR = Path("output/scraper_cache/price_history")
DEFAULT_POSITIONS_PATH = Path("data/positions.jsonl")


@dataclass
class Position:
    region: str
    size_m2: float
    acquisition_date: str          # ISO YYYY-MM-DD
    cost_per_m2: float             # IDR/m² at acquisition
    title_type: str = "HGB"        # 'HGB' | 'leasehold' | 'hak_pakai' | 'SHM_nominee'
    notes: str = ""

    @property
    def total_cost(self) -> float:
        return self.size_m2 * self.cost_per_m2


@dataclass
class PositionPnL:
    position: Position
    current_price_per_m2: float
    current_market_value: float
    unrealized_pnl_idr: float
    unrealized_pnl_pct: float
    days_held: int
    annualized_return_pct: float
    alerts: List[str] = field(default_factory=list)


def load_positions(path: Optional[Path] = None) -> List[Position]:
    """Read positions.jsonl. Returns empty list if file is absent."""
    p = Path(path) if path else DEFAULT_POSITIONS_PATH
    if not p.exists():
        return []
    out: List[Position] = []
    try:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"positions.jsonl: skipping malformed line: {e}")
                    continue
                try:
                    out.append(Position(
                        region=rec['region'],
                        size_m2=float(rec['size_m2']),
                        acquisition_date=rec['acquisition_date'],
                        cost_per_m2=float(rec['cost_per_m2']),
                        title_type=rec.get('title_type', 'HGB'),
                        notes=rec.get('notes', ''),
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"positions.jsonl: skipping incomplete entry: {e}")
    except OSError as e:
        logger.warning(f"positions.jsonl read failed: {e}")
    return out


def _load_recent_history(region: str, n: int = 8) -> List[Tuple[datetime, float, int]]:
    """Last N samples of (date, median_price_m2, listing_count) for a region."""
    f = PRICE_HISTORY_DIR / f"{region}.jsonl"
    if not f.exists():
        return []
    samples: List[Tuple[datetime, float, int]] = []
    try:
        with open(f) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = rec.get('date')
                m = rec.get('median_price_m2') or 0
                lc = rec.get('listing_count') or 0
                if not d or m <= 0:
                    continue
                try:
                    dt = datetime.strptime(d, '%Y-%m-%d')
                except ValueError:
                    continue
                samples.append((dt, float(m), int(lc)))
    except OSError:
        return []
    samples.sort()
    return samples[-n:]


def compute_position_pnl(position: Position, recent_history: Optional[List] = None) -> PositionPnL:
    """Compute P&L for a position using the latest available price."""
    history = recent_history if recent_history is not None else _load_recent_history(position.region)

    if history:
        current_price_per_m2 = history[-1][1]
    else:
        # No price history — use cost as current. Will produce zero P&L,
        # which is the right "we don't know" signal vs fabricating a number.
        current_price_per_m2 = position.cost_per_m2

    current_market_value = position.size_m2 * current_price_per_m2
    unrealized_pnl_idr = current_market_value - position.total_cost
    unrealized_pnl_pct = (
        (unrealized_pnl_idr / position.total_cost) * 100
        if position.total_cost > 0 else 0
    )

    try:
        acq_date = datetime.strptime(position.acquisition_date, '%Y-%m-%d')
        days_held = max(1, (datetime.now() - acq_date).days)
    except ValueError:
        days_held = 1
    annualized = ((current_market_value / position.total_cost) ** (365.0 / days_held) - 1) * 100 if position.total_cost > 0 and days_held > 0 else 0

    alerts: List[str] = []
    # EXIT_WATCH: price decline >5% over the last 4 samples.
    if len(history) >= 4:
        early_avg = statistics.mean(s[1] for s in history[-4:-2])
        late_avg = statistics.mean(s[1] for s in history[-2:])
        if early_avg > 0 and ((late_avg - early_avg) / early_avg) * 100 < -5:
            decline_pct = ((late_avg - early_avg) / early_avg) * 100
            alerts.append(f"EXIT_WATCH: median price down {decline_pct:.1f}% over last 4 samples")

    # LIQUIDITY_RISK: listing_count drop ≥50% in the last 2 samples vs earlier 2.
    if len(history) >= 4:
        early_lc = statistics.mean(s[2] for s in history[-4:-2])
        late_lc = statistics.mean(s[2] for s in history[-2:])
        if early_lc > 5 and late_lc / early_lc <= 0.5:
            alerts.append(
                f"LIQUIDITY_RISK: listing volume dropped {(1 - late_lc/early_lc)*100:.0f}% "
                f"({early_lc:.0f}→{late_lc:.0f}) — exit may be slower"
            )

    return PositionPnL(
        position=position,
        current_price_per_m2=current_price_per_m2,
        current_market_value=current_market_value,
        unrealized_pnl_idr=unrealized_pnl_idr,
        unrealized_pnl_pct=unrealized_pnl_pct,
        days_held=days_held,
        annualized_return_pct=annualized,
        alerts=alerts,
    )


# ============================================================================
# Correlation hints for suggested additions
# ============================================================================
# A STRONG_BUY in a region the investor already heavily owns adds correlation,
# not diversification. Same-bucket correlation is a directional flag — the
# investor still sees the recommendation, but with a one-line "you already
# have N positions in this bucket" annotation.

# Bucket map mirrors scraper_orchestrator._find_nearest_benchmark — keep
# in sync so correlation reasoning matches benchmark routing.
_CORRELATION_BUCKETS: Dict[str, List[str]] = {
    'banten': ['anyer', 'carita', 'cilegon', 'serang', 'merak'],
    'jakarta': ['jakarta', 'tangerang', 'bekasi', 'cikarang', 'bogor', 'karawang'],
    'denpasar': ['denpasar'],
    'yogyakarta': ['yogyakarta', 'yogya', 'sleman', 'bantul', 'kulon', 'magelang', 'purwokerto'],
    'surabaya': ['surabaya', 'sidoarjo', 'gresik', 'malang', 'probolinggo', 'jember', 'banyuwangi'],
    'bandung': ['bandung', 'cirebon', 'subang'],
    'semarang': ['semarang', 'solo', 'tegal', 'batang'],
    'bali': ['bali', 'canggu', 'seminyak', 'sanur', 'ubud', 'tabanan', 'nusa', 'bukit'],
    'medan': ['medan', 'kuala', 'belawan', 'toba'],
    'palembang': ['palembang', 'jakabaring', 'boom'],
    'lampung': ['lampung', 'bakauheni'],
    'batam': ['batam'],
    'makassar': ['makassar', 'manado', 'bitung'],
    'balikpapan': ['balikpapan', 'samarinda', 'banjarmasin', 'pontianak'],
    'nusantara': ['nusantara', 'ikn'],
    'lombok': ['lombok', 'mataram', 'mandalika', 'senggigi'],
}


def _bucket_for(region: str) -> Optional[str]:
    tokens = set(region.lower().split('_'))
    for bucket, keywords in _CORRELATION_BUCKETS.items():
        if any(kw in tokens for kw in keywords):
            return bucket
    return None


def correlation_hint(candidate_region: str, positions: List[Position]) -> Optional[str]:
    """If the candidate is in the same bucket as an existing position, return
    a one-line hint that the position adds correlation rather than diversification.
    Returns None when uncorrelated.
    """
    if not positions:
        return None
    candidate_bucket = _bucket_for(candidate_region)
    if not candidate_bucket:
        return None
    overlapping = [p for p in positions if _bucket_for(p.region) == candidate_bucket]
    if not overlapping:
        return None
    if len(overlapping) == 1:
        return (f"📌 You already hold {overlapping[0].region} in this bucket "
                f"({candidate_bucket}) — adds correlation, not diversification")
    names = ', '.join(p.region for p in overlapping[:2])
    extra = f' +{len(overlapping)-2} more' if len(overlapping) > 2 else ''
    return (f"📌 You already hold {len(overlapping)} positions in {candidate_bucket} "
            f"bucket ({names}{extra}) — high correlation")


# ============================================================================
# Tier downgrade alert (uses tier_transitions from the run)
# ============================================================================

def position_tier_downgrade_alert(position: Position, downgrades: List[Dict]) -> Optional[str]:
    """If this position appears in the run's downgrades list, return a short
    alert string suitable for embedding in the portfolio email section.
    """
    for d in downgrades:
        if d.get('region') == position.region:
            return (f"TIER_DOWNGRADE: {d.get('from_tier','?')} → {d.get('to_tier','?')} "
                    f"this run (score {d.get('from_score',0):.1f} → {d.get('to_score',0):.1f})")
    return None
