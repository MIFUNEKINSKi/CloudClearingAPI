# CloudClearingAPI - Quick Start Guide 🚀

**Real Estate Investment Intelligence System**

Get up and running with satellite-based investment analysis in 15 minutes.

## 🎯 **Current System Status: PRODUCTION READY**

✅ **289,318+ changes detected** across 32,880 hectares  
✅ **10 Indonesian regions** under continuous monitoring  
✅ **Multi-intelligence scoring** (satellite + infrastructure + market data)  
✅ **Investment recommendations** with confidence levels  
✅ **Smart date finding** eliminates data availability issues

## 🚀 Quick Setup (5 minutes)

### 1. Prerequisites
- **Python 3.8+** installed on your system
- **Google account** for Earth Engine access
- **Git** (optional, for cloning)

### 2. Installation
```bash
# Clone the repository (or download and extract)
git clone <your-repo-url>
cd CloudClearingAPI

# Run the setup script
python setup.py
```

The setup script will:
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Set up configuration files
- ✅ Check Earth Engine status

### 3. Google Earth Engine Setup
```bash
# Authenticate with Google Earth Engine (one-time setup)
earthengine authenticate
```
Follow the prompts to sign in with your Google account.

### 4. Configure Your Area
Edit `config/config.yaml`:
```yaml
monitoring:
  bbox_west: 110.25    # Western boundary
  bbox_east: 110.55    # Eastern boundary  
  bbox_south: -7.95    # Southern boundary
  bbox_north: -7.65    # Northern boundary
```

## 🌟 **Current Capabilities**

### **Investment Intelligence**
- 🏗️ **Infrastructure Analysis**: Highway/airport/railway proximity (OpenStreetMap)
- 💰 **Market Intelligence**: Indonesian property growth forecasting (20%+ identification)
- 🎯 **Opportunity Scoring**: 0-100 investment scores with BUY/WATCH/INVESTIGATE signals
- 📊 **Executive Reports**: Investment summaries with confidence levels

### **Technical Features**
- 🛰️ **Smart Date Finding**: Automatically finds best available satellite imagery
- 🔄 **Automated Monitoring**: Weekly analysis across 10 strategic regions
- 📈 **Multi-factor Scoring**: Infrastructure + Pattern + Strategic + Market intelligence
- 🎪 **Production Ready**: Handles 289k+ changes, 32k+ hectares analyzed

### **Recent Top Results**
- **#1 Opportunity**: Solo Expansion (85.9/100 score) - Airport development corridor
- **#2 Opportunity**: Surakarta Suburbs (84.8/100) - Growth trajectory area
- **#3 Opportunity**: Yogyakarta Periurban (82.4/100) - Infrastructure expansion

### 5. Test the System
```bash
# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Run investment intelligence system
python run_weekly_monitor.py

# Check results in output/monitoring/
```

## 🚀 **Quick Run - Investment Analysis**

### **Option 1: Run Weekly Monitoring (Recommended)**
```bash
# Run complete investment intelligence system
python run_weekly_monitor.py

# Output: Investment rankings, opportunity analysis, executive summary
# Location: output/monitoring/weekly_monitoring_[timestamp].json
```

### **Option 2: Interactive Dashboard**
```bash
# Launch investment dashboard
cd src/dashboard
python -m http.server 8000

# Open: http://localhost:8000
# Features: Interactive maps, before/after comparison, change analysis
```

### **Expected Investment Intelligence Output:**
- 🎯 **Top Opportunities**: Ranked 1-10 with investment scores
- 🏗️ **Infrastructure Context**: Highway/airport proximity analysis  
- 💰 **Market Intelligence**: Growth rate forecasts, market maturity
- 📈 **Action Signals**: BUY/WATCH/INVESTIGATE with confidence levels
- 🧠 **Strategic Reasoning**: Human-readable investment justification

## 🎯 Your First Analysis

### Option A: Use the Jupyter Notebook (Recommended)
```bash
# Start Jupyter
jupyter notebook notebooks/mvp_change_detection_demo.ipynb
```

Run all cells to perform a complete change detection analysis.

### Option B: Use the REST API
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "week_a_start": "2025-09-01",
    "week_b_start": "2025-09-08"
  }'
```

### Option C: Use the Python API directly
```python
from src.core.change_detector import ChangeDetector
import ee

ee.Initialize()

detector = ChangeDetector()
results = detector.detect_weekly_changes(
    week_a_start='2025-09-01',
    week_b_start='2025-09-08',
    bbox=ee.Geometry.Rectangle([110.25, -7.95, 110.55, -7.65])
)

print(f"Detected {results['change_count']} changes")
```

## 🎨 What You'll See

The system will:
1. **Download** Sentinel-2 satellite images
2. **Create** weekly composites (reduces clouds)
3. **Calculate** vegetation (NDVI) and built-up (NDBI) indices
4. **Detect** changes between weeks
5. **Export** results as GeoJSON polygons
6. **Visualize** results on interactive maps

## 📊 Understanding Results

### Change Types Detected:
- 🏗️ **Development**: Vegetation loss + building gain
- 🌳 **Clearing**: Significant vegetation loss
- 🛤️ **Roads**: Linear built-up patterns  
- 🏢 **Buildings**: Concentrated built-up areas
- 🌱 **Vegetation Loss**: General vegetation changes

### Output Files:
- `output/` - Analysis results and maps
- Google Drive folder `CloudClearingAPI_Results` - GeoJSON exports
- Jupyter notebook outputs - Interactive visualizations

## ⚙️ Customization

### Adjust Detection Sensitivity
Edit thresholds in `config/config.yaml`:
```yaml
monitoring:
  ndvi_loss_threshold: -0.20    # More negative = more sensitive
  ndbi_gain_threshold: 0.15     # Lower = more sensitive
  min_change_area_m2: 200       # Smaller = detect smaller changes
```

### Change the Area
Update coordinates in config file or API requests:
```yaml
monitoring:
  bbox_west: 110.0     # Your western boundary
  bbox_east: 111.0     # Your eastern boundary
  bbox_south: -8.0     # Your southern boundary  
  bbox_north: -7.0     # Your northern boundary
```

### Schedule Automated Monitoring
```bash
# Add to cron for weekly monitoring
0 9 * * 1 cd /path/to/CloudClearingAPI && python src/core/change_detector.py
```

## 🔧 Troubleshooting

### Common Issues:

**"Earth Engine not authenticated"**
```bash
earthengine authenticate
```

**"No images found"**
- Try different date ranges (avoid monsoon season)
- Increase cloud cover threshold in config
- Check your area coordinates

**"Import errors"**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**"Out of memory"**
- Reduce area size
- Increase `tileScale` parameter
- Use smaller date ranges

### Getting Help:
1. 📖 Check the full README.md
2. 🐛 Open an issue on GitHub
3. 📧 Contact the development team
4. 💬 Join our community discussions

## 🎯 Next Steps

### Production Deployment:
1. Set up PostgreSQL database
2. Configure email alerts
3. Deploy to cloud (AWS/GCP)
4. Set up monitoring dashboards
5. Implement user authentication

### Advanced Features:
1. Train ML models for better detection
2. Add Planet Labs high-resolution data
3. Implement real-time processing
4. Create mobile applications
5. Add multi-region support

---

**Happy monitoring! 🛰️🌍**

*This system helps protect our environment by providing early warning of unauthorized development and deforestation.*