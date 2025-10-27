#!/usr/bin/env python3
"""
Auto-confirmed monitoring run (bypasses user prompt)
"""
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/java_weekly_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run weekly monitoring for ALL Java regions (auto-confirmed)"""
    
    from src.core.automated_monitor import AutomatedMonitor
    from src.regions import RegionManager
    
    print("\n🚀 Starting Java-wide monitoring (auto-confirmed)...")
    print(f"⏱️  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Expected Duration: ~87 minutes for 29 regions\n")
    
    # Initialize monitor
    monitor = AutomatedMonitor()
    region_manager = RegionManager()
    
    # Get Java regions
    from src.indonesia_expansion_regions import get_expansion_manager
    expansion_manager = get_expansion_manager()
    java_regions = expansion_manager.get_java_regions()
    
    # Extract region names
    java_region_names = [r.name for r in java_regions]
    
    logger.info(f"✅ Configured with {len(java_region_names)} Java regions")
    
    # Run monitoring
    results = await monitor.run_weekly_monitoring()
    
    print(f"\n✅ Monitoring complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Results: {results}\n")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
