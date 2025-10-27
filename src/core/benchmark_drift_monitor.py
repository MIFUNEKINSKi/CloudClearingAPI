"""
Benchmark Drift Monitoring System for CloudClearingAPI v2.9

This module monitors drift between static tier benchmarks and live market prices,
enabling proactive recalibration to maintain RVI accuracy over time.

Key Features:
- Drift calculation: (live_price - benchmark) / benchmark * 100
- Persistence-based alerts: WARNING (>10% for 4+ weeks), CRITICAL (>20% for 2+ weeks)
- JSON-based history tracking with 6-month rolling retention
- Zero additional API calls (post-processing only)
- Admin-approved recalibration workflow

Author: CloudClearingAPI Team
Date: October 27, 2025
Version: 2.9.0 (CCAPI-27.2)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from .market_config import get_tier_benchmark, classify_region_tier

logger = logging.getLogger(__name__)


@dataclass
class DriftSnapshot:
    """Single drift measurement snapshot"""
    timestamp: str
    region_name: str
    tier: str
    benchmark_price: float
    live_price: float
    drift_pct: float
    data_source: str
    confidence: float
    alert_level: str  # 'NONE', 'WARNING', 'CRITICAL'


@dataclass
class DriftAlert:
    """Drift alert for regions requiring attention"""
    region_name: str
    tier: str
    current_drift_pct: float
    consecutive_weeks: int
    alert_level: str  # 'WARNING' or 'CRITICAL'
    first_detected: str
    latest_snapshot: str
    avg_drift_pct: float
    recommendation: str


class BenchmarkDriftMonitor:
    """
    Monitors drift between static tier benchmarks and live market prices.
    
    Workflow:
    1. After weekly monitoring completes, call track_drift(results)
    2. For each region with live price data, calculate drift vs benchmark
    3. Append drift snapshot to region's history file
    4. Check alert thresholds (persistence-based: 4+ weeks WARNING, 2+ CRITICAL)
    5. Generate drift summary report with alerts
    6. Admin reviews alerts and triggers recalibration if needed
    """
    
    def __init__(
        self,
        history_dir: str = "./data/benchmark_drift",
        retention_days: int = 180,  # 6 months default
        enable_alerts: bool = True
    ):
        """
        Initialize drift monitor.
        
        Args:
            history_dir: Directory for drift history JSON files
            retention_days: Days of history to retain (default 180 = 6 months)
            enable_alerts: Enable alert threshold checking
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.enable_alerts = enable_alerts
        
        # Alert thresholds (persistence-based to avoid false positives)
        self.alert_thresholds = {
            'WARNING': {
                'drift_pct': 10.0,  # >10% drift
                'min_weeks': 4      # For 4+ consecutive weeks
            },
            'CRITICAL': {
                'drift_pct': 20.0,  # >20% drift
                'min_weeks': 2      # For 2+ consecutive weeks
            }
        }
        
        logger.info(f"✅ BenchmarkDriftMonitor initialized: {self.history_dir}")
        logger.info(f"   Retention: {retention_days} days, Alerts: {enable_alerts}")
    
    def calculate_drift(
        self,
        region_name: str,
        live_price: float,
        data_source: str = "unknown",
        confidence: float = 0.75
    ) -> Optional[DriftSnapshot]:
        """
        Calculate drift for a single region.
        
        Args:
            region_name: Region identifier
            live_price: Live market price (IDR/m²)
            data_source: Source of live price (e.g., "Lamudi", "Rumah123")
            confidence: Confidence level of live price (0.0-1.0)
        
        Returns:
            DriftSnapshot or None if benchmark not found
        """
        try:
            # Get tier and benchmark for this region
            tier = classify_region_tier(region_name)
            if not tier:
                logger.warning(f"⚠️ Region {region_name} not found in tier classification")
                return None
            
            benchmark_price = get_tier_benchmark(tier)
            if not benchmark_price:
                logger.warning(f"⚠️ No benchmark found for tier {tier}")
                return None
            
            # Calculate drift percentage
            drift_pct = ((live_price - benchmark_price) / benchmark_price) * 100
            
            # Check alert level
            alert_level = self._classify_alert_level(drift_pct)
            
            snapshot = DriftSnapshot(
                timestamp=datetime.now().isoformat(),
                region_name=region_name,
                tier=tier,
                benchmark_price=benchmark_price,
                live_price=live_price,
                drift_pct=drift_pct,
                data_source=data_source,
                confidence=confidence,
                alert_level=alert_level
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate drift for {region_name}: {e}")
            return None
    
    def track_drift(
        self,
        regions_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track drift for multiple regions (called after weekly monitoring).
        
        Args:
            regions_data: List of region analysis results with financial projections
        
        Returns:
            Drift summary with alerts and statistics
        """
        logger.info("📊 Tracking benchmark drift across regions...")
        
        tracked_count = 0
        alerts = []
        drift_snapshots = []
        
        for region_data in regions_data:
            try:
                region_name = region_data.get('region_name')
                if not region_name:
                    continue
                
                # Extract live price from financial projection or dynamic score
                live_price = self._extract_live_price(region_data)
                if not live_price:
                    logger.debug(f"   No live price data for {region_name}, skipping")
                    continue
                
                # Extract data source and confidence
                data_source = self._extract_data_source(region_data)
                confidence = self._extract_confidence(region_data)
                
                # Calculate drift
                snapshot = self.calculate_drift(
                    region_name=region_name,
                    live_price=live_price,
                    data_source=data_source,
                    confidence=confidence
                )
                
                if snapshot:
                    # Save to history
                    self._save_drift_snapshot(snapshot)
                    drift_snapshots.append(snapshot)
                    tracked_count += 1
                    
                    logger.debug(f"   ✅ {region_name}: {snapshot.drift_pct:+.1f}% drift "
                                f"(Live: Rp {live_price/1e6:.1f}M, Bench: Rp {snapshot.benchmark_price/1e6:.1f}M)")
                    
            except Exception as e:
                logger.error(f"❌ Failed to track drift for {region_data.get('region_name', 'unknown')}: {e}")
                continue
        
        # Check for persistent drift alerts
        if self.enable_alerts and tracked_count > 0:
            alerts = self._check_drift_alerts()
        
        # Generate summary
        summary = self._generate_drift_summary(drift_snapshots, alerts)
        
        logger.info(f"✅ Drift tracking complete: {tracked_count} regions tracked, {len(alerts)} alerts")
        
        return summary
    
    def _save_drift_snapshot(self, snapshot: DriftSnapshot) -> None:
        """Append drift snapshot to region's history file"""
        try:
            history_file = self.history_dir / f"{snapshot.region_name}_drift_history.json"
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {
                    'region_name': snapshot.region_name,
                    'tier': snapshot.tier,
                    'snapshots': []
                }
            
            # Append new snapshot
            history['snapshots'].append(asdict(snapshot))
            
            # Cleanup old snapshots (retention policy)
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            history['snapshots'] = [
                s for s in history['snapshots']
                if datetime.fromisoformat(s['timestamp']) > cutoff_date
            ]
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save drift snapshot for {snapshot.region_name}: {e}")
    
    def get_drift_history(
        self,
        region_name: str,
        days: int = 30
    ) -> List[DriftSnapshot]:
        """
        Get drift history for a region.
        
        Args:
            region_name: Region identifier
            days: Number of days of history to retrieve
        
        Returns:
            List of DriftSnapshot objects (most recent first)
        """
        try:
            history_file = self.history_dir / f"{region_name}_drift_history.json"
            if not history_file.exists():
                return []
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            snapshots = [
                DriftSnapshot(**s) for s in history['snapshots']
                if datetime.fromisoformat(s['timestamp']) > cutoff_date
            ]
            
            # Sort by timestamp descending (most recent first)
            snapshots.sort(key=lambda x: x.timestamp, reverse=True)
            
            return snapshots
            
        except Exception as e:
            logger.error(f"❌ Failed to get drift history for {region_name}: {e}")
            return []
    
    def _check_drift_alerts(self) -> List[DriftAlert]:
        """
        Check all regions for persistent drift alerts.
        
        Returns:
            List of DriftAlert objects for regions requiring attention
        """
        alerts = []
        
        try:
            # Check all region history files
            for history_file in self.history_dir.glob("*_drift_history.json"):
                try:
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                    
                    region_name = history['region_name']
                    tier = history['tier']
                    snapshots = history['snapshots']
                    
                    if not snapshots:
                        continue
                    
                    # Get recent snapshots (last 8 weeks for checking persistence)
                    recent_snapshots = [
                        DriftSnapshot(**s) for s in snapshots[-8:]
                        if datetime.fromisoformat(s['timestamp']) > datetime.now() - timedelta(days=60)
                    ]
                    
                    if not recent_snapshots:
                        continue
                    
                    # Check for CRITICAL alert (>20% for 2+ weeks)
                    critical_consecutive = self._count_consecutive_drift(
                        recent_snapshots,
                        self.alert_thresholds['CRITICAL']['drift_pct']
                    )
                    
                    if critical_consecutive >= self.alert_thresholds['CRITICAL']['min_weeks']:
                        alert = self._create_drift_alert(
                            region_name, tier, recent_snapshots, 'CRITICAL', critical_consecutive
                        )
                        alerts.append(alert)
                        continue  # Skip WARNING check if already CRITICAL
                    
                    # Check for WARNING alert (>10% for 4+ weeks)
                    warning_consecutive = self._count_consecutive_drift(
                        recent_snapshots,
                        self.alert_thresholds['WARNING']['drift_pct']
                    )
                    
                    if warning_consecutive >= self.alert_thresholds['WARNING']['min_weeks']:
                        alert = self._create_drift_alert(
                            region_name, tier, recent_snapshots, 'WARNING', warning_consecutive
                        )
                        alerts.append(alert)
                        
                except Exception as e:
                    logger.error(f"❌ Error checking alerts for {history_file.name}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Failed to check drift alerts: {e}")
        
        # Sort alerts by severity and drift magnitude
        alerts.sort(key=lambda x: (
            0 if x.alert_level == 'CRITICAL' else 1,
            -abs(x.current_drift_pct)
        ))
        
        return alerts
    
    def _count_consecutive_drift(
        self,
        snapshots: List[DriftSnapshot],
        threshold: float
    ) -> int:
        """Count consecutive weeks with drift above threshold"""
        if not snapshots:
            return 0
        
        # Sort by timestamp descending (most recent first)
        sorted_snapshots = sorted(snapshots, key=lambda x: x.timestamp, reverse=True)
        
        consecutive = 0
        for snapshot in sorted_snapshots:
            if abs(snapshot.drift_pct) > threshold:
                consecutive += 1
            else:
                break  # Stop at first non-exceeding snapshot
        
        return consecutive
    
    def _create_drift_alert(
        self,
        region_name: str,
        tier: str,
        recent_snapshots: List[DriftSnapshot],
        alert_level: str,
        consecutive_weeks: int
    ) -> DriftAlert:
        """Create DriftAlert object from snapshots"""
        latest = recent_snapshots[-1]
        first_detected = recent_snapshots[-consecutive_weeks].timestamp
        
        # Calculate average drift over consecutive weeks
        avg_drift = sum(s.drift_pct for s in recent_snapshots[-consecutive_weeks:]) / consecutive_weeks
        
        # Generate recommendation
        if alert_level == 'CRITICAL':
            recommendation = f"URGENT: Benchmark recalibration required. Drift >20% for {consecutive_weeks}+ weeks."
        else:
            recommendation = f"Review benchmark accuracy. Drift >10% for {consecutive_weeks}+ weeks."
        
        return DriftAlert(
            region_name=region_name,
            tier=tier,
            current_drift_pct=latest.drift_pct,
            consecutive_weeks=consecutive_weeks,
            alert_level=alert_level,
            first_detected=first_detected,
            latest_snapshot=latest.timestamp,
            avg_drift_pct=avg_drift,
            recommendation=recommendation
        )
    
    def _generate_drift_summary(
        self,
        snapshots: List[DriftSnapshot],
        alerts: List[DriftAlert]
    ) -> Dict[str, Any]:
        """Generate drift summary with statistics and alerts"""
        if not snapshots:
            return {
                'status': 'no_data',
                'message': 'No drift data to summarize',
                'alerts': []
            }
        
        # Per-tier statistics
        tier_stats = defaultdict(lambda: {
            'count': 0,
            'avg_drift': 0.0,
            'max_drift': 0.0,
            'min_drift': 0.0,
            'regions': []
        })
        
        for snapshot in snapshots:
            tier = snapshot.tier
            tier_stats[tier]['count'] += 1
            tier_stats[tier]['regions'].append(snapshot.region_name)
            
            # Update min/max
            if tier_stats[tier]['count'] == 1:
                tier_stats[tier]['max_drift'] = snapshot.drift_pct
                tier_stats[tier]['min_drift'] = snapshot.drift_pct
            else:
                tier_stats[tier]['max_drift'] = max(tier_stats[tier]['max_drift'], snapshot.drift_pct)
                tier_stats[tier]['min_drift'] = min(tier_stats[tier]['min_drift'], snapshot.drift_pct)
        
        # Calculate average drift per tier
        for tier in tier_stats:
            tier_snapshots = [s for s in snapshots if s.tier == tier]
            tier_stats[tier]['avg_drift'] = sum(s.drift_pct for s in tier_snapshots) / len(tier_snapshots)
        
        # Overall statistics
        all_drifts = [s.drift_pct for s in snapshots]
        
        summary = {
            'status': 'complete',
            'timestamp': datetime.now().isoformat(),
            'regions_tracked': len(snapshots),
            'overall_stats': {
                'avg_drift_pct': sum(all_drifts) / len(all_drifts),
                'max_drift_pct': max(all_drifts),
                'min_drift_pct': min(all_drifts),
                'regions_above_10pct': sum(1 for d in all_drifts if abs(d) > 10),
                'regions_above_20pct': sum(1 for d in all_drifts if abs(d) > 20)
            },
            'tier_stats': dict(tier_stats),
            'alerts': {
                'total': len(alerts),
                'critical': len([a for a in alerts if a.alert_level == 'CRITICAL']),
                'warning': len([a for a in alerts if a.alert_level == 'WARNING']),
                'details': [asdict(a) for a in alerts]
            }
        }
        
        return summary
    
    def get_tier_drift_summary(self, tier: str, days: int = 30) -> Dict[str, Any]:
        """
        Get drift summary for all regions in a tier.
        
        Args:
            tier: Tier identifier (e.g., 'tier_1_metros')
            days: Days of history to analyze
        
        Returns:
            Tier-level drift statistics
        """
        tier_snapshots = []
        
        try:
            for history_file in self.history_dir.glob("*_drift_history.json"):
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                if history.get('tier') == tier:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    region_snapshots = [
                        DriftSnapshot(**s) for s in history['snapshots']
                        if datetime.fromisoformat(s['timestamp']) > cutoff_date
                    ]
                    tier_snapshots.extend(region_snapshots)
            
            if not tier_snapshots:
                return {'tier': tier, 'status': 'no_data', 'regions_count': 0}
            
            # Calculate statistics
            drifts = [s.drift_pct for s in tier_snapshots]
            regions = list(set(s.region_name for s in tier_snapshots))
            
            # Calculate 30-day rolling average (smoothed)
            recent_30d = [s for s in tier_snapshots 
                         if datetime.fromisoformat(s.timestamp) > datetime.now() - timedelta(days=30)]
            smoothed_drift = sum(s.drift_pct for s in recent_30d) / len(recent_30d) if recent_30d else 0
            
            return {
                'tier': tier,
                'status': 'complete',
                'regions_count': len(regions),
                'regions': regions,
                'avg_drift_pct': sum(drifts) / len(drifts),
                'smoothed_drift_30d': smoothed_drift,
                'max_drift_pct': max(drifts),
                'min_drift_pct': min(drifts),
                'snapshots_count': len(tier_snapshots)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get tier drift summary for {tier}: {e}")
            return {'tier': tier, 'status': 'error', 'error': str(e)}
    
    def generate_recalibration_recommendations(self) -> Dict[str, Any]:
        """
        Generate benchmark recalibration recommendations based on drift analysis.
        
        Returns:
            Proposed benchmark updates with justification
        """
        logger.info("📋 Generating benchmark recalibration recommendations...")
        
        recommendations = {
            'timestamp': datetime.now().isoformat(),
            'analysis_period_days': 30,
            'tier_recommendations': [],
            'requires_recalibration': False
        }
        
        try:
            # Analyze each tier
            tiers = ['tier_1_metros', 'tier_2_secondary', 'tier_3_emerging', 'tier_4_frontier']
            
            for tier in tiers:
                tier_summary = self.get_tier_drift_summary(tier, days=30)
                
                if tier_summary['status'] != 'complete':
                    continue
                
                smoothed_drift = tier_summary['smoothed_drift_30d']
                current_benchmark = get_tier_benchmark(tier)
                
                # Propose new benchmark if drift is significant
                if abs(smoothed_drift) > 10:
                    proposed_benchmark = current_benchmark * (1 + smoothed_drift / 100)
                    
                    recommendations['tier_recommendations'].append({
                        'tier': tier,
                        'current_benchmark': current_benchmark,
                        'proposed_benchmark': proposed_benchmark,
                        'drift_pct': smoothed_drift,
                        'change_amount': proposed_benchmark - current_benchmark,
                        'justification': f"30-day smoothed drift: {smoothed_drift:+.1f}%",
                        'urgency': 'HIGH' if abs(smoothed_drift) > 20 else 'MEDIUM',
                        'regions_affected': tier_summary['regions']
                    })
                    
                    recommendations['requires_recalibration'] = True
        
        except Exception as e:
            logger.error(f"❌ Failed to generate recalibration recommendations: {e}")
            recommendations['error'] = str(e)
        
        return recommendations
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _classify_alert_level(self, drift_pct: float) -> str:
        """Classify single drift measurement (not persistence-based)"""
        abs_drift = abs(drift_pct)
        if abs_drift > self.alert_thresholds['CRITICAL']['drift_pct']:
            return 'CRITICAL'
        elif abs_drift > self.alert_thresholds['WARNING']['drift_pct']:
            return 'WARNING'
        else:
            return 'NONE'
    
    def _extract_live_price(self, region_data: Dict[str, Any]) -> Optional[float]:
        """Extract live price from region analysis data"""
        # Try financial projection first
        financial = region_data.get('financial_projection')
        if financial and isinstance(financial, dict):
            live_price = financial.get('current_land_value_per_m2')
            if live_price and live_price > 0:
                return float(live_price)
        
        # Try dynamic score breakdown
        dynamic_score = region_data.get('dynamic_score', {})
        if isinstance(dynamic_score, dict):
            financial_data = dynamic_score.get('financial_projection', {})
            if isinstance(financial_data, dict):
                live_price = financial_data.get('current_land_value_per_m2')
                if live_price and live_price > 0:
                    return float(live_price)
        
        return None
    
    def _extract_data_source(self, region_data: Dict[str, Any]) -> str:
        """Extract data source from region analysis data"""
        financial = region_data.get('financial_projection', {})
        if isinstance(financial, dict):
            sources = financial.get('data_sources', [])
            if sources:
                return sources[0] if isinstance(sources, list) else str(sources)
        
        return "unknown"
    
    def _extract_confidence(self, region_data: Dict[str, Any]) -> float:
        """Extract confidence from region analysis data"""
        # Try dynamic score confidence
        dynamic_score = region_data.get('dynamic_score', {})
        if isinstance(dynamic_score, dict):
            confidence = dynamic_score.get('dynamic_confidence')
            if confidence:
                return float(confidence)
        
        # Try financial projection confidence
        financial = region_data.get('financial_projection', {})
        if isinstance(financial, dict):
            confidence = financial.get('confidence_level')
            if confidence:
                return float(confidence)
        
        return 0.75  # Default moderate confidence
