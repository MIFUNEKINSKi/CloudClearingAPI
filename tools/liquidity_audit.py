#!/usr/bin/env python3
"""
Liquidity audit tool — print observed listing-volume per region from
archived price-history JSONLs, with research-tier comparison.

Usage:
    python tools/liquidity_audit.py            # all regions, sorted by avg listings asc
    python tools/liquidity_audit.py --mismatch # only regions where research disagrees with observation
    python tools/liquidity_audit.py --thin     # only regions with avg listings < 10

Useful as a periodic input to refining region_feasibility profiles.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.liquidity_estimator import (
    PRICE_HISTORY_DIR, estimate_liquidity, liquidity_mismatch, liquidity_summary_label,
)
from src.core.region_feasibility import get_feasibility
from src.core.market_config import classify_region_tier


def main():
    ap = argparse.ArgumentParser(description='Per-region liquidity audit')
    ap.add_argument('--mismatch', action='store_true',
                    help='Only show regions where research and observed disagree')
    ap.add_argument('--thin', action='store_true',
                    help='Only show regions with avg < 10 listings/scrape')
    args = ap.parse_args()

    rows = []
    for f in sorted(Path(PRICE_HISTORY_DIR).glob('*.jsonl')):
        region = f.stem
        if region in {'bali', 'jakarta', 'yogyakarta'}:
            continue  # legacy aggregate buckets, not real regions
        feas = get_feasibility(region, tier=classify_region_tier(region))
        liq = estimate_liquidity(region)
        if liq.observed_tier == 'unknown':
            continue
        mm = liquidity_mismatch(feas.liquidity_tier, liq)
        rows.append((region, feas.liquidity_tier, liq, mm))

    if args.mismatch:
        rows = [r for r in rows if r[3]]
    if args.thin:
        rows = [r for r in rows if r[2].avg_listings < 10]

    rows.sort(key=lambda r: r[2].avg_listings)

    print(f"{'REGION':<40} {'RESEARCH':<10} {'OBSERVED':<14} {'avg':>5}  {'n':>3}  flag")
    print('-' * 95)
    for region, research_tier, liq, mm in rows:
        flag = '⚠ MISMATCH' if mm else ''
        print(f"{region:<40} {research_tier:<10} {liq.observed_tier:<14} "
              f"{liq.avg_listings:>5.1f}  {liq.n_samples:>3}  {flag}")
    print()
    print(f"Total: {len(rows)} regions")
    if args.mismatch and not rows:
        print('(no mismatches found — research and observed liquidity agree across the board)')


if __name__ == '__main__':
    main()
