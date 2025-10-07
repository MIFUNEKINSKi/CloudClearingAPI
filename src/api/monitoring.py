"""
Monitoring endpoints for automated satellite analysis
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json
import logging

# Set up router
monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = logging.getLogger(__name__)

class MonitoringStatus(BaseModel):
    """Status of automated monitoring system"""
    is_running: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    regions_monitored: int
    total_alerts: int

class MonitoringResults(BaseModel):
    """Results from monitoring run"""
    timestamp: str
    period: str
    regions_analyzed: List[Dict[str, Any]]
    total_changes: int
    total_area_m2: float
    alerts: List[Dict[str, Any]]
    summary: Dict[str, Any]

# Global monitoring state
monitoring_active = False
last_monitoring_results = None
monitoring_task = None

@monitoring_router.get("/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get current status of automated monitoring"""
    return MonitoringStatus(
        is_running=monitoring_active,
        last_run=last_monitoring_results.get('timestamp') if last_monitoring_results else None,
        next_run="Not scheduled" if not monitoring_active else "Next week",
        regions_monitored=10,  # Number of regions we monitor
        total_alerts=len(last_monitoring_results.get('alerts', [])) if last_monitoring_results else 0
    )

@monitoring_router.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start automated weekly monitoring"""
    global monitoring_active, monitoring_task
    
    if monitoring_active:
        raise HTTPException(status_code=400, detail="Monitoring is already running")
    
    monitoring_active = True
    
    # Start monitoring in background
    monitoring_task = asyncio.create_task(run_monitoring_loop())
    
    logger.info("🤖 Automated monitoring started")
    return {"message": "Automated monitoring started", "status": "running"}

@monitoring_router.post("/stop")
async def stop_monitoring():
    """Stop automated monitoring"""
    global monitoring_active, monitoring_task
    
    if not monitoring_active:
        raise HTTPException(status_code=400, detail="Monitoring is not running")
    
    monitoring_active = False
    
    if monitoring_task:
        monitoring_task.cancel()
        monitoring_task = None
    
    logger.info("⏹️ Automated monitoring stopped")
    return {"message": "Automated monitoring stopped", "status": "stopped"}

@monitoring_router.post("/run-now", response_model=MonitoringResults)
async def run_monitoring_now():
    """Run monitoring analysis immediately (manual trigger)"""
    logger.info("🔍 Running manual monitoring analysis")
    
    try:
        results = await run_single_monitoring_cycle()
        return MonitoringResults(**results)
    except Exception as e:
        logger.error(f"Manual monitoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Monitoring failed: {str(e)}")

@monitoring_router.get("/results/latest", response_model=Optional[MonitoringResults])
async def get_latest_results():
    """Get results from the most recent monitoring run"""
    if not last_monitoring_results:
        return None
    
    return MonitoringResults(**last_monitoring_results)

@monitoring_router.get("/results/history")  
async def get_monitoring_history(limit: int = 10):
    """Get historical monitoring results"""
    # This would read from database or file storage
    # For now, return placeholder
    return {
        "message": "Historical results not yet implemented",
        "available_results": 0,
        "limit": limit
    }

async def run_monitoring_loop():
    """Background task that runs monitoring on schedule"""
    global last_monitoring_results
    
    logger.info("📅 Starting monitoring schedule loop")
    
    while monitoring_active:
        try:
            # Run monitoring cycle
            results = await run_single_monitoring_cycle()
            last_monitoring_results = results
            
            logger.info(f"✅ Scheduled monitoring completed: {results['total_changes']} changes detected")
            
            # Wait for next cycle (7 days = 604800 seconds)
            # For testing, use shorter interval (e.g., 300 seconds = 5 minutes)
            await asyncio.sleep(300)  # 5 minutes for testing, change to 604800 for weekly
            
        except asyncio.CancelledError:
            logger.info("🛑 Monitoring loop cancelled")
            break
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")
            # Wait before retrying (1 hour)
            await asyncio.sleep(3600)

async def run_single_monitoring_cycle() -> Dict[str, Any]:
    """Run a single monitoring cycle across all regions"""
    from datetime import datetime, timedelta
    
    # Calculate time periods
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Demo implementation - replace with real analysis
    demo_results = {
        'timestamp': end_date.isoformat(),
        'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        'regions_analyzed': [
            {
                'region_name': 'yogyakarta_urban',
                'change_count': 15,
                'total_area_m2': 8500.0,
                'change_types': {'development': 12, 'vegetation_loss': 3}
            },
            {
                'region_name': 'sleman_north', 
                'change_count': 8,
                'total_area_m2': 4200.0,
                'change_types': {'development': 5, 'land_clearing': 3}
            },
            {
                'region_name': 'bantul_south',
                'change_count': 22,
                'total_area_m2': 12800.0,
                'change_types': {'development': 18, 'vegetation_loss': 4}
            }
        ],
        'total_changes': 45,
        'total_area_m2': 25500.0,
        'alerts': [
            {
                'level': 'MAJOR',
                'type': 'high_change_count',
                'region': 'bantul_south',
                'message': 'Major: 22 changes detected in bantul_south',
                'details': {'change_count': 22, 'threshold': 20}
            }
        ],
        'summary': {
            'status': 'completed',
            'regions_monitored': 3,
            'total_changes': 45,
            'total_area_hectares': 2.55,
            'alert_summary': {'critical': 0, 'major': 1, 'total': 1},
            'most_active_regions': [
                {'name': 'bantul_south', 'changes': 22, 'area_hectares': 1.28},
                {'name': 'yogyakarta_urban', 'changes': 15, 'area_hectares': 0.85},
                {'name': 'sleman_north', 'changes': 8, 'area_hectares': 0.42}
            ],
            'change_types_total': {'development': 35, 'vegetation_loss': 7, 'land_clearing': 3},
            'average_changes_per_region': 15.0
        },
        'errors': []
    }
    
    return demo_results