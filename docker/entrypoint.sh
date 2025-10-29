#!/bin/bash
# CloudClearingAPI Docker Entrypoint Script
# Version: 2.9.1 (CCAPI-28.0)
# Purpose: Initialize container environment and handle GEE authentication

set -e  # Exit on error

# ============================================================================
# Color codes for logging
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging functions
# ============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Signal handlers for graceful shutdown
# ============================================================================
cleanup() {
    log_warning "Received shutdown signal, cleaning up..."
    
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Save any in-progress work
    if [ -n "$MONITOR_PID" ]; then
        log_info "Waiting for monitoring process to complete..."
        wait $MONITOR_PID 2>/dev/null || true
    fi
    
    log_success "Cleanup complete"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# ============================================================================
# Environment validation
# ============================================================================
log_info "CloudClearingAPI Container Starting..."
log_info "Version: 2.9.1 (CCAPI-28.0)"
log_info "Python version: $(python --version)"

# Check required environment variables
if [ -z "$EARTHENGINE_PROJECT" ]; then
    log_warning "EARTHENGINE_PROJECT not set. GEE authentication may fail."
fi

# ============================================================================
# Google Earth Engine Authentication
# ============================================================================
log_info "Checking Google Earth Engine authentication..."

# Check if service account credentials exist
if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    log_success "Found GEE service account credentials: $GOOGLE_APPLICATION_CREDENTIALS"
    
    # Authenticate with service account
    log_info "Authenticating with GEE service account..."
    if earthengine authenticate --authorization-code="" --quiet 2>/dev/null || true; then
        log_success "GEE authentication successful (using cached credentials)"
    else
        # Try service account authentication via Python
        python -c "
import os
import earthengine as ee

try:
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    project = os.getenv('EARTHENGINE_PROJECT')
    
    if credentials_path and os.path.exists(credentials_path):
        credentials = ee.ServiceAccountCredentials(None, credentials_path)
        ee.Initialize(credentials, project=project)
        print('[SUCCESS] GEE initialized with service account')
    else:
        ee.Initialize(project=project)
        print('[SUCCESS] GEE initialized with default credentials')
except Exception as e:
    print(f'[ERROR] GEE initialization failed: {e}')
    exit(1)
" || {
            log_error "GEE authentication failed. Please check credentials."
            exit 1
        }
    fi
else
    log_warning "GEE service account credentials not found at: $GOOGLE_APPLICATION_CREDENTIALS"
    log_info "Attempting to initialize with default credentials..."
    
    python -c "
import os
import earthengine as ee

try:
    project = os.getenv('EARTHENGINE_PROJECT')
    ee.Initialize(project=project)
    print('[SUCCESS] GEE initialized with default credentials')
except Exception as e:
    print(f'[WARNING] GEE initialization failed: {e}')
    print('[INFO] Container will attempt to authenticate when running')
" || true
fi

# ============================================================================
# Directory initialization
# ============================================================================
log_info "Initializing application directories..."

# Ensure directories exist and are writable
for dir in "$CACHE_DIR" "$OUTPUT_DIR" "$OUTPUT_DIR/reports" "$OUTPUT_DIR/monitoring" "$OUTPUT_DIR/satellite_images"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" 2>/dev/null || log_warning "Could not create directory: $dir"
    fi
    
    if [ -w "$dir" ]; then
        log_success "Directory ready: $dir"
    else
        log_warning "Directory not writable: $dir"
    fi
done

# ============================================================================
# Configuration validation
# ============================================================================
log_info "Validating configuration..."

if [ -f "$CONFIG_PATH" ]; then
    log_success "Configuration file found: $CONFIG_PATH"
else
    log_warning "Configuration file not found: $CONFIG_PATH"
    log_info "Using default configuration from config.example.yaml"
    
    # Copy example config if available
    if [ -f "/app/config/config.example.yaml" ]; then
        cp /app/config/config.example.yaml "$CONFIG_PATH" 2>/dev/null || true
    fi
fi

# ============================================================================
# Cache statistics
# ============================================================================
if [ -d "$CACHE_DIR/gee" ]; then
    GEE_CACHE_COUNT=$(find "$CACHE_DIR/gee" -type f -name "*.tif" 2>/dev/null | wc -l)
    log_info "GEE cache entries: $GEE_CACHE_COUNT"
fi

if [ -d "$CACHE_DIR/osm" ]; then
    OSM_CACHE_COUNT=$(find "$CACHE_DIR/osm" -type f -name "*.json" 2>/dev/null | wc -l)
    log_info "OSM cache entries: $OSM_CACHE_COUNT"
fi

# ============================================================================
# Health check
# ============================================================================
log_info "Running health check..."

python -c "
import sys
try:
    # Test imports (note: earthengine-api uses 'ee' not 'earthengine')
    import ee
    import src.core.automated_monitor
    import src.core.change_detector
    import src.scrapers.scraper_orchestrator
    print('[SUCCESS] All critical modules imported successfully')
except ImportError as e:
    print(f'[ERROR] Module import failed: {e}')
    sys.exit(1)
" || {
    log_error "Health check failed"
    exit 1
}

log_success "Health check passed"

# ============================================================================
# Execute command
# ============================================================================
log_info "Starting application: $@"
log_info "Log level: $LOG_LEVEL"
log_info "----------------------------------------"

# Execute the command and capture PID for graceful shutdown
exec "$@" &
MONITOR_PID=$!

# Wait for process to complete
wait $MONITOR_PID

log_success "Application completed successfully"
