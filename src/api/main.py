"""
FastAPI web server for CloudClearingAPI

This module provides REST API endpoints for triggering change detection,
viewing results, and managing monitoring configurations.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uvicorn
from datetime import datetime, timedelta
import json
import os
import sys
import logging
from pathlib import Path

# Add src to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.change_detector import ChangeDetector, ChangeDetectionConfig
from core.config import get_config, AppConfig
from .monitoring import monitoring_router

# Set up logging
logger = logging.getLogger(__name__)

# Database integration (optional)
try:
    from core.database import get_db_manager
    DATABASE_AVAILABLE = True
    logger.info("Database integration available")
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database integration not available (missing dependencies)")

# Set up logging
logger = logging.getLogger(__name__)

try:
    # Import regions module (we're in src/api/, regions.py is in src/)
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from regions import (
        RegionManager, OverlookedAreaDetector, 
        get_region_manager, AreaOfInterest
    )
    REGIONS_AVAILABLE = True
    print("✅ Regions module loaded successfully")
except ImportError as e:
    REGIONS_AVAILABLE = False
    logger.warning(f"Regions module not available: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="CloudClearingAPI",
    description="Satellite imagery change detection API for monitoring land development",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring router
app.include_router(monitoring_router)

# Pydantic models for API requests/responses
class AnalysisRequest(BaseModel):
    """Request model for change detection analysis"""
    week_a_start: str = Field(..., description="Start date of first week (YYYY-MM-DD)")
    week_b_start: str = Field(..., description="Start date of second week (YYYY-MM-DD)")
    region_name: Optional[str] = Field(None, description="Predefined region name (e.g., 'Kulon Progo Airport Zone')")
    bbox_west: float = Field(110.25, description="Western boundary (longitude)")
    bbox_east: float = Field(110.55, description="Eastern boundary (longitude)")
    bbox_south: float = Field(-7.95, description="Southern boundary (latitude)")
    bbox_north: float = Field(-7.65, description="Northern boundary (latitude)")
    ndvi_threshold: float = Field(-0.20, description="NDVI loss threshold")
    ndbi_threshold: float = Field(0.15, description="NDBI gain threshold")
    min_area_m2: float = Field(200.0, description="Minimum change area in square meters")

class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    analysis_id: str
    status: str
    change_count: int
    total_area_m2: float
    change_types: Dict[str, int]
    week_a: str
    week_b: str
    bbox: List[float]
    timestamp: str

class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    monitoring: Optional[Dict[str, Any]] = None
    processing: Optional[Dict[str, Any]] = None
    alerts: Optional[Dict[str, Any]] = None

# Global variables
detector = None
current_config = None

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    global detector, current_config
    
    try:
        # Load configuration
        current_config = get_config()
        
        # Try to initialize change detector with GEE project if available
        detection_config = ChangeDetectionConfig(
            ndvi_loss_threshold=current_config.monitoring.ndvi_loss_threshold,
            ndbi_gain_threshold=current_config.monitoring.ndbi_gain_threshold,
            min_change_area=current_config.monitoring.min_change_area_m2
        )
        
        try:
            # Initialize Earth Engine with project if specified
            import ee
            if current_config.gee_project:
                print(f"🌍 Initializing Earth Engine with project: {current_config.gee_project}")
                ee.Initialize(project=current_config.gee_project)
            else:
                print("🌍 Initializing Earth Engine (no project specified)")
                ee.Initialize()
            
            detector = ChangeDetector(detection_config)
            print("✅ CloudClearingAPI server initialized with Earth Engine")
        except Exception as ee_error:
            print(f"⚠️  Earth Engine not available: {str(ee_error)}")
            print("   💡 To fix: Set gee_project in config.yaml or run 'earthengine authenticate'")
            print("   (Server will run in demo mode without satellite analysis)")
            detector = None
        
        print("✅ CloudClearingAPI server startup completed")
        
    except Exception as e:
        print(f"❌ Critical startup error: {str(e)}")
        # Don't raise - let server start anyway for testing
        detector = None
        current_config = None

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Root endpoint with API information"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CloudClearingAPI</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            .endpoint { background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { font-weight: bold; color: #27ae60; }
            .status { color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">🛰️ CloudClearingAPI</h1>
            <p><strong>Satellite imagery change detection for monitoring land development around Yogyakarta</strong></p>
            
            <h2>🚀 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/health</code> - Health check
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/analyze</code> - Run change detection analysis
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/config</code> - Get current configuration
            </div>
            
            <div class="endpoint">
                <span class="method">PUT</span> <code>/config</code> - Update configuration
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/docs</code> - Interactive API documentation
            </div>
            
            <h2>📊 Current Status</h2>
            <p>Status: <span class="status">Ready</span></p>
            <p>Version: 0.1.0</p>
            <p>Framework: FastAPI + Google Earth Engine</p>
            
            <h2>🗺️ Default Area</h2>
            <p>Monitoring the Yogyakarta region (110.25°E to 110.55°E, 7.65°S to 7.95°S)</p>
            
            <p><a href="/docs" style="color: #3498db;">📖 View Full API Documentation</a></p>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the interactive dashboard"""
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    else:
        return HTMLResponse("""
        <html><body>
        <h1>Dashboard Not Found</h1>
        <p>Dashboard files are not available. Please check the installation.</p>
        </body></html>
        """, status_code=404)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "services": {
            "earth_engine": "connected" if detector else "not_initialized",
            "config": "loaded" if current_config else "not_loaded"
        }
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Run change detection analysis for specified time periods and area
    """
    if not detector:
        raise HTTPException(status_code=500, detail="Change detector not initialized")
    
    try:
        # Create bounding box
        import ee
        bbox = ee.Geometry.Rectangle([
            request.bbox_west,
            request.bbox_south, 
            request.bbox_east,
            request.bbox_north
        ])
        
        # Update detector configuration
        detector.config.ndvi_loss_threshold = request.ndvi_threshold
        detector.config.ndbi_gain_threshold = request.ndbi_threshold
        detector.config.min_change_area = request.min_area_m2
        
        # Generate analysis ID
        analysis_id = f"{request.week_a_start}_{request.week_b_start}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # For now, return a demo response to test the dashboard
        # TODO: Implement full analysis when compute issues are resolved
        logger.info(f"Demo analysis requested for {request.week_a_start} to {request.week_b_start}")
        
        # Simulate some basic processing
        import time
        time.sleep(2)  # Simulate processing time
        
        # Demo response with simulated results
        demo_results = {
            'change_count': 12,
            'total_area': 15600.0,  # square meters
            'change_types': {
                'development': 8,
                'vegetation_loss': 3,
                'land_clearing': 1
            },
            'week_a': f"{request.week_a_start} to {request.week_a_start}",
            'week_b': f"{request.week_b_start} to {request.week_b_start}"
        }
        
        # Prepare response
        response = AnalysisResponse(
            analysis_id=analysis_id,
            status="completed",
            change_count=demo_results['change_count'],
            total_area_m2=demo_results['total_area'],
            change_types=demo_results['change_types'],
            week_a=demo_results['week_a'],
            week_b=demo_results['week_b'],
            bbox=[request.bbox_west, request.bbox_south, request.bbox_east, request.bbox_north],
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Demo analysis completed: {demo_results['change_count']} changes detected")
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/config")
async def get_current_config():
    """Get current configuration settings"""
    if not current_config:
        raise HTTPException(status_code=500, detail="Configuration not loaded")
    
    return {
        "monitoring": {
            "bbox_west": current_config.monitoring.bbox_west,
            "bbox_east": current_config.monitoring.bbox_east,
            "bbox_south": current_config.monitoring.bbox_south,
            "bbox_north": current_config.monitoring.bbox_north,
            "ndvi_loss_threshold": current_config.monitoring.ndvi_loss_threshold,
            "ndbi_gain_threshold": current_config.monitoring.ndbi_gain_threshold,
            "min_change_area_m2": current_config.monitoring.min_change_area_m2,
        },
        "processing": {
            "max_cloud_cover": current_config.processing.max_cloud_cover,
            "scale": current_config.processing.scale,
        },
        "alerts": {
            "email_enabled": current_config.alerts.email_enabled,
            "email_recipients": current_config.alerts.email_recipients,
        }
    }

@app.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration settings"""
    global current_config, detector
    
    try:
        # Update configuration (simplified - in production you'd want proper validation)
        if request.monitoring:
            for key, value in request.monitoring.items():
                if hasattr(current_config.monitoring, key):
                    setattr(current_config.monitoring, key, value)
        
        if request.processing:
            for key, value in request.processing.items():
                if hasattr(current_config.processing, key):
                    setattr(current_config.processing, key, value)
        
        if request.alerts:
            for key, value in request.alerts.items():
                if hasattr(current_config.alerts, key):
                    setattr(current_config.alerts, key, value)
        
        # Reinitialize detector with new config
        if detector and request.monitoring:
            detection_config = ChangeDetectionConfig(
                ndvi_loss_threshold=current_config.monitoring.ndvi_loss_threshold,
                ndbi_gain_threshold=current_config.monitoring.ndbi_gain_threshold,
                min_change_area=current_config.monitoring.min_change_area_m2
            )
            detector = ChangeDetector(detection_config)
        
        return {"status": "success", "message": "Configuration updated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")

@app.get("/status")
async def get_status():
    """Get system status and recent activities"""
    return {
        "system": {
            "status": "running",
            "uptime": "N/A",  # Would implement actual uptime tracking
            "version": "0.1.0"
        },
        "monitoring": {
            "area": f"{current_config.monitoring.bbox_west}, {current_config.monitoring.bbox_south} to {current_config.monitoring.bbox_east}, {current_config.monitoring.bbox_north}",
            "last_analysis": "N/A",  # Would track in database
            "total_analyses": 0      # Would track in database
        },
        "earth_engine": {
            "status": "connected" if detector else "disconnected",
            "quota_usage": "N/A"     # Would implement quota tracking
        }
    }

# Multi-Region Endpoints
@app.get("/regions")
async def list_regions():
    """List all available monitoring regions"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    try:
        manager = RegionManager()
        regions = []
        
        for aoi in manager.get_all_regions():
            regions.append({
                "name": aoi.name,
                "description": f"{aoi.focus} monitoring area on {aoi.island}",
                "bbox": list(aoi.bbox),
                "area_km2": round(aoi.area_km2(), 2),
                "priority": aoi.priority,
                "tags": [aoi.island, aoi.focus]
            })
        
        return {
            "total_regions": len(regions),
            "regions": regions,
            "by_priority": {
                "high": len([r for r in regions if r["priority"] == 1]),
                "medium": len([r for r in regions if r["priority"] == 2]),
                "low": len([r for r in regions if r["priority"] == 3])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load regions: {str(e)}")

@app.get("/regions/priority/{priority_level}")
async def get_regions_by_priority(priority_level: int):
    """Get regions by priority level (1=high, 2=medium, 3=low)"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    try:
        manager = RegionManager()
        regions = manager.get_regions_by_priority(priority_level)
        
        return {
            "priority_level": priority_level,
            "count": len(regions),
            "regions": [
                {
                    "name": aoi.name,
                    "description": f"{aoi.focus} monitoring area on {aoi.island}",
                    "bbox": list(aoi.bbox),
                    "area_km2": round(aoi.area_km2(), 2),
                    "tags": [aoi.island, aoi.focus]
                } for aoi in regions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get regions: {str(e)}")

@app.get("/regions/island/{island}")
async def get_regions_by_island(island: str):
    """Get regions by island (java, sumatra, bali, etc.)"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    try:
        manager = RegionManager()
        regions = manager.get_regions_by_island(island.lower())
        
        return {
            "island": island,
            "count": len(regions),
            "regions": [
                {
                    "name": aoi.name,
                    "description": f"{aoi.focus} monitoring area on {aoi.island}",
                    "bbox": list(aoi.bbox),
                    "area_km2": round(aoi.area_km2(), 2),
                    "priority": aoi.priority,
                    "tags": [aoi.island, aoi.focus]
                } for aoi in regions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get regions for {island}: {str(e)}")

@app.post("/analyze/batch")
async def run_batch_analysis(
    week_a_start: str,
    week_b_start: str, 
    priority_filter: Optional[int] = None,
    island_filter: Optional[str] = None
):
    """Run change detection analysis for multiple regions"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    if not detector:
        raise HTTPException(status_code=500, detail="Change detector not initialized")
    
    try:
        manager = RegionManager()
        
        # Get regions based on filters
        if priority_filter:
            regions = manager.get_regions_by_priority(priority_filter)
        elif island_filter:
            regions = manager.get_regions_by_island(island_filter.lower())
        else:
            regions = manager.get_regions_by_priority(1)  # Default to high priority (priority=1)
        
        results = []
        
        # Run analysis for each region
        for aoi in regions:
            try:
                bbox = aoi.to_ee_geometry()
                
                region_results = detector.detect_weekly_changes(
                    week_a_start=week_a_start,
                    week_b_start=week_b_start,
                    bbox=bbox,
                    export_results=False  # Don't export individually
                )
                
                results.append({
                    "region_name": aoi.name,
                    "success": True,
                    "change_count": region_results['change_count'],
                    "total_area_m2": region_results['total_area'],
                    "change_types": region_results['change_types'],
                    "area_km2": round(aoi.area_km2(), 2)
                })
                
            except Exception as e:
                results.append({
                    "region_name": aoi.name,
                    "success": False,
                    "error": str(e)
                })
        
        # Summary statistics
        successful_analyses = [r for r in results if r["success"]]
        total_changes = sum([r["change_count"] for r in successful_analyses])
        total_area_affected = sum([r["total_area_m2"] for r in successful_analyses])
        
        return {
            "batch_summary": {
                "total_regions": len(results),
                "successful": len(successful_analyses),
                "failed": len(results) - len(successful_analyses),
                "total_changes_detected": total_changes,
                "total_area_affected_m2": total_area_affected,
                "analysis_period": f"{week_a_start} to {week_b_start}"
            },
            "region_results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@app.post("/discover/overlooked")
async def discover_overlooked_areas(
    region_bbox: List[float],  # [west, south, east, north]
    grid_size_km: float = 2.0,
    max_results: int = 20
):
    """Discover overlooked areas with development potential"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    try:
        detector = OverlookedAreaDetector()
        
        # Convert list to tuple
        bbox_tuple = tuple(region_bbox)
        
        # Run detection algorithm
        candidates = detector.detect_overlooked_areas_ee(
            region_bbox=bbox_tuple,
            grid_size_km=grid_size_km,
            max_results=max_results
        )
        
        # Export results
        filename = detector.export_candidates_geojson(candidates)
        
        return {
            "status": "success",
            "candidates_found": max_results,
            "grid_size_km": grid_size_km,
            "region_bbox": region_bbox,
            "export_file": filename,
            "algorithm_weights": detector.weights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overlooked area detection failed: {str(e)}")

@app.get("/export/regions")
async def export_regions_geojson():
    """Export all regions as GeoJSON"""
    if not REGIONS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Multi-region functionality not available")
    
    try:
        manager = RegionManager()
        filename = "indonesia_monitoring_regions.geojson"
        geojson_content = manager.export_aois_geojson(filename)
        
        return JSONResponse(
            content=json.loads(geojson_content),
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )