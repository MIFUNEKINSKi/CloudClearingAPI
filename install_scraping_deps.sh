#!/bin/bash
# Installation script for web scraping dependencies
# CloudClearingAPI - October 19, 2025

echo "================================================"
echo "Installing Web Scraping Dependencies"
echo "================================================"
echo ""

# Install required packages
echo "Installing: requests, beautifulsoup4, lxml"
python3 -m pip install requests beautifulsoup4 lxml

echo ""
echo "================================================"
echo "Verifying Installation"
echo "================================================"
echo ""

# Verify installation
python3 -c "
import requests
import bs4
import lxml

print('✓ requests version:', requests.__version__)
print('✓ beautifulsoup4 version:', bs4.__version__)
print('✓ lxml available')
print('')
print('All dependencies installed successfully!')
"

echo ""
echo "================================================"
echo "Testing Scraper System"
echo "================================================"
echo ""

# Test import
python3 -c "
import sys
sys.path.insert(0, '.')

from src.scrapers.scraper_orchestrator import LandPriceOrchestrator

orchestrator = LandPriceOrchestrator(enable_live_scraping=False)
result = orchestrator.get_land_price('Sleman Yogyakarta')

print('✓ Scraper system operational')
print(f'✓ Fallback benchmark: Rp {result[\"average_price_per_m2\"]:,.0f}/m²')
print('')
print('Ready to use!')
"

echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo "1. Run test suite: python3 test_web_scraping.py"
echo "2. View documentation: cat WEB_SCRAPING_DOCUMENTATION.md"
echo "3. Check cache directory: ls output/scraper_cache/"
echo ""
