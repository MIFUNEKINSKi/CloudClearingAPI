# CloudClearingAPI Project Instructions

This is a Python-based satellite imagery analysis system for monitoring land development changes around Yogyakarta using Sentinel-2 data via Google Earth Engine.

## Project Overview
- **Primary Goal**: Monitor development changes (roads, buildings, vegetation loss) using satellite imagery
- **Tech Stack**: Python, Google Earth Engine, Flask/FastAPI for web API, PostgreSQL for data storage
- **Data Sources**: Sentinel-2 (free), with optional Planet Labs integration (paid)
- **Architecture**: Change detection algorithms, web dashboard, alerting system

## Key Components
- `/src/core/` - Core change detection algorithms
- `/src/data/` - Data ingestion and preprocessing 
- `/src/api/` - Web API endpoints
- `/src/dashboard/` - Web dashboard frontend
- `/src/alerts/` - Notification and alerting system
- `/notebooks/` - Jupyter notebooks for analysis and prototyping
- `/tests/` - Unit and integration tests
- `/config/` - Configuration files

## Development Guidelines
- Use Google Earth Engine Python API for satellite data access
- Implement NDVI/NDBI based change detection algorithms
- Follow clean architecture principles with dependency injection
- Include comprehensive logging and error handling
- Use environment variables for API keys and configuration

## Setup Requirements
- Python 3.8+
- Google Earth Engine account and authentication
- PostgreSQL database (optional for production)
- Required Python packages: earthengine-api, rasterio, geopandas, flask/fastapi, numpy, scikit-image

## Coding Standards
- Use type hints and docstrings
- Follow PEP 8 style guidelines
- Implement proper error handling and logging
- Write unit tests for all core functionality
- Use configuration files for parameters and thresholds