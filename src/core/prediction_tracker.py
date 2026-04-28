"""
Prediction-vs-reality tracker — closes the feedback loop for the investor.

Each weekly run logs its STRONG_BUY / BUY / WATCH picks with predicted ROI
to ``data/forecasts/forecast_log.jsonl`` (v2.16.9). This module reads that
log and the per-region price-history archive, picks an anchor run that's N
weeks old, and reports how those past predictions are tracking against
realized price movement.

Why this matters: until v2.18.0, the system surfaced what's signaling *now*
but never told the investor whether past calls panned out. That's the
classic "optimizing in a vacuum" failure mode. A weekly Prediction Review
section in the email/PDF builds trust calibration, surfaces patterns
("STRONG_BUYs at 100% confidence hit 80%; clamped ones hit 30%"), and
makes the system into a learning instrument rather than a recommendation
firehose.

Three honest constraints baked into the design:

  1. Indonesian land prices don't move week-to-week. A 4-week window may
     show "+0.2%" on a "+12%/yr predicted" call — that's actually on
     track, not underperforming. We compare REALIZED to PRORATED-PREDICTED
     so the math is fair to short windows.

  2. Listing-pool noise. Lamudi's listing mix shifts week to week for
     non-market reasons. A 30% price drop can be coverage change, not
     market move. We carry a `listing_count_shift_flag` (mirrors
     tools/backtest.py logic) so the investor sees data-quality concerns
     inline, and the aggregate hit-rate excludes flagged samples.

  3. Sparse data near the start. forecast_log.jsonl was added in v2.16.9
     (2026-04-28); the 4-week window won't have a clean post-fix anchor
     until ~2026-05-26. Until then we fall back to reconstructing
     forecasts from ``output/monitoring/weekly_monitoring_*.json`` (the
     per-run JSON archive, going back to Sept 2025), but with the
     pre-2026-04-25 noise-floor caveat surfaced.

Frozen-benchmark regions (Nusantara, Labuan Bajo) are excluded — their
price data is unreliable per the deep-research report.
"""

from __future__ import annotations

import json
import logging
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PRICE_HISTORY_DIR = Path("output/scraper_cache/price_history")
DEFAULT_FORECAST_LOG = Path("data/forecasts/forecast_log.jsonl")
DEFAULT_RUN_DIR = Path("output/monitoring")

# Frozen regions per scraper_orchestrator._FROZEN_BENCHMARK_REGIONS — keep in sync.
_FROZEN_REGIONS = frozenset({
    'nusantara_capital_core',
    'nusantara_balikpapan_corridor',
    'labuan_bajo_komodo_gateway',
})

# Major scraper/scoring fix dates (matches tools/backtest.py noise floor).
# Anchors before this date predate the v2.16.4 outlier-resistant mean +
# v2.16.7 benchmark recalibration; their forecasts were partially based on
# data that has since been retroactively cleaned.
_NOISE_FLOOR_DATE = datetime(2026, 4, 25)


@dataclass
class Forecast:
    run_timestamp: datetime
    region: str
    tier: str
    investment_score: float
    confidence: float
    price_at_forecast: float
    predicted_roi_3yr: Optional[float]   # decimal e.g. 0.36 for 36% over 3yr
    predicted_roi_5yr: Optional[float]
    feasibility_flag: Optional[str]      # ✅ / ⚠️ / 🚫
    listing_count: Optional[int]         # at forecast time, when known


@dataclass
class Realization:
    forecast: Forecast
    weeks_elapsed: float
    current_price: float
    current_listing_count: Optional[int]
    realized_return_pct: float           # absolute, point-to-point
    realized_annualized_pct: float       # (1+r)^(52/weeks) - 1
    prorated_predicted_pct: Optional[float]  # what the predicted 3yr ROI says we should have at this point
    on_track: Optional[str]              # 'on_track' | 'lagging' | 'ahead' | None
    directional_correct: bool            # realized >= 0
    listing_shift_flag: bool             # listing_count moved ≥2× — comparison suspect


@dataclass
class PredictionReview:
    anchor_run_timestamp: datetime
    anchor_age_weeks: float
    realizations: List[Realization]
    excluded_listing_shifted: int
    excluded_no_history: int
    pre_noise_floor: bool                # anchor predates v2.16.4 fixes
    tier_means: Dict[str, float]         # by-tier mean realized return
    hit_rate: Optional[Tuple[int, int]]  # (positive, total) for STRONG_BUY+BUY


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_forecasts_from_log(log_path: Optional[Path] = None) -> List[Forecast]:
    """Read data/forecasts/forecast_log.jsonl into Forecast objects."""
    p = Path(log_path) if log_path else DEFAULT_FORECAST_LOG
    if not p.exists():
        return []
    out: List[Forecast] = []
    try:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = rec.get('run_timestamp')
                if not ts:
                    continue
                try:
                    run_ts = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                region = rec.get('region')
                if not region or region in _FROZEN_REGIONS:
                    continue
                price = rec.get('current_price_per_m2') or 0
                if price <= 0:
                    continue
                out.append(Forecast(
                    run_timestamp=run_ts,
                    region=region,
                    tier=rec.get('tier', 'PASS'),
                    investment_score=float(rec.get('investment_score') or 0),
                    confidence=float(rec.get('confidence') or 0),
                    price_at_forecast=float(price),
                    predicted_roi_3yr=rec.get('predicted_roi_3yr'),
                    predicted_roi_5yr=rec.get('predicted_roi_5yr'),
                    feasibility_flag=rec.get('feasibility_flag'),
                    listing_count=None,  # forecast log doesn't carry this; will derive from history
                ))
    except OSError:
        return []
    return out


def load_forecasts_from_run_archive(run_dir: Optional[Path] = None,
                                     limit: int = 200) -> List[Forecast]:
    """Reconstruct forecasts from the weekly_monitoring_*.json archive.

    Used as a fallback when forecast_log.jsonl is sparse (it was only added
    in v2.16.9). The run-archive goes back further in history.
    """
    rd = Path(run_dir) if run_dir else DEFAULT_RUN_DIR
    if not rd.exists():
        return []
    files = sorted(rd.glob('weekly_monitoring_*.json'), reverse=True)[:limit]
    out: List[Forecast] = []
    for fp in files:
        try:
            base = os.path.basename(fp)
            # weekly_monitoring_YYYYMMDD_HHMMSS.json
            stamp = base.replace('weekly_monitoring_', '').replace('.json', '')
            run_ts = datetime.strptime(stamp, '%Y%m%d_%H%M%S')
        except ValueError:
            continue
        try:
            with open(fp) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        ya = data.get('investment_analysis', {}).get('yogyakarta_analysis', {})
        for tier_label, key in [('STRONG_BUY', 'strong_buy_recommendations'),
                                ('BUY', 'buy_recommendations'),
                                ('WATCH', 'watch_list')]:
            for r in ya.get(key, []) or []:
                if not isinstance(r, dict):
                    continue
                region = r.get('region') or r.get('region_name')
                if not region or region in _FROZEN_REGIONS:
                    continue
                price = r.get('current_price_per_m2') or 0
                if price <= 0:
                    continue
                fp_obj = r.get('financial_projection') or {}
                if isinstance(fp_obj, dict):
                    roi_3yr = fp_obj.get('land_only_roi_3yr') or fp_obj.get('projected_roi_3yr')
                    roi_5yr = fp_obj.get('land_only_roi_5yr') or fp_obj.get('projected_roi_5yr')
                else:
                    roi_3yr = getattr(fp_obj, 'land_only_roi_3yr', None) or getattr(fp_obj, 'projected_roi_3yr', None)
                    roi_5yr = getattr(fp_obj, 'land_only_roi_5yr', None) or getattr(fp_obj, 'projected_roi_5yr', None)
                feas = r.get('feasibility') or {}
                out.append(Forecast(
                    run_timestamp=run_ts,
                    region=region,
                    tier=tier_label,
                    investment_score=float(r.get('investment_score') or 0),
                    confidence=float(r.get('confidence') or r.get('confidence_level') or 0),
                    price_at_forecast=float(price),
                    predicted_roi_3yr=roi_3yr,
                    predicted_roi_5yr=roi_5yr,
                    feasibility_flag=feas.get('flag') if isinstance(feas, dict) else None,
                    listing_count=None,
                ))
    return out


def load_all_forecasts() -> List[Forecast]:
    """Combine forecast log + run archive, dedup by (run_timestamp, region).
    Forecast log entries take priority when present.
    """
    log_forecasts = load_forecasts_from_log()
    archive_forecasts = load_forecasts_from_run_archive()
    seen = set()
    combined: List[Forecast] = []
    for f in log_forecasts + archive_forecasts:
        key = (f.run_timestamp.replace(microsecond=0), f.region)
        if key in seen:
            continue
        seen.add(key)
        combined.append(f)
    return combined


# ---------------------------------------------------------------------------
# Realization computation
# ---------------------------------------------------------------------------

def _load_price_history(region: str) -> List[Tuple[datetime, float, int]]:
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
                if not d or m <= 0 or lc <= 0:
                    continue
                try:
                    dt = datetime.strptime(d, '%Y-%m-%d')
                except ValueError:
                    continue
                samples.append((dt, float(m), int(lc)))
    except OSError:
        pass
    samples.sort()
    return samples


def _sample_at(samples, target: datetime, tolerance_days: int = 10):
    if not samples:
        return None
    best = min(samples, key=lambda s: abs((s[0] - target).days))
    if abs((best[0] - target).days) <= tolerance_days:
        return best
    return None


def _prorate(predicted_full_period_decimal: float, weeks_elapsed: float,
             full_period_weeks: float = 156) -> float:
    """Given a full-period predicted ROI (decimal), what fraction should be
    realized at weeks_elapsed assuming compound growth?
    """
    if predicted_full_period_decimal is None or weeks_elapsed <= 0:
        return 0
    return ((1 + predicted_full_period_decimal) ** (weeks_elapsed / full_period_weeks) - 1) * 100


def compute_realization(forecast: Forecast, now: Optional[datetime] = None) -> Optional[Realization]:
    """For one forecast, compare predicted to realized using current price history."""
    now = now or datetime.now()
    samples = _load_price_history(forecast.region)
    cur = _sample_at(samples, now, tolerance_days=10)
    if cur is None:
        return None
    cur_dt, cur_price, cur_lc = cur
    # Pull listing_count at forecast time too — needed for shift-flag.
    anchor_sample = _sample_at(samples, forecast.run_timestamp, tolerance_days=10)
    anchor_lc = anchor_sample[2] if anchor_sample else None

    weeks_elapsed = max(0.1, (now - forecast.run_timestamp).days / 7.0)
    realized_pct = ((cur_price - forecast.price_at_forecast) / forecast.price_at_forecast) * 100
    if cur_price > 0 and forecast.price_at_forecast > 0 and weeks_elapsed > 0:
        annualized = ((cur_price / forecast.price_at_forecast) ** (52.0 / weeks_elapsed) - 1) * 100
    else:
        annualized = 0

    # Listing-shift flag: anchor vs current listing count
    listing_shift = False
    if anchor_lc and cur_lc:
        ratio = cur_lc / anchor_lc
        listing_shift = ratio >= 2.0 or ratio <= 0.5

    prorated = None
    on_track = None
    if forecast.predicted_roi_3yr:
        prorated = _prorate(forecast.predicted_roi_3yr, weeks_elapsed, full_period_weeks=156)
        if prorated > 0:
            ratio = realized_pct / prorated
            if ratio >= 0.7:
                on_track = 'on_track' if ratio <= 1.5 else 'ahead'
            else:
                on_track = 'lagging'
        elif realized_pct >= 0:
            on_track = 'on_track'  # predicted ~0, realized non-negative

    return Realization(
        forecast=forecast,
        weeks_elapsed=weeks_elapsed,
        current_price=cur_price,
        current_listing_count=cur_lc,
        realized_return_pct=realized_pct,
        realized_annualized_pct=annualized,
        prorated_predicted_pct=prorated,
        on_track=on_track,
        directional_correct=realized_pct >= 0,
        listing_shift_flag=listing_shift,
    )


# ---------------------------------------------------------------------------
# Anchor selection + review build
# ---------------------------------------------------------------------------

def _pick_anchor_run(forecasts: List[Forecast], target_age_weeks: float,
                     tolerance_weeks: float = 1.0) -> Optional[datetime]:
    """Among unique run_timestamps, pick the one closest to target_age_weeks ago."""
    now = datetime.now()
    target = now - timedelta(weeks=target_age_weeks)
    by_ts: Dict[datetime, int] = {}
    for f in forecasts:
        ts = f.run_timestamp.replace(microsecond=0)
        by_ts[ts] = by_ts.get(ts, 0) + 1
    candidates = [ts for ts in by_ts
                  if abs((ts - target).total_seconds()) <= tolerance_weeks * 7 * 86400]
    if not candidates:
        return None
    return min(candidates, key=lambda ts: abs((ts - target).total_seconds()))


def build_review(forecasts: List[Forecast], target_age_weeks: float,
                 tolerance_weeks: float = 1.0) -> Optional[PredictionReview]:
    """Find an anchor run aged target_age_weeks, compute realizations for all
    its picks, return a PredictionReview.
    """
    anchor_ts = _pick_anchor_run(forecasts, target_age_weeks, tolerance_weeks)
    if anchor_ts is None:
        return None
    anchor_picks = [f for f in forecasts if f.run_timestamp.replace(microsecond=0) == anchor_ts]
    if not anchor_picks:
        return None

    realizations: List[Realization] = []
    excluded_no_history = 0
    excluded_listing_shifted = 0
    for f in anchor_picks:
        rz = compute_realization(f)
        if rz is None:
            excluded_no_history += 1
            continue
        realizations.append(rz)
        if rz.listing_shift_flag:
            excluded_listing_shifted += 1

    # Tier means (using clean — non-shifted — samples for fair aggregate)
    tier_means: Dict[str, float] = {}
    for tier in ('STRONG_BUY', 'BUY', 'WATCH'):
        clean = [r.realized_return_pct for r in realizations
                 if r.forecast.tier == tier and not r.listing_shift_flag]
        if len(clean) >= 2:
            tier_means[tier] = statistics.mean(clean)

    # Hit rate: STRONG_BUY+BUY only, excluding listing-shifted
    actionable = [r for r in realizations
                  if r.forecast.tier in ('STRONG_BUY', 'BUY') and not r.listing_shift_flag]
    hit_rate = None
    if actionable:
        positive = sum(1 for r in actionable if r.directional_correct)
        hit_rate = (positive, len(actionable))

    age_weeks = (datetime.now() - anchor_ts).days / 7.0
    return PredictionReview(
        anchor_run_timestamp=anchor_ts,
        anchor_age_weeks=age_weeks,
        realizations=realizations,
        excluded_listing_shifted=excluded_listing_shifted,
        excluded_no_history=excluded_no_history,
        pre_noise_floor=anchor_ts < _NOISE_FLOOR_DATE,
        tier_means=tier_means,
        hit_rate=hit_rate,
    )


# ---------------------------------------------------------------------------
# Email rendering
# ---------------------------------------------------------------------------

def _icon_for_realization(rz: Realization) -> str:
    if rz.listing_shift_flag:
        return '⚠'
    if rz.on_track == 'ahead':
        return '🔥'
    if rz.on_track == 'on_track':
        return '✅'
    if rz.on_track == 'lagging':
        return '⏳'
    return '✅' if rz.directional_correct else '❌'


def review_to_email_lines(review: PredictionReview, max_per_tier: int = 3) -> List[str]:
    """Render a PredictionReview as plain-text email lines."""
    out: List[str] = []
    age_label = f"{review.anchor_age_weeks:.0f} weeks ago"
    anchor_date = review.anchor_run_timestamp.date().isoformat()
    out.append(f"Predictions from {age_label} (anchor: {anchor_date}):")
    if review.pre_noise_floor:
        out.append(f"  ⚠️  Anchor predates 2026-04-25 v2.16.x fix wave —")
        out.append(f"     deltas reflect scraper recalibration as much as real")
        out.append(f"     market movement. Treat directionally; full predictive")
        out.append(f"     signal needs anchors after 2026-04-25.")

    # Sort realizations: tier order (STRONG_BUY first), then by realized_return desc
    tier_order = {'STRONG_BUY': 0, 'BUY': 1, 'WATCH': 2}
    grouped: Dict[str, List[Realization]] = {}
    for rz in review.realizations:
        grouped.setdefault(rz.forecast.tier, []).append(rz)
    for tier in sorted(grouped, key=lambda t: tier_order.get(t, 99)):
        regions = sorted(grouped[tier], key=lambda r: -r.realized_return_pct)[:max_per_tier]
        for rz in regions:
            f = rz.forecast
            icon = _icon_for_realization(rz)
            line1 = (f"  {icon} {f.region:35s}  {f.tier:10s} @ Rp {f.price_at_forecast:>10,.0f}/m²")
            shift_note = ' *listing-shift' if rz.listing_shift_flag else ''
            out.append(line1 + shift_note)
            # Sanitize the annualized display — short windows with extreme
            # deltas (>50% realized in <8 weeks) almost always reflect data
            # artifacts (slug changes, outlier-resistant mean fix, listing-
            # pool turnover) rather than real market moves. Annualizing those
            # produces absurd numbers like 3,796,042%/yr that mislead more
            # than inform. Cap display at ±500% and flag the rest.
            if abs(rz.realized_annualized_pct) > 500:
                ann_display = "ann saturated (likely data artifact, not market)"
            else:
                ann_display = f"ann {rz.realized_annualized_pct:+.1f}%"
            if rz.prorated_predicted_pct is not None:
                line2 = (f"     Today: Rp {rz.current_price:>10,.0f}/m² "
                         f"({rz.realized_return_pct:+.1f}%, {ann_display}) "
                         f"vs prorated-predicted {rz.prorated_predicted_pct:+.1f}% — {rz.on_track or 'n/a'}")
            else:
                line2 = (f"     Today: Rp {rz.current_price:>10,.0f}/m² "
                         f"({rz.realized_return_pct:+.1f}%, {ann_display}) "
                         f"— no predicted ROI in archive")
            out.append(line2)
            if rz.listing_shift_flag and rz.current_listing_count is not None:
                out.append(f"     ⚠ listing pool shifted to {rz.current_listing_count} listings — "
                           "comparison may reflect coverage change rather than market move")

    # Aggregate
    if review.tier_means:
        out.append("")
        means_str = ' / '.join(f'{t} {v:+.1f}%' for t, v in review.tier_means.items())
        out.append(f"  Tier means (clean samples only): {means_str}")
        # Tier ordering check
        ranks = list(review.tier_means.values())
        if 'STRONG_BUY' in review.tier_means and 'WATCH' in review.tier_means:
            sb = review.tier_means['STRONG_BUY']
            w = review.tier_means['WATCH']
            order_ok = sb > w
            out.append(f"  Tier integrity: STRONG_BUY {sb:+.1f}% vs WATCH {w:+.1f}% — "
                       f"{'✅ order preserved' if order_ok else '❌ INVERTED — review scoring weights'}")
    if review.hit_rate:
        positive, total = review.hit_rate
        pct = 100.0 * positive / total if total else 0
        out.append(f"  Hit rate: {positive}/{total} STRONG_BUY+BUY moved positively ({pct:.0f}%)")
    if review.excluded_listing_shifted or review.excluded_no_history:
        out.append(f"  Excluded: {review.excluded_listing_shifted} listing-shifted, "
                   f"{review.excluded_no_history} no current price history")
    return out


def empty_review_lines(target_age_weeks: float) -> List[str]:
    """Lines to render when no anchor was found at the target age."""
    needed_date = (datetime.now() - timedelta(weeks=target_age_weeks)).date()
    out: List[str] = []
    out.append(f"Predictions from {target_age_weeks:.0f} weeks ago: ⏳ Insufficient post-fix history.")
    out.append(f"  forecast_log.jsonl writer activated 2026-04-28 (v2.16.9).")
    out.append(f"  This window will become meaningful once 4+ weeks of post-2026-04-25")
    out.append(f"  history accumulate (target: ~{(_NOISE_FLOOR_DATE + timedelta(weeks=target_age_weeks)).date().isoformat()}).")
    return out


def build_full_review_section() -> List[str]:
    """Build the complete email section. Returns list of lines (with header).

    Tries anchors at 4w, 8w, 12w. Skips windows with no anchor or empty data
    (with a transparent placeholder so the investor knows when to expect data).
    """
    forecasts = load_all_forecasts()
    lines: List[str] = []
    if not forecasts:
        return lines  # empty section if absolutely no history

    lines.append("PREDICTION REVIEW — How past calls are tracking")
    lines.append("-" * 55)

    rendered_any = False
    for target_weeks, tol in [(4, 1.0), (8, 1.5), (12, 2.0)]:
        review = build_review(forecasts, target_age_weeks=target_weeks, tolerance_weeks=tol)
        if review is None:
            lines.extend(empty_review_lines(target_weeks))
        else:
            lines.extend(review_to_email_lines(review))
            rendered_any = True
        lines.append("")

    if not rendered_any:
        lines.append("Tracking begins after the first weekly run; comparable predictions")
        lines.append("require at least one prior weekly cycle.")

    return lines
