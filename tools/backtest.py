#!/usr/bin/env python3
"""
Backtest harness for CloudClearingAPI.

For each historical run that's at least N weeks old, compares the run's
tier recommendations (STRONG_BUY/BUY/WATCH/PASS) against the actual price
movement of those regions over the N-week window.

The premise: if the scoring is predictive, regions ranked STRONG_BUY at time
T should show higher median price growth at time T+N than regions ranked
PASS. The signal we measure is RELATIVE — across-tier comparison controls
for general market trends and scraper-coverage shifts.

Usage:
    python tools/backtest.py                # 4-week + 8-week windows
    python tools/backtest.py --window 4     # just 4-week
    python tools/backtest.py --tolerance 5  # ±5 days around target window

Output:
    Console summary + output/backtests/backtest_YYYYMMDD_HHMMSS.json

Methodology notes:
    - Price-change is measured on `median_price_m2` from the per-region
      price-history JSONL (Lamudi medians), since the median was robust
      against the v2.16.4-fixed listing-level outlier issue.
    - Regions in `_FROZEN_BENCHMARK_REGIONS` (Nusantara, Labuan Bajo) are
      excluded — their price data is unreliable per the deep-research
      report (40× source disagreement on retail platforms).
    - Anchor runs are the OLDEST run within the target window for each
      region — gives the longest measurable price trajectory.
    - Hit-rate metric: did STRONG_BUY median price-change > BUY > WATCH >
      PASS? Plus Spearman rank correlation between investment_score and
      realized N-week price-change.

Caveats:
    - "Price change" is *what our scraper extracted*, not necessarily what
      the actual market did. Major scraper changes (slug fixes, outlier-
      mean fix) can produce artifactual price moves not tied to real
      market movement. The relative-tier-ranking metric mitigates this
      because all tiers are subject to the same scraper-noise floor.
    - Sample sizes are small (3-10 regions per tier per anchor); reported
      means are directional, not statistically significant.

Author: CloudClearingAPI Team
Date: 2026-04-28
"""

import argparse
import glob
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Match the orchestrator's frozen list — these regions have unreliable price data
_FROZEN_REGIONS = frozenset({
    'nusantara_capital_core',
    'nusantara_balikpapan_corridor',
    'labuan_bajo_komodo_gateway',
})

PRICE_HISTORY_DIR = Path('output/scraper_cache/price_history')
RUN_DIR = Path('output/monitoring')
OUT_DIR = Path('output/backtests')


def parse_run_timestamp(path: Path) -> Optional[datetime]:
    """weekly_monitoring_YYYYMMDD_HHMMSS.json → datetime."""
    stem = path.stem.replace('weekly_monitoring_', '')
    try:
        return datetime.strptime(stem, '%Y%m%d_%H%M%S')
    except ValueError:
        return None


def load_run(path: Path) -> Optional[Dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def extract_tier_assignments(run_data: Dict) -> Dict[str, Tuple[str, float]]:
    """Return {region_name: (tier, investment_score)} from a run JSON."""
    out: Dict[str, Tuple[str, float]] = {}
    ya = run_data.get('investment_analysis', {}).get('yogyakarta_analysis', {})
    for tier_label, key in [
        ('STRONG_BUY', 'strong_buy_recommendations'),
        ('BUY', 'buy_recommendations'),
        ('WATCH', 'watch_list'),
        ('PASS', 'pass_list'),
    ]:
        for entry in ya.get(key, []) or []:
            region = entry.get('region') or entry.get('region_name')
            score = entry.get('investment_score') or entry.get('final_score') or 0
            if region:
                out[region] = (tier_label, float(score))
    return out


def load_price_history(region: str) -> List[Tuple[datetime, float, int]]:
    """Return sorted [(date, median_price_m2, listing_count), ...] for a region."""
    f = PRICE_HISTORY_DIR / f'{region}.jsonl'
    if not f.exists():
        return []
    samples: List[Tuple[datetime, float, int]] = []
    with open(f) as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            d = rec.get('date')
            m = rec.get('median_price_m2') or 0
            n = rec.get('listing_count') or 0
            if not d or m <= 0 or n < 3:
                continue
            try:
                dt = datetime.strptime(d, '%Y-%m-%d')
            except ValueError:
                continue
            samples.append((dt, float(m), int(n)))
    samples.sort()
    return samples


def sample_at(samples: List[Tuple[datetime, float, int]], target: datetime,
              tolerance_days: int = 7) -> Optional[Tuple[float, int]]:
    """Find the price-history sample nearest to target, within tolerance.

    Returns (price, listing_count) or None if no sample is within tolerance.
    """
    if not samples:
        return None
    best = min(samples, key=lambda s: abs((s[0] - target).days))
    if abs((best[0] - target).days) <= tolerance_days:
        return best[1], best[2]
    return None


def spearman(xy: List[Tuple[float, float]]) -> Tuple[float, int]:
    """Spearman rank correlation. Returns (rho, n).

    Hand-rolled to avoid scipy dependency. Uses average ranks for ties.
    """
    n = len(xy)
    if n < 3:
        return float('nan'), n
    xs = [p[0] for p in xy]
    ys = [p[1] for p in xy]

    def ranks(arr):
        idx = sorted(range(len(arr)), key=lambda i: arr[i])
        r = [0.0] * len(arr)
        i = 0
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and arr[idx[j + 1]] == arr[idx[i]]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[idx[k]] = avg_rank
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    num = sum((rx[i] - mean_x) * (ry[i] - mean_y) for i in range(n))
    denx = (sum((rx[i] - mean_x) ** 2 for i in range(n))) ** 0.5
    deny = (sum((ry[i] - mean_y) ** 2 for i in range(n))) ** 0.5
    if denx == 0 or deny == 0:
        return float('nan'), n
    return num / (denx * deny), n


def find_anchor_run(runs: List[Tuple[datetime, Path]], target_age_days: int,
                    tolerance: int) -> Optional[Tuple[datetime, Path]]:
    """Find the run closest to (now - target_age_days), within tolerance."""
    now = datetime.now()
    target = now - timedelta(days=target_age_days)
    candidates = [r for r in runs if abs((r[0] - target).days) <= tolerance]
    if not candidates:
        return None
    return min(candidates, key=lambda r: abs((r[0] - target).days))


def backtest_window(runs: List[Tuple[datetime, Path]], window_weeks: int,
                    tolerance: int = 5) -> Optional[Dict]:
    """Run a backtest for one window (4w, 8w, etc.). Returns summary dict."""
    anchor = find_anchor_run(runs, target_age_days=window_weeks * 7, tolerance=tolerance)
    if anchor is None:
        return None
    anchor_dt, anchor_path = anchor
    run_data = load_run(anchor_path)
    if not run_data:
        return None

    assignments = extract_tier_assignments(run_data)
    if not assignments:
        return None

    now = datetime.now()
    by_tier: Dict[str, List[Dict]] = {'STRONG_BUY': [], 'BUY': [], 'WATCH': [], 'PASS': []}
    score_delta_pairs: List[Tuple[float, float]] = []

    for region, (tier, score) in assignments.items():
        if region in _FROZEN_REGIONS:
            continue
        samples = load_price_history(region)
        s_anchor = sample_at(samples, anchor_dt, tolerance_days=10)
        s_now = sample_at(samples, now, tolerance_days=10)
        if s_anchor is None or s_now is None or s_anchor[0] <= 0:
            continue
        p_anchor, n_anchor = s_anchor
        p_now, n_now = s_now
        delta_pct = ((p_now - p_anchor) / p_anchor) * 100
        # listing_count change is a coverage-shift proxy: when listings
        # double or halve, the price comparison is more about scraper
        # behavior than market movement. Flag and exclude from headline
        # tier means.
        listing_ratio = (n_now / n_anchor) if n_anchor else 0
        listing_shift = listing_ratio >= 2.0 or listing_ratio <= 0.5
        rec = {
            'region': region,
            'score_at_anchor': score,
            'price_at_anchor': p_anchor,
            'price_now': p_now,
            'delta_pct': delta_pct,
            'listings_at_anchor': n_anchor,
            'listings_now': n_now,
            'listing_shift_flag': listing_shift,
        }
        by_tier[tier].append(rec)
        # Only feed clean comparisons (no listing shift) into Spearman.
        if not listing_shift:
            score_delta_pairs.append((score, delta_pct))

    # Per-tier aggregates: split clean vs listing-shifted samples so the
    # headline number isn't polluted by scraper-coverage artifacts.
    tier_summary = {}
    for tier, recs in by_tier.items():
        clean = [r for r in recs if not r['listing_shift_flag']]
        if len(clean) < 3:
            tier_summary[tier] = {
                'n_total': len(recs),
                'n_clean': len(clean),
                'note': 'insufficient clean sample (<3 after listing-shift filter)',
            }
            continue
        deltas_clean = [r['delta_pct'] for r in clean]
        deltas_all = [r['delta_pct'] for r in recs]
        tier_summary[tier] = {
            'n_total': len(recs),
            'n_clean': len(clean),
            'n_shifted': len(recs) - len(clean),
            'mean_delta_pct_clean': statistics.mean(deltas_clean),
            'median_delta_pct_clean': statistics.median(deltas_clean),
            'positive_pct_clean': 100.0 * sum(1 for d in deltas_clean if d > 0) / len(clean),
            'mean_delta_pct_all': statistics.mean(deltas_all),
            'top_3_regions': sorted(recs, key=lambda r: -r['delta_pct'])[:3],
            'bottom_3_regions': sorted(recs, key=lambda r: r['delta_pct'])[:3],
        }

    # Cross-tier ranking signal
    rho, n_pairs = spearman(score_delta_pairs)

    # Mean-delta tier ordering (does STRONG_BUY > BUY > WATCH > PASS?).
    # Use clean (listing-shift-filtered) means since they reflect price moves
    # where scraper coverage stayed comparable across the window.
    means = {
        t: tier_summary[t].get('mean_delta_pct_clean')
        for t in ('STRONG_BUY', 'BUY', 'WATCH', 'PASS')
        if 'mean_delta_pct_clean' in tier_summary[t]
    }

    return {
        'window_weeks': window_weeks,
        'anchor_run': anchor_path.name,
        'anchor_date': anchor_dt.isoformat(),
        'anchor_age_days': (now - anchor_dt).days,
        'evaluated_now': now.isoformat(),
        'spearman_score_vs_delta': {'rho': rho, 'n': n_pairs},
        'tier_means': means,
        'tier_ordering_correct': (
            'STRONG_BUY' in means and 'PASS' in means and means['STRONG_BUY'] > means['PASS']
        ),
        'tier_summary': tier_summary,
    }


# Major scraper/scoring fix dates. Any anchor run BEFORE these dates carries
# noise from price-extraction artifacts that get "corrected" later — not real
# market movement. The backtest is most informative once the anchor is on or
# after the latest fix date.
_NOISE_FLOOR_DATES = [
    ('2026-04-25', 'v2.16.4 outlier-resistant Lamudi mean'),
    ('2026-04-25', 'v2.16.4 brotli accept-encoding fix (Antara revival)'),
    ('2026-04-25', 'v2.16.5 kulon-progo / gunung-kidul slug fix'),
    ('2026-04-25', 'v2.16.6 Medan Kuala Namu → deli-serdang slug'),
    ('2026-04-28', 'v2.16.7 11 region-specific benchmark overrides'),
    ('2026-04-28', 'v2.16.8 per-region history-anchored clamp'),
]


def print_methodology_note(result: Dict) -> None:
    anchor_date = datetime.fromisoformat(result['anchor_date']).date()
    cutoff = datetime.strptime(_NOISE_FLOOR_DATES[-1][0], '%Y-%m-%d').date()
    if anchor_date < cutoff:
        days_pre_cutoff = (cutoff - anchor_date).days
        print()
        print('  ⚠️  ANCHOR PRE-DATES MAJOR SCORING FIXES')
        print(f'      Anchor is {days_pre_cutoff}d before {cutoff} (last v2.16.x fix date).')
        print('      Many "price changes" in this window reflect scraper-extraction')
        print('      corrections rather than real market movement. Examples from this run:')
        print('        - kulon_progo "drop" = slug fix (urban Yogya → correct corridor)')
        print('        - jakarta/bekasi "drop" = outlier-resistant mean filtering misparses')
        print('      This window is included for completeness but is NOT yet a valid')
        print('      test of scoring predictiveness. Re-run after 4+ weeks of stable')
        print(f'      post-{cutoff} history accumulates.')


def print_summary(result: Dict) -> None:
    print()
    print('=' * 90)
    print(f"BACKTEST: {result['window_weeks']}-week window")
    print(f"  Anchor: {result['anchor_run']} ({result['anchor_age_days']} days ago)")
    print('=' * 90)
    print_methodology_note(result)

    means = result['tier_means']
    print(f"\nMean N-week price-change by tier (clean = listing_count stable within ±2×):")
    for tier in ('STRONG_BUY', 'BUY', 'WATCH', 'PASS'):
        ts = result['tier_summary'].get(tier, {})
        if tier in means:
            n_clean = ts['n_clean']
            n_shift = ts.get('n_shifted', 0)
            pos_pct = ts.get('positive_pct_clean', 0)
            shift_note = f", {n_shift} shifted-excluded" if n_shift else ""
            print(f"  {tier:11s} (n={n_clean:2d}{shift_note}):  {means[tier]:>+7.2f}%  ({pos_pct:.0f}% positive)")
        else:
            n_total = ts.get('n_total', ts.get('n', 0))
            print(f"  {tier:11s} (n={n_total:2d}):  insufficient clean sample")

    print()
    expected = '✅ MONOTONIC' if result['tier_ordering_correct'] else '❌ INVERTED or UNCLEAR'
    print(f"  Tier ordering (STRONG_BUY > PASS): {expected}")

    rho = result['spearman_score_vs_delta']['rho']
    n = result['spearman_score_vs_delta']['n']
    if rho == rho:  # not nan
        sign = '↑' if rho > 0 else '↓' if rho < 0 else '−'
        strength = (
            'strong predictive' if abs(rho) > 0.5 else
            'moderate' if abs(rho) > 0.3 else
            'weak' if abs(rho) > 0.1 else
            'noise'
        )
        print(f"  Spearman ρ(score, delta) = {rho:+.3f} {sign}  (n={n}, {strength})")
    else:
        print(f"  Spearman ρ: insufficient samples (n={n})")

    # Show the top movers per tier (where tier had enough samples). Mark
    # listing-shifted entries with * — those moves likely reflect scraper
    # coverage rather than market movement.
    for tier in ('STRONG_BUY', 'BUY'):
        ts = result['tier_summary'].get(tier, {})
        if 'top_3_regions' not in ts:
            continue
        print(f"\n  Top 3 {tier} performers (* = listing_count shifted ≥2×, suspect):")
        for r in ts['top_3_regions']:
            mark = '*' if r['listing_shift_flag'] else ' '
            print(f"   {mark}{r['region']:38s}  {r['delta_pct']:>+7.2f}%  "
                  f"(Rp {r['price_at_anchor']:>10,.0f} → Rp {r['price_now']:>10,.0f}, "
                  f"listings {r['listings_at_anchor']}→{r['listings_now']})")
        print(f"  Bottom 3 {tier} performers:")
        for r in ts['bottom_3_regions']:
            mark = '*' if r['listing_shift_flag'] else ' '
            print(f"   {mark}{r['region']:38s}  {r['delta_pct']:>+7.2f}%  "
                  f"(Rp {r['price_at_anchor']:>10,.0f} → Rp {r['price_now']:>10,.0f}, "
                  f"listings {r['listings_at_anchor']}→{r['listings_now']})")


def main() -> int:
    ap = argparse.ArgumentParser(description='CloudClearingAPI backtest harness')
    ap.add_argument('--window', type=int, default=None,
                    help='Single window in weeks (default: try 4 and 8)')
    ap.add_argument('--tolerance', type=int, default=5,
                    help='Days tolerance around target window (default: 5)')
    ap.add_argument('--out', type=Path, default=None,
                    help='Optional output JSON path')
    args = ap.parse_args()

    runs = []
    for path in RUN_DIR.glob('weekly_monitoring_*.json'):
        ts = parse_run_timestamp(path)
        if ts is not None:
            runs.append((ts, path))
    runs.sort()
    if not runs:
        print('ERROR: No weekly_monitoring_*.json files found in', RUN_DIR)
        return 1
    print(f'Loaded {len(runs)} historical runs '
          f'({runs[0][0].date()} → {runs[-1][0].date()})')

    # Default windows: 2w (post-v2.16.x era — cleanest signal), 4w (one
    # cycle), 8w (longer, but spans pre-fix era so noisier). Older windows
    # use a wider tolerance because run cadence was lower.
    if args.window:
        windows = [(args.window, args.tolerance)]
    else:
        windows = [(2, args.tolerance), (4, args.tolerance), (8, max(args.tolerance, 10))]
    results = []
    for w, tol in windows:
        result = backtest_window(runs, window_weeks=w, tolerance=tol)
        if result is None:
            print(f'\n  {w}-week window: no anchor run within ±{tol}d. Skipping.')
            continue
        print_summary(result)
        results.append(result)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = args.out or OUT_DIR / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, 'w') as f:
        json.dump({'generated': datetime.now().isoformat(), 'results': results}, f, indent=2, default=str)
    print(f'\nSaved: {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
