# CloudClearingAPI Setup Guide

## 🚀 Quick Start Checklist

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] Google Cloud Platform account
- [ ] Earth Engine access approved

### Step 1: Earth Engine Setup (CRITICAL)
```bash
# 1. Create GCP project
open "https://console.cloud.google.com/"

# 2. Enable Earth Engine API
# Go to APIs & Services > Enable APIs and Services > Search "Earth Engine"

# 3. Register your project for Earth Engine
open "https://code.earthengine.google.com/register?project=YOUR_PROJECT_ID"

# 4. Authenticate locally
earthengine authenticate

# 5. Test authentication
python -c "import ee; ee.Initialize(project='YOUR_PROJECT_ID'); print('✅ Success!')"
```

### Step 2: Project Setup
```bash
# Clone and setup
git clone <your-repo>
cd CloudClearingAPI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your settings
```

### Step 3: Configuration
Edit `config/config.yaml`:

1. **Earth Engine Project** (REQUIRED):
   ```yaml
   gee_project: "your-gcp-project-id"
   ```

2. **Area of Interest**:
   ```yaml
   monitoring:
     bbox_west: 110.25    # Your area coordinates
     bbox_east: 110.55
     bbox_south: -7.95
     bbox_north: -7.65
   ```

3. **Alert Settings**:
   ```yaml
   alerts:
     email_recipients:
       - "your-email@domain.com"
   ```

### Step 4: Test Installation
```bash
# Test Earth Engine
python -c "import ee; ee.Initialize(project='YOUR_PROJECT_ID'); print('✅ Earth Engine OK')"

# Start server
python src/api/main.py

# Test endpoints (in another terminal)
curl "http://localhost:8000/health"
curl "http://localhost:8000/regions"
```

## 🔧 Common Issues & Solutions

### Earth Engine "no project found" Error
**Problem**: `ee.Initialize: no project found`
**Solution**: 
1. Set `gee_project` in config.yaml
2. Register project at: https://code.earthengine.google.com/register
3. Run `earthengine authenticate`

### High Cloud Cover in Tropical Regions
**Problem**: Poor image quality in Indonesia/SE Asia
**Solution**: Adjust cloud masking settings:
```yaml
processing:
  max_cloud_cover: 15.0  # Lower threshold
  use_s2cloudless: true  # Better cloud detection
  cloud_probability_threshold: 40
```

### Too Many False Alerts
**Problem**: Alerts for every small change
**Solution**: Increase minimum area and add filters:
```yaml
monitoring:
  min_change_area_m2: 1000.0  # Larger minimum
  exclude_agricultural: true   # Filter farm changes
  change_confidence_threshold: 0.75
```

### Memory/Performance Issues
**Problem**: Analysis takes too long or crashes
**Solution**: Reduce processing area or increase resources:
```yaml
processing:
  max_pixels: 500000000  # Reduce if needed
  scale: 20             # Lower resolution = faster
```

## 📊 Production Deployment

### Environment Variables
```bash
export GEE_PROJECT="your-project-id"
export SMTP_USERNAME="alerts@yourdomain.com"
export SMTP_PASSWORD="your-app-password"
export DATABASE_URL="postgresql://..."
```

### Docker Deployment
```bash
# Build image
docker build -t cloudclearing-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e GEE_PROJECT="your-project-id" \
  -v ./config:/app/config \
  cloudclearing-api
```

### Health Monitoring
Monitor these endpoints:
- `GET /health` - Service health
- `GET /status` - System status
- `GET /metrics` - Performance metrics (if enabled)

## 🧪 Testing & Validation

### Test with Historical Data
```python
# Test change detection with known changes
from src.core.change_detector import ChangeDetector

detector = ChangeDetector()
results = detector.detect_weekly_changes(
    week_a_start="2023-01-01",
    week_b_start="2023-01-08",
    bbox=your_test_area
)
```

### Validate Thresholds
Use the Jupyter notebook in `notebooks/` to:
1. Visualize NDVI/NDBI changes
2. Tune detection thresholds
3. Test different cloud masking approaches

## 📈 Scaling Considerations

### Multi-Region Setup
Add multiple AOIs in config:
```yaml
monitoring_regions:
  - name: "Region 1"
    bbox_west: 110.0
    # ... coordinates
  - name: "Region 2"
    bbox_west: 115.0
    # ... coordinates
```

### Database Integration
For production, enable PostgreSQL:
```yaml
database:
  enabled: true
  url: "postgresql://user:pass@host/db"
```

### Commercial Data Sources
Upgrade path to higher resolution:
- Planet Labs: 3m daily imagery
- Maxar: Sub-meter imagery
- Airbus: SPOT/Pleiades imagery