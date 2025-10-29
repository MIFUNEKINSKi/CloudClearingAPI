# Docker Deployment Guide
**CloudClearingAPI v2.9.1 (CCAPI-28.0)**

Complete guide for containerizing and deploying the CloudClearingAPI using Docker and Amazon ECR.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Amazon ECR Setup](#amazon-ecr-setup)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)
7. [Performance Optimization](#performance-optimization)

---

## Quick Start

### Prerequisites
- Docker Engine 20.10+ (with BuildKit support)
- Docker Compose 2.0+
- Google Earth Engine service account credentials
- AWS CLI (for ECR deployment)

### 1. Clone Repository
```bash
git clone https://github.com/MIFUNEKINSKi/CloudClearingAPI.git
cd CloudClearingAPI
```

### 2. Prepare Configuration
```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit configuration (set your GEE project ID, region coordinates, etc.)
nano config/config.yaml
```

### 3. Add GEE Credentials
```bash
# Create credentials directory
mkdir -p credentials

# Copy your GEE service account JSON file
cp ~/path/to/your-gee-service-account.json credentials/gee-service-account.json
```

### 4. Build and Run
```bash
# Build the Docker image
docker build -t cloudclearing-api:latest .

# Run with docker-compose
docker-compose up
```

---

## Local Development

### Building the Image

#### Standard Build
```bash
docker build -t cloudclearing-api:latest .
```

#### Build with Custom Tag
```bash
docker build -t cloudclearing-api:v2.9.1 .
```

#### Build with BuildKit (Faster)
```bash
DOCKER_BUILDKIT=1 docker build -t cloudclearing-api:latest .
```

#### Multi-Platform Build (ARM64 + AMD64)
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t cloudclearing-api:latest .
```

### Running the Container

#### Run Weekly Monitoring (Default)
```bash
docker run --rm \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/credentials:/app/credentials:ro \
  -e EARTHENGINE_PROJECT=your-gee-project-id \
  cloudclearing-api:latest
```

#### Run with Custom Command
```bash
docker run --rm \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/output:/app/output \
  -e EARTHENGINE_PROJECT=your-gee-project-id \
  cloudclearing-api:latest \
  python -c "import earthengine as ee; ee.Initialize(project='your-project'); print('GEE OK')"
```

#### Interactive Shell (Debugging)
```bash
docker run -it --rm \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/credentials:/app/credentials:ro \
  -e EARTHENGINE_PROJECT=your-gee-project-id \
  cloudclearing-api:latest \
  /bin/bash
```

### Using Docker Compose

#### Start Services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background (detached)
docker-compose up -d

# View logs
docker-compose logs -f monitor
```

#### Stop Services
```bash
# Graceful shutdown
docker-compose down

# Remove volumes (cache, output)
docker-compose down -v
```

#### Rebuild and Restart
```bash
# Rebuild image and restart
docker-compose up --build

# Force recreate containers
docker-compose up --force-recreate
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Google Earth Engine
EARTHENGINE_PROJECT=your-gee-project-id

# Paths
GEE_CREDENTIALS_PATH=./credentials

# Application Settings
LOG_LEVEL=INFO

# Optional: Email Alerts
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Slack/Discord Webhooks
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_TOKEN=xoxb-your-slack-token
```

### Volume Mounts Explained

| Host Path | Container Path | Purpose | Size (Typical) |
|-----------|---------------|---------|----------------|
| `./cache` | `/app/cache` | GEE + OSM cache (persistent) | 400-500MB |
| `./output` | `/app/output` | PDF reports, JSON data, satellite images | 50-100MB |
| `./logs` | `/app/logs` | Application logs | 10-20MB |
| `./config` | `/app/config` | Configuration files (read-only) | <1MB |
| `./credentials` | `/app/credentials` | GEE service account JSON (read-only) | <1MB |

---

## Production Deployment

### Image Size Optimization

The multi-stage Dockerfile is optimized for production:

- **Stage 1 (Builder):** Compiles dependencies with build tools (gcc, gdal-dev)
- **Stage 2 (Runtime):** Minimal image with only runtime libraries
- **Target Size:** <500MB (typically 300-400MB)

Check image size:
```bash
docker images cloudclearing-api:latest --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
```

### Security Best Practices

#### Non-Root User
The container runs as user `cloudclearing` (UID 1000), not root.

#### Read-Only Mounts
Configuration and credentials are mounted read-only:
```bash
-v $(pwd)/config:/app/config:ro
-v $(pwd)/credentials:/app/credentials:ro
```

#### Secrets Management
Never commit credentials to Git. Use:
- Docker secrets (Swarm mode)
- AWS Secrets Manager (ECS)
- Environment variables (injected at runtime)

#### Scan for Vulnerabilities
```bash
# Using Trivy
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image cloudclearing-api:latest
```

### Resource Limits

Set CPU and memory limits in `docker-compose.yml`:

```yaml
services:
  monitor:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

Or via `docker run`:
```bash
docker run --rm \
  --cpus=4.0 \
  --memory=8g \
  cloudclearing-api:latest
```

### Health Checks

The container includes a health check that validates:
- Python environment
- GEE authentication
- Critical module imports

Check health status:
```bash
docker inspect --format='{{.State.Health.Status}}' cloudclearing-monitor
```

---

## Amazon ECR Setup

### 1. Create ECR Repository

```bash
# Set variables
AWS_REGION=us-east-1
ECR_REPO_NAME=cloudclearing-api

# Create repository
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# Output will include: repositoryUri
```

### 2. Authenticate Docker to ECR

```bash
# Get login command
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $(aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text | cut -d'/' -f1)
```

### 3. Tag and Push Image

```bash
# Get ECR URI
ECR_URI=$(aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text)

# Tag image
docker tag cloudclearing-api:latest $ECR_URI:latest
docker tag cloudclearing-api:latest $ECR_URI:v2.9.1
docker tag cloudclearing-api:latest $ECR_URI:$(git rev-parse --short HEAD)

# Push all tags
docker push $ECR_URI:latest
docker push $ECR_URI:v2.9.1
docker push $ECR_URI:$(git rev-parse --short HEAD)
```

### 4. Verify Push

```bash
# List images in ECR
aws ecr list-images --repository-name $ECR_REPO_NAME --region $AWS_REGION

# Get image details
aws ecr describe-images --repository-name $ECR_REPO_NAME --region $AWS_REGION
```

### 5. Set Lifecycle Policy (Optional)

Keep only the last 10 images to save storage costs:

```bash
aws ecr put-lifecycle-policy \
  --repository-name $ECR_REPO_NAME \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }]
  }'
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `EARTHENGINE_PROJECT` | GEE Cloud Project ID | `my-gee-project-123456` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GEE service account JSON | `/app/credentials/gee-service-account.json` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONFIG_PATH` | Path to config.yaml | `/app/config/config.yaml` |
| `CACHE_DIR` | Cache directory | `/app/cache` |
| `OUTPUT_DIR` | Output directory | `/app/output` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `SMTP_USERNAME` | Email username for alerts | - |
| `SMTP_PASSWORD` | Email password for alerts | - |
| `WEBHOOK_URL` | Slack/Discord webhook URL | - |

---

## Troubleshooting

### Common Issues

#### 1. GEE Authentication Failed

**Symptom:**
```
[ERROR] GEE authentication failed. Please check credentials.
```

**Solution:**
```bash
# Verify credentials file exists
ls -la credentials/gee-service-account.json

# Verify EARTHENGINE_PROJECT is set
docker-compose config | grep EARTHENGINE_PROJECT

# Test authentication manually
docker run --rm \
  -v $(pwd)/credentials:/app/credentials:ro \
  -e EARTHENGINE_PROJECT=your-project-id \
  cloudclearing-api:latest \
  python -c "import earthengine as ee; ee.Initialize(project='your-project-id'); print('OK')"
```

#### 2. Permission Denied on Volumes

**Symptom:**
```
[WARNING] Directory not writable: /app/cache
```

**Solution:**
```bash
# Fix ownership (user ID 1000 = cloudclearing user in container)
sudo chown -R 1000:1000 cache/ output/ logs/

# Or run with current user
docker run --rm --user $(id -u):$(id -g) ...
```

#### 3. Image Size Too Large

**Symptom:**
```
Image size exceeds 500MB target
```

**Solution:**
```bash
# Remove unnecessary layers
docker build --squash -t cloudclearing-api:latest .

# Analyze layers
docker history cloudclearing-api:latest --no-trunc

# Use dive to inspect
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive cloudclearing-api:latest
```

#### 4. Out of Memory

**Symptom:**
```
Killed
```

**Solution:**
```bash
# Increase Docker memory limit (Docker Desktop settings)
# Or set explicit limits
docker run --memory=8g cloudclearing-api:latest
```

#### 5. Slow Build Times

**Solution:**
```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Use build cache
docker build --cache-from cloudclearing-api:latest -t cloudclearing-api:latest .

# Clean up build cache
docker builder prune
```

### Debugging Commands

```bash
# View container logs
docker logs cloudclearing-monitor

# Follow logs in real-time
docker logs -f cloudclearing-monitor

# Execute shell in running container
docker exec -it cloudclearing-monitor /bin/bash

# Inspect container
docker inspect cloudclearing-monitor

# Check resource usage
docker stats cloudclearing-monitor

# View container processes
docker top cloudclearing-monitor
```

---

## Performance Optimization

### 1. Cache Persistence

**Always mount cache volumes** to avoid re-downloading satellite data:

```yaml
volumes:
  - ./cache:/app/cache  # ✅ GEE cache persists between runs
```

**Cache Statistics:**
- **Cold run (no cache):** ~16 minutes for 29 regions
- **Warm run (100% cache hit):** ~0.9 minutes for 29 regions
- **Cache size:** ~400-500MB (GEE) + ~30MB (OSM)

### 2. Multi-Stage Build

The Dockerfile uses multi-stage builds to:
- Compile dependencies in builder stage (with gcc, build tools)
- Copy only runtime files to final stage (minimal image)
- Result: 60-70% size reduction vs single-stage build

### 3. Layer Caching

Optimize build order in Dockerfile:
1. Install system dependencies (changes rarely)
2. Copy `requirements.txt` and install Python packages (changes occasionally)
3. Copy application code (changes frequently)

This ensures fast rebuilds when only code changes.

### 4. Parallel Processing

The container supports async parallel processing:
- Default: 5 regions per batch
- Configurable via `run_weekly_java_monitor.py`

### 5. Resource Allocation

Recommended resources:
- **CPU:** 2-4 cores
- **Memory:** 4-8GB
- **Disk:** 1GB for cache + 200MB for outputs

---

## CI/CD Integration

### GitHub Actions Workflow

The project includes `.github/workflows/docker-build-push.yml`:

**Triggers:**
- Push to `main` branch
- Pull requests
- Manual workflow dispatch

**Jobs:**
1. **Build:** Compile image, run tests, check size
2. **Push to ECR:** Authenticate and push to Amazon ECR
3. **Security Scan:** Trivy vulnerability scanning

**Required Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Add secrets in GitHub repo settings:
```
Settings → Secrets and variables → Actions → New repository secret
```

### Manual ECR Push

```bash
# Build image
docker build -t cloudclearing-api:latest .

# Tag for ECR
ECR_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/cloudclearing-api
docker tag cloudclearing-api:latest $ECR_URI:latest

# Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(echo $ECR_URI | cut -d'/' -f1)

# Push
docker push $ECR_URI:latest
```

---

## Next Steps

- **Tier 3:** Configure AWS ECS/Fargate for container orchestration
- **Tier 3:** Set up Step Functions for scheduled monitoring
- **Tier 4:** Configure CloudWatch for monitoring and alerting

See `docs/roadmap/v2.9-to-v3.0.md` for full roadmap.

---

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/MIFUNEKINSKi/CloudClearingAPI/issues
- **Documentation:** `docs/README.md`
- **Architecture:** `docs/architecture/data_flow.md`
