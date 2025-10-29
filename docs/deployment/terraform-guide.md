# Terraform Infrastructure as Code Guide
**CloudClearingAPI v2.9.1 (CCAPI-28.1)**

Complete guide for deploying CloudClearingAPI infrastructure using Terraform on AWS.

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Module Architecture](#module-architecture)
5. [Deployment Workflow](#deployment-workflow)
6. [Configuration Reference](#configuration-reference)
7. [Cost Optimization](#cost-optimization)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Infrastructure Components

The Terraform configuration deploys a production-ready, scalable infrastructure:

- **Network:** VPC with public/private subnets, NAT Gateway, VPC endpoints
- **Data Lake:** S3 buckets (raw/staging/curated/logs) with lifecycle policies
- **Security:** IAM roles (least-privilege), KMS encryption, Secrets Manager
- **Compute:** ECS Fargate cluster, ECR repository, task definitions
- **Monitoring:** CloudWatch alarms, SNS notifications, dashboards, cost budgets

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                               │
│                                                                  │
│  ┌────────────── VPC (10.0.0.0/16) ──────────────────┐         │
│  │                                                     │         │
│  │  ┌─ Public Subnets (NAT, Load Balancers) ─┐      │         │
│  │  │  - 10.0.0.0/20  (us-east-1a)            │      │         │
│  │  │  - 10.0.1.0/20  (us-east-1b)            │      │         │
│  │  └──────────────────────────────────────────┘      │         │
│  │                    │                                │         │
│  │             [NAT Gateways]                          │         │
│  │                    │                                │         │
│  │  ┌─ Private Subnets (ECS, Lambda) ─────────┐      │         │
│  │  │  - 10.0.16.0/20 (us-east-1a)            │      │         │
│  │  │  - 10.0.17.0/20 (us-east-1b)            │      │         │
│  │  │                                          │      │         │
│  │  │  ┌─────────────────────────┐            │      │         │
│  │  │  │   ECS Fargate Tasks     │            │      │         │
│  │  │  │  (Weekly Monitoring)    │            │      │         │
│  │  │  └─────────────────────────┘            │      │         │
│  │  └──────────────────────────────────────────┘      │         │
│  │                                                     │         │
│  │  ┌─ VPC Endpoints ──────────────────────┐         │         │
│  │  │  - S3 (Gateway)                      │         │         │
│  │  │  - ECR API/DKR (Interface)           │         │         │
│  │  │  - Secrets Manager (Interface)       │         │         │
│  │  │  - CloudWatch Logs (Interface)       │         │         │
│  │  └──────────────────────────────────────┘         │         │
│  └─────────────────────────────────────────────────────┘         │
│                                                                  │
│  ┌─ Data Lake (S3) ───────────────────────────────┐            │
│  │  - cloudclearing-dev-raw-{account_id}          │            │
│  │  - cloudclearing-dev-staging-{account_id}      │            │
│  │  - cloudclearing-dev-curated-{account_id}      │            │
│  │  - cloudclearing-dev-logs-{account_id}         │            │
│  └────────────────────────────────────────────────┘            │
│                                                                  │
│  ┌─ Security ───────────────────────────────────┐              │
│  │  - KMS Key (data encryption)                 │              │
│  │  - Secrets Manager (GEE credentials, API keys)│              │
│  │  - IAM Roles (ECS, Lambda, Step Functions)   │              │
│  └──────────────────────────────────────────────┘              │
│                                                                  │
│  ┌─ Monitoring ─────────────────────────────────┐              │
│  │  - CloudWatch Alarms (CPU, Memory, Failures) │              │
│  │  - SNS Topics (Email notifications)          │              │
│  │  - CloudWatch Dashboard                      │              │
│  │  - AWS Budgets (Cost alerts)                 │              │
│  └──────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Install Required Tools

```bash
# Terraform (>= 1.5.0)
brew install terraform

# AWS CLI
brew install awscli

# Verify installations
terraform --version
aws --version
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify access
aws sts get-caller-identity
```

### 3. Prepare GEE Credentials

Ensure you have:
- Google Earth Engine project ID
- Service account JSON credentials file

---

## Quick Start

### Step 1: Initialize Terraform

```bash
cd infra/terraform

# Initialize Terraform (downloads providers)
terraform init
```

### Step 2: Configure Variables

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

**Minimum required configuration:**

```hcl
# terraform.tfvars
environment         = "dev"
earthengine_project = "your-gee-project-id"  # REQUIRED

alarm_email_endpoints = [
  "your-email@example.com"
]
```

### Step 3: Plan Deployment

```bash
# Review what Terraform will create
terraform plan

# Save plan for review
terraform plan -out=tfplan
```

### Step 4: Deploy Infrastructure

```bash
# Apply configuration
terraform apply

# Or use saved plan
terraform apply tfplan
```

**Deployment time:** ~5-7 minutes

### Step 5: Post-Deployment Configuration

After successful deployment, Terraform will output next steps. Follow them to:

1. Add GEE credentials to Secrets Manager
2. Push Docker image to ECR
3. Test ECS task execution

---

## Module Architecture

### Module Directory Structure

```
infra/terraform/
├── main.tf                      # Root configuration
├── variables.tf                 # Input variables
├── outputs.tf                   # Output values
├── terraform.tfvars.example     # Example configuration
├── modules/
│   ├── network/                 # VPC, subnets, routing
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── data_lake/               # S3 buckets, lifecycle policies
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── security/                # IAM, KMS, Secrets Manager
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/                 # ECS, ECR, task definitions
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── monitoring/              # CloudWatch, SNS, budgets
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
```

### Module Dependencies

```
network → security → data_lake → compute → monitoring
```

- **Network** creates VPC foundation (no dependencies)
- **Security** creates IAM roles, KMS keys (depends on Network for VPC ID)
- **Data Lake** creates S3 buckets (depends on Security for KMS key)
- **Compute** creates ECS cluster, tasks (depends on Network, Security, Data Lake)
- **Monitoring** creates alarms, dashboards (depends on Compute for ECS cluster)

---

## Deployment Workflow

### Environment-Based Deployment

Deploy separate environments using workspaces:

```bash
# Create dev environment
terraform workspace new dev
terraform workspace select dev
terraform apply -var="environment=dev"

# Create staging environment
terraform workspace new staging
terraform workspace select staging
terraform apply -var="environment=staging"

# Create production environment
terraform workspace new prod
terraform workspace select prod
terraform apply -var="environment=prod"
```

### State Management

#### Option 1: Local State (Dev/Testing)

Default configuration uses local state (`terraform.tfstate`).

**Pros:** Simple, no setup required  
**Cons:** Not suitable for team collaboration, no locking

#### Option 2: Remote State (Production)

Configure S3 backend for team collaboration:

```bash
# 1. Create S3 bucket for state
aws s3 mb s3://cloudclearing-terraform-state --region us-east-1

# 2. Enable versioning
aws s3api put-bucket-versioning \
  --bucket cloudclearing-terraform-state \
  --versioning-configuration Status=Enabled

# 3. Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name cloudclearing-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# 4. Uncomment backend configuration in main.tf
# backend "s3" { ... }

# 5. Migrate existing state
terraform init -migrate-state
```

---

## Configuration Reference

### Network Module

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `vpc_cidr` | VPC CIDR block | `10.0.0.0/16` | No |
| `enable_nat_gateway` | Enable NAT Gateway | `true` | No |
| `enable_vpc_endpoints` | Enable VPC endpoints | `true` | No |
| `enable_flow_logs` | Enable VPC flow logs | `false` | No |

**Cost Impact:**
- NAT Gateway: ~$32/month per AZ
- VPC Endpoints: $7-14/month (reduces data transfer costs)
- Flow Logs: ~$0.50/GB ingested

### Data Lake Module

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `logs_retention_days` | Log retention in S3 | `90` | No |
| `enable_event_notifications` | S3 event triggers | `false` | No |

**Storage Tiers:**
- **Raw:** 30 days Standard → Intelligent-Tiering → Glacier (90d) → Deep Archive (365d)
- **Staging:** 14 days Standard → Intelligent-Tiering
- **Curated:** 7 days Standard → Intelligent-Tiering → Glacier (180d)
- **Logs:** 30 days Standard → Standard-IA → Glacier (90d), expire after retention period

### Security Module

All IAM roles follow least-privilege principles. Secrets must be added manually after deployment.

### Compute Module

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `earthengine_project` | GEE project ID | - | **Yes** |
| `ecs_task_cpu` | CPU units | `2048` | No |
| `ecs_task_memory` | Memory (MB) | `8192` | No |
| `log_level` | Application log level | `INFO` | No |

**Task Sizing:**
- **Dev:** 1024 CPU / 4096 MB (~$0.05/hour)
- **Staging:** 2048 CPU / 8192 MB (~$0.10/hour)
- **Prod:** 4096 CPU / 16384 MB (~$0.20/hour)

### Monitoring Module

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `alarm_email_endpoints` | Email for alerts | `[]` | No |
| `monthly_budget_limit` | Budget in USD | `100` | No |
| `enable_dashboard` | CloudWatch dashboard | `true` | No |

---

## Cost Optimization

### Monthly Cost Estimates

#### Dev Environment (Minimal)

```
NAT Gateway:              $0    (disabled)
VPC Endpoints:            $7
S3 Storage:               $2    (10GB)
ECS Fargate:              $10   (20 hours/month)
CloudWatch:               $3
Secrets Manager:          $0.80 (2 secrets)
──────────────────────────────
Total:                    ~$23/month
```

#### Production Environment (Full)

```
NAT Gateway (2 AZs):      $64
VPC Endpoints:            $14
S3 Storage:               $10   (50GB raw + staging + curated)
ECS Fargate:              $40   (weekly runs, 4 hours/week)
CloudWatch:               $10   (logs + metrics + dashboard)
Secrets Manager:          $0.80
──────────────────────────────
Total:                    ~$139/month
```

### Cost Reduction Strategies

#### 1. Disable NAT Gateway in Dev

```hcl
# terraform.tfvars (dev)
enable_nat_gateway = false
```

**Savings:** $32/month per AZ  
**Trade-off:** ECS tasks need public IPs OR use VPC endpoints only

#### 2. Use FARGATE_SPOT

Already configured in compute module (80% weight to SPOT):

**Savings:** Up to 70% on compute costs  
**Trade-off:** Tasks may be interrupted (acceptable for scheduled monitoring)

#### 3. Optimize S3 Storage

- Enable Intelligent-Tiering (automatic cost optimization)
- Set aggressive lifecycle policies for temp data
- Use Deep Archive for long-term retention

#### 4. Right-Size ECS Tasks

Start small and scale up:

```hcl
# Start with minimal sizing
ecs_task_cpu    = "1024"  # 1 vCPU
ecs_task_memory = "4096"  # 4 GB
```

Monitor CloudWatch metrics and increase if needed.

---

## Troubleshooting

### Common Issues

#### 1. Terraform Init Fails

**Symptom:**
```
Error: Failed to query available provider packages
```

**Solution:**
```bash
# Clear Terraform cache
rm -rf .terraform .terraform.lock.hcl

# Re-initialize
terraform init
```

#### 2. Insufficient IAM Permissions

**Symptom:**
```
Error: Error creating VPC: UnauthorizedOperation
```

**Solution:**

Ensure your AWS credentials have these permissions:
- `ec2:*`
- `iam:*`
- `s3:*`
- `ecs:*`
- `ecr:*`
- `secretsmanager:*`
- `kms:*`
- `cloudwatch:*`
- `sns:*`
- `budgets:*`

#### 3. Resource Already Exists

**Symptom:**
```
Error: Error creating S3 bucket: BucketAlreadyExists
```

**Solution:**

Bucket names must be globally unique. Update `terraform.tfvars`:

```hcl
# Add unique suffix
project_name = "cloudclearing-yourcompany"
```

#### 4. State Lock Conflict

**Symptom:**
```
Error: Error acquiring the state lock
```

**Solution:**

```bash
# Force unlock (use with caution)
terraform force-unlock LOCK_ID

# Or wait for lock to expire (typically 15 minutes)
```

### Debugging Commands

```bash
# Validate configuration syntax
terraform validate

# Format code
terraform fmt -recursive

# Show current state
terraform show

# List resources in state
terraform state list

# Inspect specific resource
terraform state show module.network.aws_vpc.main

# Enable debug logging
export TF_LOG=DEBUG
terraform apply
```

---

## Advanced Topics

### Multi-Region Deployment

To deploy in multiple regions, create separate configurations:

```bash
# Directory structure
infra/terraform/
├── us-east-1/
│   ├── main.tf
│   └── terraform.tfvars
├── ap-southeast-1/
│   ├── main.tf
│   └── terraform.tfvars
└── modules/ (shared)
```

### Disaster Recovery

```bash
# Backup Terraform state
aws s3 cp s3://cloudclearing-terraform-state/terraform.tfstate \
  ./backups/terraform.tfstate.$(date +%Y%m%d)

# Snapshot infrastructure
terraform show -json > infrastructure-snapshot.json
```

### Infrastructure Drift Detection

```bash
# Detect changes outside Terraform
terraform plan -detailed-exitcode

# Exit code 2 = drift detected
# Exit code 0 = no changes
# Exit code 1 = error
```

---

## Next Steps

1. **Tier 3:** Configure Step Functions for scheduled monitoring
2. **Tier 3:** Implement dbt for data transformations
3. **Tier 4:** Set up comprehensive monitoring and alerting

See `docs/roadmap/v2.9-to-v3.0.md` for complete roadmap.

---

## Support

- **Documentation:** `/docs/deployment/terraform-guide.md` (this file)
- **Issues:** GitHub Issues
- **Terraform Registry:** https://registry.terraform.io/providers/hashicorp/aws/latest/docs
