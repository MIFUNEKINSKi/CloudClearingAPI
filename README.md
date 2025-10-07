# CloudClearingAPI 🛰️💰

**Real Estate Investment Intelligence via Satellite Analysis**

An advanced Python-based system that transforms satellite imagery into investment opportunities by analyzing land development changes across Indonesia using Sentinel-2 data, real infrastructure intelligence, and market analysis.

## 🎯 System Capabilities

**Investment Intelligence Platform:**
- 🏗️ **Infrastructure Analysis**: Real OpenStreetMap highway/airport/railway proximity
- 💰 **Market Intelligence**: Indonesian property growth forecasting (20%+ markets)
- 🧠 **AI Scoring**: Multi-factor investment recommendations (0-100 scale)
- 📈 **Opportunity Ranking**: BUY/WATCH/INVESTIGATE signals with confidence levels
- 🎯 **Strategic Focus**: 10 Indonesian growth corridors under continuous monitoring

**Change Detection Core:**
- New roads and infrastructure development
- Building construction and land clearing
- Industrial expansion and planned subdivisions
- Smart date finding for continuous monitoring

## 🏗️ Enhanced Architecture

### Intelligence Pipeline
1. **Satellite Analysis**: Sentinel-2 via Google Earth Engine with smart date finding
2. **Infrastructure Intelligence**: Real-time OpenStreetMap highway/airport/railway analysis
3. **Market Intelligence**: Indonesian property market growth analysis & forecasting
4. **Change Detection**: NDVI/NDBI/BSI spectral analysis with pattern recognition
5. **Investment Scoring**: Multi-factor algorithms (infrastructure + pattern + strategic + market)
6. **Executive Reporting**: Investment-grade recommendations with confidence levels

### Production Enhancements
- **Smart Date Finding**: Automatic imagery optimization (eliminates data gaps)
- **Multi-Region Processing**: 10 Indonesian strategic regions simultaneously  
- **Real Infrastructure Data**: OpenStreetMap integration with distance weighting
- **Investment Focus**: Transform academic monitoring → real estate alpha generation

### Enhanced Tech Stack
- **Intelligence**: Multi-source analysis (Sentinel-2 + OpenStreetMap + Market Data)
- **Backend**: Python, Flask/FastAPI, Google Earth Engine
- **Data Processing**: rasterio, numpy, scikit-image, geopandas
- **Infrastructure**: OpenStreetMap Overpass API, spatial analysis
- **Market Intel**: Indonesian property data, growth forecasting
- **Frontend**: Interactive Leaflet dashboard, before/after visualization
- **Deployment**: Production-ready with smart date finding

## 🎊 **Current Results**

**Latest Monitoring Run (Sept 2025):**
- 📊 **Total Analysis**: 289,318 changes across 32,880 hectares
- 🏆 **Top Opportunity**: Solo Expansion (85.9/100 score)
- 🎯 **Investment Signals**: 1 BUY, 4 WATCH, 5 INVESTIGATE
- 🏗️ **Infrastructure Intelligence**: Highway/airport proximity analysis
- 💰 **Market Intelligence**: 20%+ growth markets identified

**Strategic Regions Monitored:**
1. Solo Expansion (Airport corridor) - 85.9/100
2. Surakarta Suburbs - 84.8/100  
3. Yogyakarta Periurban - 82.4/100
4. Kulon Progo West (Airport development) - 72.5/100
5. Gunungkidul East (Coastal highway) - 77.0/100
6. Plus 5 additional strategic regions

## 📁 Enhanced Project Structure

```
CloudClearingAPI/
├── src/
│   ├── core/                    # Enhanced Intelligence Modules
│   │   ├── change_detector.py   # Smart date finding + change detection
│   │   ├── speculative_scorer.py # Investment scoring algorithms  
│   │   ├── infrastructure_analyzer.py # Real OSM infrastructure analysis
│   │   ├── price_intelligence.py # Indonesian market intelligence
│   │   └── automated_monitor.py # Production monitoring system
│   ├── api/            # Investment API endpoints
│   ├── dashboard/      # Interactive investment dashboard
│   └── regions.py      # 10 Indonesian strategic regions
├── output/monitoring/  # Investment analysis results
├── notebooks/          # Analysis & prototyping
├── tests/              # Production-ready testing
├── config/             # Multi-environment configuration
└── docs/               # Enhanced documentation
```

## 🚀 Quick Start

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup**

```bash
# 1. Clone and setup
git clone [repository]
cd CloudClearingAPI
pip install -r requirements.txt

# 2. Configure Google Earth Engine
ee authenticate
cp config/config.example.yaml config/config.yaml

# 3. Run investment analysis
python run_weekly_monitor.py

# 4. View results
# output/monitoring/weekly_monitoring_[timestamp].json
```

### Prerequisites
1. **Google Earth Engine Account**: Sign up at [earthengine.google.com](https://earthengine.google.com)
2. **Python 3.8+**: Install from [python.org](https://python.org)

### Installation
```bash
# Clone and setup
git clone <your-repo>
cd CloudClearingAPI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Authenticate Google Earth Engine (one-time setup)
earthengine authenticate
```

### Configuration
```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit config with your settings:
# - Area of interest coordinates
# - Alert thresholds
# - Notification settings
```

### Run MVP Demo
```bash
# Run the basic change detection
python src/core/change_detector.py

# Start the web API
python src/api/main.py

# View dashboard at http://localhost:5000
```

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
isort src/
```

### Environment Variables
Create a `.env` file:
```
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
DATABASE_URL=postgresql://user:pass@localhost/cloudclearing
SMTP_SERVER=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📊 MVP Features

### Change Detection Algorithms
- **NDVI Analysis**: Vegetation loss detection
- **NDBI Analysis**: Built-up area detection
- **Spectral Differencing**: Multi-band change analysis
- **Morphological Filtering**: Noise reduction

### Output Products
- **Change Polygons**: GeoJSON/Shapefile export
- **Confidence Scores**: Algorithm reliability metrics
- **Before/After Images**: Visual comparison tiles
- **Summary Reports**: Area calculations and statistics

### Alerting System
- **Email Notifications**: Automated alerts for significant changes
- **Webhook Integration**: Slack/Discord notifications
- **Threshold Configuration**: Customizable sensitivity settings
- **Dashboard Alerts**: Real-time web interface updates

## 🌍 Area of Interest

Default configuration monitors the Yogyakarta region:
- **Bounding Box**: 110.25°E to 110.55°E, 7.65°S to 7.95°S
- **Resolution**: 10m (Sentinel-2)
- **Update Frequency**: Weekly composites
- **Coverage**: ~900 km² monitoring area

## 🔮 Upgrade Path

### Enhanced Data Sources
- **Planet Labs**: Daily 3m imagery (paid)
- **Maxar**: Sub-meter resolution (paid)
- **Landsat**: Historical analysis (free)

### Advanced Algorithms
- **Machine Learning**: UNet segmentation models
- **Time Series Analysis**: Seasonal pattern recognition
- **Multi-sensor Fusion**: Radar + optical data

### Scaling Features
- **Multi-region Support**: Monitor multiple areas
- **API Rate Limiting**: Commercial usage controls
- **Batch Processing**: Historical change analysis
- **Cloud Deployment**: Production infrastructure

## 📈 Performance Metrics

### Accuracy Targets
- **Precision**: >80% for development detection
- **Recall**: >70% for significant changes (>200m²)
- **Processing Time**: <5 minutes per weekly composite

### Cost Estimates
- **Sentinel-2**: Free (Google Earth Engine limits apply)
- **Planet**: ~$2-5 per km² per month
- **Compute**: ~$10-50/month for weekly processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Check the `docs/` folder for detailed guides

---

**Note**: This is an MVP implementation designed for rapid prototyping. For production deployment, consider additional security, scalability, and monitoring requirements.