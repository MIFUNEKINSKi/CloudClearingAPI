#!/usr/bin/env python3
"""
Manual runner for weekly automated monitoring
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

import ee
from core.config import get_config

def initialize_earth_engine():
    """Initialize Google Earth Engine"""
    config = get_config()
    project_id = config.gee_project
    
    print(f'🔧 Using GEE project: {project_id}')
    
    try:
        ee.Initialize(project=project_id)
        print('✅ Earth Engine initialized successfully')
        return True
    except Exception as e:
        print(f'❌ Earth Engine initialization failed: {e}')
        print('📝 You may need to run: earthengine authenticate')
        return False

async def main():
    """Main runner function"""
    print("🤖 CloudClearing Automated Monitor")
    print("==================================")
    
    # Initialize Earth Engine
    if not initialize_earth_engine():
        sys.exit(1)
    
    # Import and run the monitoring CLI
    try:
        from core.automated_monitor import run_monitoring_cli
        print('🚀 Starting weekly automated monitoring...')
        await run_monitoring_cli()
    except Exception as e:
        print(f"❌ Monitoring failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())