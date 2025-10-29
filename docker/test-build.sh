#!/bin/bash
# Docker Build & Test Script for CloudClearingAPI
# Version: 2.9.1 (CCAPI-28.0)
# Purpose: Automated testing of Docker build and runtime

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       CloudClearingAPI Docker Build & Test Script            ║${NC}"
echo -e "${BLUE}║                    Version 2.9.1                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Check Docker Installation
# ============================================================================
echo -e "${BLUE}[1/7] Checking Docker installation...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker Desktop"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed and running${NC}"
docker --version
echo ""

# ============================================================================
# Step 2: Clean Previous Builds (Optional)
# ============================================================================
echo -e "${BLUE}[2/7] Cleaning previous builds...${NC}"

read -p "Remove existing cloudclearing-api images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi cloudclearing-api:latest 2>/dev/null || true
    echo -e "${GREEN}✓ Cleaned previous images${NC}"
else
    echo -e "${YELLOW}⊘ Skipped cleaning${NC}"
fi
echo ""

# ============================================================================
# Step 3: Build Docker Image
# ============================================================================
echo -e "${BLUE}[3/7] Building Docker image...${NC}"
echo "This may take 5-10 minutes on first build..."

START_TIME=$(date +%s)

if DOCKER_BUILDKIT=1 docker build -t cloudclearing-api:latest . ; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    echo -e "${GREEN}✓ Build completed in ${BUILD_TIME} seconds${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# ============================================================================
# Step 4: Check Image Size
# ============================================================================
echo -e "${BLUE}[4/7] Checking image size...${NC}"

IMAGE_SIZE=$(docker images cloudclearing-api:latest --format "{{.Size}}")
echo "Image size: ${IMAGE_SIZE}"

# Convert size to MB for comparison
SIZE_MB=$(docker images cloudclearing-api:latest --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "0")

if (( $(echo "$SIZE_MB > 500" | bc -l 2>/dev/null || echo "0") )); then
    echo -e "${YELLOW}⚠ Image size exceeds 500MB target (${IMAGE_SIZE})${NC}"
else
    echo -e "${GREEN}✓ Image size within target (<500MB)${NC}"
fi
echo ""

# ============================================================================
# Step 5: Test Container Startup
# ============================================================================
echo -e "${BLUE}[5/7] Testing container startup and imports...${NC}"

if docker run --rm cloudclearing-api:latest python -c "
import sys
print('Python version:', sys.version)
print('')

# Test critical imports
modules = [
    'earthengine',
    'src.core.automated_monitor',
    'src.core.change_detector',
    'src.scrapers.scraper_orchestrator',
    'reportlab'
]

success = True
for module in modules:
    try:
        __import__(module)
        print(f'✓ {module} imported successfully')
    except ImportError as e:
        print(f'✗ {module} import failed: {e}')
        success = False

if not success:
    sys.exit(1)

print('')
print('✓ All critical modules loaded successfully')
"; then
    echo -e "${GREEN}✓ Container startup test passed${NC}"
else
    echo -e "${RED}✗ Container startup test failed${NC}"
    exit 1
fi
echo ""

# ============================================================================
# Step 6: Inspect Image Layers
# ============================================================================
echo -e "${BLUE}[6/7] Image layer analysis...${NC}"

echo "Top 10 largest layers:"
docker history cloudclearing-api:latest --format "table {{.Size}}\t{{.CreatedBy}}" --no-trunc | head -11
echo ""

# ============================================================================
# Step 7: Summary
# ============================================================================
echo -e "${BLUE}[7/7] Test Summary${NC}"
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    All Tests Passed! ✓                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Image Details:"
echo "  - Name: cloudclearing-api:latest"
echo "  - Size: ${IMAGE_SIZE}"
echo "  - Build Time: ${BUILD_TIME}s"
echo ""
echo "Next Steps:"
echo "  1. Test with docker-compose:"
echo "     $ docker-compose up"
echo ""
echo "  2. Run monitoring manually:"
echo "     $ docker run --rm \\"
echo "       -v \$(pwd)/cache:/app/cache \\"
echo "       -v \$(pwd)/output:/app/output \\"
echo "       -v \$(pwd)/credentials:/app/credentials:ro \\"
echo "       -e EARTHENGINE_PROJECT=your-project-id \\"
echo "       cloudclearing-api:latest"
echo ""
echo "  3. Push to ECR (see docs/deployment/docker-setup.md)"
echo ""
