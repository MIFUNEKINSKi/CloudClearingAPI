# Docker Image Optimization Notes
**Date:** October 29, 2025  
**Task:** CCAPI-28.0 Docker Image Optimization  
**Goal:** Reduce image size from 2.36GB to <500MB

---

## Issues Identified

### Issue 1: Image Size Too Large
- **Initial build:** 2.36GB (372% over 500MB target)
- **Root causes:**
  1. All development dependencies included (jupyter, pytest, black, mypy, dask)
  2. Development libraries (-dev packages) in runtime stage
  3. Large geospatial dependencies (GDAL, GEOS, PROJ)

### Issue 2: earthengine-api Not Found
- **Symptom:** `ModuleNotFoundError: No module named 'earthengine'` in health check
- **Root cause:** requirements.txt may not have been copied or installed correctly

### Issue 3: Incorrect Runtime Library Names
- **First attempt:** Used generic names like `libgdal30`, `libgeos-c1v5`, `libproj22`
- **Problem:** These packages don't exist in python:3.10-slim (Debian Trixie)
- **Solution:** Query apt-cache to find correct versions

---

## Solutions Implemented

### 1. Created Production Requirements File
**File:** `requirements-prod.txt`

**Removed dependencies (dev/test only):**
- `jupyter>=1.0.0` (42MB)
- `notebook>=7.0.0` (15MB)
- `ipykernel>=6.25.0` (8MB)
- `pytest>=7.4.0` (3MB)
- `pytest-cov>=4.1.0` (1MB)
- `black>=23.7.0` (2MB)
- `isort>=5.12.0` (1MB)
- `flake8>=6.0.0` (1MB)
- `mypy>=1.5.0` (5MB)
- `dask[complete]>=2023.1.0` (85MB with all extras)
- `psycopg2-binary>=2.9.0` (optional, commented out)
- `sqlalchemy>=2.0.0` (optional, commented out)
- `alembic>=1.11.0` (optional, commented out)
- `asyncpg>=0.28.0` (optional, commented out)
- `geoalchemy2>=0.14.0` (optional, commented out)
- `folium>=0.14.0` (not needed for batch processing)
- `plotly>=5.15.0` (not needed for batch processing)
- `seaborn>=0.12.0` (not needed)
- `loguru>=0.7.0` (using standard logging)

**Estimated savings:** ~170MB

**Kept for production:**
- Core geospatial: earthengine-api, rasterio, geopandas, shapely, numpy, scikit-image, scipy
- Web framework: fastapi, uvicorn, pydantic (for future API)
- Data processing: pandas, xarray, matplotlib (minimal viz)
- PDF generation: reportlab, Pillow
- Utilities: python-dotenv, pyyaml, click, rich
- Web scraping: requests, beautifulsoup4, lxml

### 2. Corrected Runtime Library Package Names
**Query commands:**
```bash
docker run --rm python:3.10-slim bash -c \
  "apt-get update > /dev/null 2>&1 && apt-cache search libgdal"

docker run --rm python:3.10-slim bash -c \
  "apt-get update > /dev/null 2>&1 && apt-cache search libgeos"
```

**Correct packages for python:3.10-slim (Debian Trixie):**
- `libgdal36` (not libgdal30)
- `libgeos-c1t64` (not libgeos-c1v5)
- `libgeos3.13.1` (full C++ library)
- `libproj25` (correct)
- `libspatialindex-c8` (not libspatialindex6)
- `libspatialindex8` (full library)

### 3. Updated Dockerfile
**Changes made:**

1. **Builder stage (line 30):**
   ```dockerfile
   # OLD
   COPY requirements.txt /tmp/requirements.txt
   pip install --no-cache-dir -r /tmp/requirements.txt
   
   # NEW
   COPY requirements-prod.txt /tmp/requirements-prod.txt
   pip install --no-cache-dir -r /tmp/requirements-prod.txt && \
   pip list > /tmp/installed-packages.txt
   ```
   - Added `pip list` to verify installed packages

2. **Runtime stage (lines 52-62):**
   ```dockerfile
   # OLD (didn't work)
   RUN apt-get update && apt-get install -y --no-install-recommends \
       gdal-bin \
       libgdal30 \
       libgeos-c1v5 \
       ...
   
   # NEW (correct versions)
   RUN apt-get update && apt-get install -y --no-install-recommends \
       gdal-bin \
       libgdal36 \
       libgeos-c1t64 \
       libgeos3.13.1 \
       libproj25 \
       libspatialindex-c8 \
       libspatialindex8 \
       ...
   ```

---

## Expected Results

### Image Size Breakdown (Estimated)

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| Base image (python:3.10-slim) | 150MB | 150MB | 0MB |
| GDAL/GEOS runtime libs | 120MB | 80MB | 40MB |
| Python packages (prod) | 850MB | 350MB | 500MB |
| Application code | 15MB | 15MB | 0MB |
| Geospatial data/fonts | 150MB | 150MB | 0MB |
| Temporary build artifacts | 1,100MB | 0MB | 1,100MB |
| **Total** | **2,360MB** | **745MB** | **1,615MB** |

**Note:** Still above 500MB target due to:
1. GDAL/GEOS runtime libraries (~80MB unavoidable)
2. Core Python geospatial packages (~250MB unavoidable for rasterio, geopandas)
3. Remaining dependencies (pandas, numpy, scipy, reportlab ~200MB)

### Further Optimization Options

If image needs to be <500MB:
1. **Use Alpine Linux base** (reduces base from 150MB to 5MB)
   - Requires compiling all packages from source (slower builds)
   - GDAL/GEOS compilation adds 15-20 minutes to build time
   
2. **Multi-architecture manifests** (ARM64 vs AMD64)
   - Current build on ARM64 Mac (M-series) may have different size than AMD64
   
3. **Remove matplotlib** (saves ~50MB)
   - Would lose PDF chart generation capability
   
4. **Use external data volumes**
   - Mount GDAL data files instead of bundling (~30MB savings)

---

## Validation Checklist

After build completes, verify:

- [ ] Image size <1GB (intermediate goal)
- [ ] earthengine-api module imports successfully
- [ ] Container starts without errors
- [ ] Health check passes
- [ ] GEE authentication works (with credentials)
- [ ] Cache directories writable
- [ ] Config file readable

---

## Build Commands

```bash
# Clean rebuild
docker build --no-cache -t cloudclearing-api:latest .

# Quick rebuild (with cache)
docker build -t cloudclearing-api:latest .

# Check image size
docker images cloudclearing-api:latest

# Test health check
docker run --rm cloudclearing-api:latest python -c \
  "import earthengine as ee; print('✓ earthengine-api imported')"

# Run with mounted credentials
docker run --rm \
  -v $(pwd)/credentials:/app/credentials:ro \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/output:/app/output \
  -e EARTHENGINE_PROJECT=your-gee-project \
  cloudclearing-api:latest
```

---

## Next Steps After Optimization

1. **Update CI/CD workflow** to use `requirements-prod.txt`
2. **Tag Docker image** for production use
3. **Push to Amazon ECR**
4. **Test ECS Fargate deployment**
5. **Monitor resource usage** (CPU, memory, startup time)
6. **Update documentation** with final image size

---

## References

- Original Dockerfile: 2.36GB (before optimization)
- Debian package search: `apt-cache search <package>`
- Docker BuildKit: `DOCKER_BUILDKIT=1 docker build`
- Multi-stage builds: https://docs.docker.com/develop/develop-images/multistage-build/
