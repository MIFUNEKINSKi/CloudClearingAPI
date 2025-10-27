#!/usr/bin/env python3
"""
Benchmark Recalibration Tool for CloudClearingAPI v2.9

Admin tool for reviewing drift alerts and updating tier benchmarks in market_config.py.

Workflow:
1. Review drift alerts and recommendations
2. Validate live price data quality
3. Propose new benchmarks (30-day rolling average)
4. Generate diff report (old vs new)
5. Update market_config.py with new values
6. Backup old values for rollback

Usage:
    python tools/recalibrate_benchmarks.py review           # Review current drift
    python tools/recalibrate_benchmarks.py propose          # Generate recommendations
    python tools/recalibrate_benchmarks.py apply --tier=<tier>  # Apply recalibration
    python tools/recalibrate_benchmarks.py rollback         # Rollback last change

Author: CloudClearingAPI Team
Date: October 27, 2025
Version: 2.9.0 (CCAPI-27.2)
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.benchmark_drift_monitor import BenchmarkDriftMonitor
from src.core.market_config import get_tier_benchmark, REGIONAL_HIERARCHY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkRecalibrator:
    """
    Admin tool for benchmark recalibration based on drift analysis.
    """
    
    def __init__(self):
        """Initialize recalibrator"""
        self.drift_monitor = BenchmarkDriftMonitor(
            history_dir="./data/benchmark_drift",
            retention_days=180,
            enable_alerts=True
        )
        self.market_config_path = Path("src/core/market_config.py")
        self.backup_dir = Path("data/benchmark_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def review_drift(self) -> Dict[str, Any]:
        """
        Review current drift status across all tiers.
        
        Returns:
            Drift review summary
        """
        print("\n" + "="*80)
        print("📊 BENCHMARK DRIFT REVIEW")
        print("="*80 + "\n")
        
        tiers = ['tier_1_metros', 'tier_2_secondary', 'tier_3_emerging', 'tier_4_frontier']
        tier_names = {
            'tier_1_metros': 'Tier 1 (Metros)',
            'tier_2_secondary': 'Tier 2 (Secondary Cities)',
            'tier_3_emerging': 'Tier 3 (Emerging Corridors)',
            'tier_4_frontier': 'Tier 4 (Frontier Regions)'
        }
        
        review = {
            'timestamp': datetime.now().isoformat(),
            'tiers': {},
            'requires_action': False
        }
        
        for tier in tiers:
            tier_summary = self.drift_monitor.get_tier_drift_summary(tier, days=30)
            
            if tier_summary['status'] != 'complete':
                print(f"⚪ {tier_names[tier]}: No data available")
                continue
            
            current_benchmark = get_tier_benchmark(tier)
            avg_drift = tier_summary['avg_drift_pct']
            smoothed_drift = tier_summary['smoothed_drift_30d']
            regions_count = tier_summary['regions_count']
            
            # Determine status
            if abs(smoothed_drift) > 20:
                status = "🔴 CRITICAL"
                review['requires_action'] = True
            elif abs(smoothed_drift) > 10:
                status = "🟡 WARNING"
                review['requires_action'] = True
            else:
                status = "🟢 HEALTHY"
            
            print(f"{status} {tier_names[tier]}")
            print(f"   Current Benchmark: Rp {current_benchmark/1e6:.1f}M/m²")
            print(f"   30-Day Smoothed Drift: {smoothed_drift:+.1f}%")
            print(f"   Average Drift: {avg_drift:+.1f}%")
            print(f"   Regions Tracked: {regions_count}")
            print(f"   Max Drift: {tier_summary['max_drift_pct']:+.1f}%")
            print(f"   Min Drift: {tier_summary['min_drift_pct']:+.1f}%")
            
            if abs(smoothed_drift) > 10:
                proposed = current_benchmark * (1 + smoothed_drift / 100)
                print(f"   💡 Proposed Benchmark: Rp {proposed/1e6:.1f}M/m² "
                      f"({(proposed - current_benchmark)/1e6:+.2f}M change)")
            
            print()
            
            review['tiers'][tier] = {
                'current_benchmark': current_benchmark,
                'avg_drift': avg_drift,
                'smoothed_drift': smoothed_drift,
                'status': status,
                'regions_count': regions_count
            }
        
        # Check for drift alerts
        alerts_file = self.drift_monitor.history_dir / "current_alerts.json"
        if alerts_file.exists():
            with open(alerts_file, 'r') as f:
                alerts_data = json.load(f)
                alert_count = alerts_data.get('total', 0)
                
                if alert_count > 0:
                    print("⚠️  ACTIVE DRIFT ALERTS:")
                    print(f"   Total: {alert_count} "
                          f"({alerts_data.get('critical', 0)} CRITICAL, "
                          f"{alerts_data.get('warning', 0)} WARNING)")
                    print()
        
        print("="*80)
        
        if review['requires_action']:
            print("\n⚠️  ACTION REQUIRED: One or more tiers show significant drift")
            print("   Run: python tools/recalibrate_benchmarks.py propose")
            print()
        else:
            print("\n✅ All benchmarks are healthy - no recalibration needed")
            print()
        
        return review
    
    def propose_recalibration(self) -> Dict[str, Any]:
        """
        Generate recalibration recommendations.
        
        Returns:
            Proposed benchmark updates
        """
        print("\n" + "="*80)
        print("💡 BENCHMARK RECALIBRATION RECOMMENDATIONS")
        print("="*80 + "\n")
        
        recommendations = self.drift_monitor.generate_recalibration_recommendations()
        
        if not recommendations.get('requires_recalibration'):
            print("✅ No recalibration needed - all tiers within acceptable drift")
            print()
            return recommendations
        
        print("The following tier benchmarks show significant drift:\n")
        
        for rec in recommendations.get('tier_recommendations', []):
            tier = rec['tier']
            current = rec['current_benchmark']
            proposed = rec['proposed_benchmark']
            drift = rec['drift_pct']
            urgency = rec['urgency']
            
            urgency_icon = "🔴" if urgency == "HIGH" else "🟡"
            
            print(f"{urgency_icon} {tier.upper().replace('_', ' ')}")
            print(f"   Current:  Rp {current/1e6:.1f}M/m²")
            print(f"   Proposed: Rp {proposed/1e6:.1f}M/m² ({drift:+.1f}% change)")
            print(f"   Justification: {rec['justification']}")
            print(f"   Regions Affected: {len(rec['regions_affected'])}")
            print(f"   Urgency: {urgency}")
            print()
        
        print("="*80)
        print("\n📋 NEXT STEPS:")
        print("   1. Review proposed changes above")
        print("   2. Validate data quality for affected regions")
        print("   3. Apply recalibration: python tools/recalibrate_benchmarks.py apply --tier=<tier>")
        print("   4. Or apply all: python tools/recalibrate_benchmarks.py apply --all")
        print()
        
        # Save recommendations
        rec_file = self.backup_dir / f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(rec_file, 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        print(f"💾 Recommendations saved to: {rec_file}")
        print()
        
        return recommendations
    
    def apply_recalibration(self, tier: Optional[str] = None, apply_all: bool = False) -> bool:
        """
        Apply benchmark recalibration.
        
        Args:
            tier: Specific tier to update (or None for all)
            apply_all: Apply to all tiers with recommendations
        
        Returns:
            True if successful
        """
        print("\n" + "="*80)
        print("⚙️  APPLYING BENCHMARK RECALIBRATION")
        print("="*80 + "\n")
        
        # Generate recommendations
        recommendations = self.drift_monitor.generate_recalibration_recommendations()
        
        if not recommendations.get('requires_recalibration'):
            print("❌ No recalibration needed")
            return False
        
        tier_recs = recommendations.get('tier_recommendations', [])
        
        # Filter recommendations
        if tier:
            tier_recs = [r for r in tier_recs if r['tier'] == tier]
            if not tier_recs:
                print(f"❌ No recommendations found for tier: {tier}")
                return False
        elif not apply_all:
            print("❌ Must specify --tier=<tier> or --all")
            return False
        
        # Show what will be updated
        print("📝 The following changes will be applied:\n")
        for rec in tier_recs:
            current = rec['current_benchmark']
            proposed = rec['proposed_benchmark']
            drift = rec['drift_pct']
            
            print(f"   {rec['tier']}")
            print(f"      {current/1e6:.1f}M → {proposed/1e6:.1f}M ({drift:+.1f}%)")
        
        print()
        response = input("⚠️  Confirm recalibration? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n❌ Recalibration cancelled")
            return False
        
        # Backup current market_config.py
        backup_path = self._backup_market_config()
        print(f"\n💾 Backed up current config to: {backup_path}")
        
        # Apply changes
        try:
            self._update_market_config(tier_recs)
            
            print("\n✅ Benchmark recalibration applied successfully!")
            print()
            print("📋 NEXT STEPS:")
            print("   1. Run weekly monitoring to validate new benchmarks")
            print("   2. Monitor drift over next 2-4 weeks")
            print("   3. If issues arise, rollback: python tools/recalibrate_benchmarks.py rollback")
            print()
            print("="*80)
            print()
            
            # Log recalibration
            self._log_recalibration(tier_recs, backup_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply recalibration: {e}")
            print(f"\n❌ Recalibration failed: {e}")
            print(f"   Config backup available at: {backup_path}")
            return False
    
    def rollback(self) -> bool:
        """
        Rollback to previous benchmark configuration.
        
        Returns:
            True if successful
        """
        print("\n" + "="*80)
        print("⏮️  ROLLBACK BENCHMARK RECALIBRATION")
        print("="*80 + "\n")
        
        # Find most recent backup
        backups = sorted(self.backup_dir.glob("market_config_*.py"), reverse=True)
        
        if not backups:
            print("❌ No backups found")
            return False
        
        latest_backup = backups[0]
        backup_timestamp = latest_backup.stem.replace('market_config_', '')
        
        print(f"📁 Latest backup: {latest_backup.name}")
        print(f"   Created: {backup_timestamp}")
        print()
        
        response = input("⚠️  Confirm rollback to this backup? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n❌ Rollback cancelled")
            return False
        
        try:
            # Backup current state before rollback
            current_backup = self._backup_market_config(prefix="pre_rollback")
            
            # Restore from backup
            shutil.copy2(latest_backup, self.market_config_path)
            
            print(f"\n✅ Rolled back to {backup_timestamp}")
            print(f"💾 Current state backed up to: {current_backup.name}")
            print()
            print("="*80)
            print()
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            print(f"\n❌ Rollback failed: {e}")
            return False
    
    def _backup_market_config(self, prefix: str = "market_config") -> Path:
        """Create timestamped backup of market_config.py"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"{prefix}_{timestamp}.py"
        shutil.copy2(self.market_config_path, backup_path)
        return backup_path
    
    def _update_market_config(self, recommendations: List[Dict[str, Any]]) -> None:
        """
        Update benchmark values in market_config.py
        
        Args:
            recommendations: List of tier recommendations with new benchmarks
        """
        # Read current config
        with open(self.market_config_path, 'r') as f:
            config_lines = f.readlines()
        
        # Update benchmark values
        for rec in recommendations:
            tier = rec['tier']
            new_benchmark = int(rec['proposed_benchmark'])
            
            # Find the benchmarks section for this tier
            # Pattern: 'avg_price_m2': 8_000_000,
            old_benchmark = int(rec['current_benchmark'])
            old_pattern = f"'avg_price_m2': {old_benchmark:_},"
            new_pattern = f"'avg_price_m2': {new_benchmark:_},"
            
            # Update in config lines
            for i, line in enumerate(config_lines):
                if old_pattern in line and tier in ''.join(config_lines[max(0, i-50):i]):
                    config_lines[i] = line.replace(old_pattern, new_pattern)
                    logger.info(f"Updated {tier}: {old_benchmark:,} → {new_benchmark:,}")
                    break
        
        # Write updated config
        with open(self.market_config_path, 'w') as f:
            f.writelines(config_lines)
    
    def _log_recalibration(self, recommendations: List[Dict[str, Any]], backup_path: Path) -> None:
        """Log recalibration to history file"""
        log_file = self.backup_dir / "recalibration_history.json"
        
        history = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                history = json.load(f)
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'backup_file': backup_path.name,
            'changes': [
                {
                    'tier': rec['tier'],
                    'old_benchmark': rec['current_benchmark'],
                    'new_benchmark': rec['proposed_benchmark'],
                    'drift_pct': rec['drift_pct'],
                    'justification': rec['justification']
                }
                for rec in recommendations
            ]
        }
        
        history.append(entry)
        
        with open(log_file, 'w') as f:
            json.dump(history, f, indent=2)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark Recalibration Tool for CloudClearingAPI v2.9",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/recalibrate_benchmarks.py review
  python tools/recalibrate_benchmarks.py propose
  python tools/recalibrate_benchmarks.py apply --tier=tier_1_metros
  python tools/recalibrate_benchmarks.py apply --all
  python tools/recalibrate_benchmarks.py rollback
        """
    )
    
    parser.add_argument(
        'command',
        choices=['review', 'propose', 'apply', 'rollback'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--tier',
        type=str,
        help='Specific tier to recalibrate (tier_1_metros, tier_2_secondary, etc.)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Apply recalibration to all tiers with recommendations'
    )
    
    args = parser.parse_args()
    
    recalibrator = BenchmarkRecalibrator()
    
    try:
        if args.command == 'review':
            recalibrator.review_drift()
        
        elif args.command == 'propose':
            recalibrator.propose_recalibration()
        
        elif args.command == 'apply':
            success = recalibrator.apply_recalibration(
                tier=args.tier,
                apply_all=args.all
            )
            sys.exit(0 if success else 1)
        
        elif args.command == 'rollback':
            success = recalibrator.rollback()
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
