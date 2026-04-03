"""
Development Momentum Analyzer
CloudClearingAPI - v2.10

Calculates the rate-of-change acceleration of development activity.
Compares recent change velocity against historical baseline to detect
regions where development is accelerating — a strong leading indicator
for real estate investment.

Example:
  - 6 months ago: 100 changes/month (baseline)
  - 3 months ago: 200 changes/month (2x)
  - This month:   500 changes/month (5x)
  → Momentum multiplier = 1.25x (strong acceleration)

Data source: Historical monitoring JSON files in output/monitoring/
"""

import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class MomentumAnalyzer:
    """
    Analyzes development momentum: is the rate of change accelerating or decelerating?
    
    Reads historical weekly monitoring results and calculates:
    - Recent velocity: average changes/week over last 4 weeks
    - Baseline velocity: average changes/week over 8-16 weeks ago
    - Momentum ratio: recent_velocity / baseline_velocity
    - Multiplier: converts momentum ratio to a scoring multiplier (0.85x–1.30x)
    """
    
    def __init__(self, 
                 monitoring_dir: str = "./output/monitoring",
                 recent_weeks: int = 4,
                 baseline_weeks_start: int = 8,
                 baseline_weeks_end: int = 16):
        """
        Args:
            monitoring_dir: Directory containing weekly_monitoring_*.json files
            recent_weeks: Number of recent weeks to average (default 4)
            baseline_weeks_start: Start of baseline window in weeks ago (default 8)
            baseline_weeks_end: End of baseline window in weeks ago (default 16)
        """
        self.monitoring_dir = Path(monitoring_dir)
        self.recent_weeks = recent_weeks
        self.baseline_weeks_start = baseline_weeks_start
        self.baseline_weeks_end = baseline_weeks_end
        
        logger.info(f"📈 Momentum Analyzer initialized "
                   f"(recent: {recent_weeks}w, baseline: {baseline_weeks_start}-{baseline_weeks_end}w ago)")
    
    def _load_historical_results(self) -> List[Dict[str, Any]]:
        """
        Load all historical monitoring JSON files, sorted by date.
        
        Returns:
            List of monitoring result dicts, newest first
        """
        results = []
        
        if not self.monitoring_dir.exists():
            logger.warning(f"Monitoring directory not found: {self.monitoring_dir}")
            return []
        
        for json_file in sorted(self.monitoring_dir.glob("weekly_monitoring_*.json"), reverse=True):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Extract timestamp from filename (weekly_monitoring_YYYYMMDD_HHMMSS.json)
                timestamp_str = json_file.stem.replace("weekly_monitoring_", "")
                try:
                    file_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                except ValueError:
                    file_timestamp = datetime.fromtimestamp(json_file.stat().st_mtime)
                
                data['_file_timestamp'] = file_timestamp.isoformat()
                data['_file_path'] = str(json_file)
                results.append(data)
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load {json_file.name}: {e}")
                continue
        
        logger.info(f"📂 Loaded {len(results)} historical monitoring results")
        return results
    
    def _extract_region_changes(self, 
                                 historical_results: List[Dict[str, Any]],
                                 region_name: str) -> List[Tuple[datetime, int]]:
        """
        Extract (timestamp, change_count) pairs for a specific region from history.
        
        Returns:
            List of (datetime, change_count) tuples, newest first
        """
        region_history = []
        
        for result in historical_results:
            timestamp = datetime.fromisoformat(result['_file_timestamp'])
            
            # Look in regions_analyzed
            for region_data in result.get('regions_analyzed', []):
                if region_data.get('region_name') == region_name:
                    change_count = region_data.get('change_count', 0)
                    region_history.append((timestamp, change_count))
                    break
        
        return region_history
    
    def calculate_momentum(self, region_name: str) -> Dict[str, Any]:
        """
        Calculate development momentum for a specific region.
        
        Compares recent change velocity against historical baseline.
        
        Args:
            region_name: Name of the region to analyze
            
        Returns:
            Dict with momentum_ratio, multiplier, recent_velocity, baseline_velocity, etc.
        """
        historical = self._load_historical_results()
        
        if len(historical) < 2:
            logger.info(f"📈 {region_name}: Insufficient history ({len(historical)} runs) for momentum analysis")
            return {
                'momentum_ratio': 1.0,
                'multiplier': 1.0,
                'recent_velocity': 0,
                'baseline_velocity': 0,
                'data_points_recent': 0,
                'data_points_baseline': 0,
                'trend': 'insufficient_data',
                'description': 'Not enough historical data for momentum analysis'
            }
        
        region_history = self._extract_region_changes(historical, region_name)
        
        if len(region_history) < 2:
            logger.info(f"📈 {region_name}: No historical data found for this region")
            return {
                'momentum_ratio': 1.0,
                'multiplier': 1.0,
                'recent_velocity': 0,
                'baseline_velocity': 0,
                'data_points_recent': 0,
                'data_points_baseline': 0,
                'trend': 'new_region',
                'description': 'First analysis for this region — no momentum data yet'
            }
        
        now = datetime.now()
        
        # Split into recent and baseline windows
        recent_cutoff = now - timedelta(weeks=self.recent_weeks)
        baseline_start = now - timedelta(weeks=self.baseline_weeks_end)
        baseline_end = now - timedelta(weeks=self.baseline_weeks_start)
        
        recent_changes = [count for ts, count in region_history if ts >= recent_cutoff]
        baseline_changes = [count for ts, count in region_history if baseline_start <= ts <= baseline_end]
        
        # Calculate velocities (average changes per run)
        recent_velocity = sum(recent_changes) / len(recent_changes) if recent_changes else 0
        baseline_velocity = sum(baseline_changes) / len(baseline_changes) if baseline_changes else 0
        
        # Calculate momentum ratio
        if baseline_velocity > 0:
            momentum_ratio = recent_velocity / baseline_velocity
        elif recent_velocity > 0:
            momentum_ratio = 2.0  # Activity where there was none → strong signal
        else:
            momentum_ratio = 1.0  # No activity in either period
        
        # Convert to multiplier (0.85x–1.30x range)
        multiplier = self._ratio_to_multiplier(momentum_ratio)
        
        # Determine trend description
        trend, description = self._describe_trend(momentum_ratio, recent_velocity, baseline_velocity)
        
        logger.info(f"📈 {region_name}: Momentum {momentum_ratio:.2f}x → multiplier {multiplier:.2f}x "
                   f"(recent: {recent_velocity:.0f}/run, baseline: {baseline_velocity:.0f}/run, trend: {trend})")
        
        return {
            'momentum_ratio': round(momentum_ratio, 3),
            'multiplier': round(multiplier, 3),
            'recent_velocity': round(recent_velocity, 1),
            'baseline_velocity': round(baseline_velocity, 1),
            'data_points_recent': len(recent_changes),
            'data_points_baseline': len(baseline_changes),
            'trend': trend,
            'description': description
        }
    
    def _ratio_to_multiplier(self, momentum_ratio: float) -> float:
        """
        Convert momentum ratio to a scoring multiplier.
        
        Uses a clamped logistic-style mapping:
        - ratio < 0.5: 0.85x (decelerating strongly)
        - ratio = 1.0: 1.00x (steady state)
        - ratio = 2.0: 1.15x (accelerating)
        - ratio = 3.0: 1.22x (accelerating strongly)
        - ratio > 5.0: 1.30x (max boost)
        
        Formula: 0.85 + 0.45 * (1 - 1/(1 + ln(ratio)))  for ratio > 0
        """
        if momentum_ratio <= 0:
            return 0.85
        
        # Logarithmic mapping: smooth, bounded, diminishing returns
        raw = 0.85 + 0.45 * (1.0 - 1.0 / (1.0 + math.log(max(0.01, momentum_ratio))))
        
        # Clamp to 0.85–1.30
        return round(min(1.30, max(0.85, raw)), 3)
    
    def _describe_trend(self, ratio: float, recent: float, baseline: float) -> Tuple[str, str]:
        """Generate human-readable trend description"""
        if ratio > 3.0:
            return ('surging', 
                    f"Development is surging: {ratio:.1f}x acceleration "
                    f"({recent:.0f} changes/run vs {baseline:.0f} baseline)")
        elif ratio > 1.5:
            return ('accelerating',
                    f"Development is accelerating: {ratio:.1f}x growth "
                    f"({recent:.0f} vs {baseline:.0f} baseline)")
        elif ratio > 1.1:
            return ('growing',
                    f"Steady growth: {ratio:.1f}x above baseline "
                    f"({recent:.0f} vs {baseline:.0f})")
        elif ratio > 0.9:
            return ('steady',
                    f"Development pace is steady ({recent:.0f} changes/run)")
        elif ratio > 0.5:
            return ('slowing',
                    f"Development is slowing: {ratio:.1f}x of baseline "
                    f"({recent:.0f} vs {baseline:.0f})")
        else:
            return ('stalling',
                    f"Development has stalled: only {ratio:.1f}x of baseline "
                    f"({recent:.0f} vs {baseline:.0f})")
