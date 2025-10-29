# CloudClearingAPI Terraform Infrastructure

**Version:** 2.9.1 (CCAPI-28.1)

Production-ready AWS infrastructure for the CloudClearingAPI satellite monitoring platform.

## Quick Start

```bash
# 1. Initialize Terraform
terraform init

# 2. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your settings

# 3. Plan deployment
terraform plan

# 4. Deploy infrastructure
terraform apply
```

## What Gets Deployed

- **Network:** VPC with public/private subnets across 2 AZs, NAT Gateways, VPC endpoints
- **Data Lake:** 4 S3 buckets (raw, staging, curated, logs) with lifecycle policies
- **Security:** IAM roles, KMS encryption keys, Secrets Manager for credentials
- **Compute:** ECS Fargate cluster, ECR repository, task definitions
- **Monitoring:** CloudWatch alarms, SNS topics, dashboards, cost budgets

## Cost Estimate

- **Dev (minimal):** ~$23/month
- **Production (full):** ~$139/month

See `docs/deployment/terraform-guide.md` for cost optimization strategies.

## Module Structure

```
modules/
├── network/      # VPC, subnets, routing, VPC endpoints
├── data_lake/    # S3 buckets with intelligent tiering
├── security/     # IAM, KMS, Secrets Manager
├── compute/      # ECS Fargate, ECR, task definitions
└── monitoring/   # CloudWatch, SNS, budgets
```

## Required Variables

**Minimum configuration in `terraform.tfvars`:**

```hcl
environment         = "dev"
earthengine_project = "your-gee-project-id"  # REQUIRED

alarm_email_endpoints = [
  "your-email@example.com"
]
```

## Post-Deployment

After `terraform apply` completes:

1. **Add GEE Credentials:**
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id $(terraform output -raw gee_credentials_secret_arn) \
     --secret-string file://path/to/gee-service-account.json
   ```

2. **Push Docker Image:**
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url | cut -d'/' -f1)
   docker tag cloudclearing-api:latest $(terraform output -raw ecr_repository_url):latest
   docker push $(terraform output -raw ecr_repository_url):latest
   ```

3. **Test ECS Task:**
   ```bash
   aws ecs run-task \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --task-definition $(terraform output -raw weekly_monitoring_task_definition_arn) \
     --launch-type FARGATE
   ```

## Outputs

All outputs are available via:

```bash
terraform output
```

Key outputs:
- `ecr_repository_url` - Docker image repository
- `ecs_cluster_name` - ECS cluster name
- `raw_bucket_name` - S3 raw data bucket
- `gee_credentials_secret_arn` - Secrets Manager ARN

## Documentation

- **Full Guide:** [`docs/deployment/terraform-guide.md`](../../docs/deployment/terraform-guide.md)
- **Docker Setup:** [`docs/deployment/docker-setup.md`](../../docs/deployment/docker-setup.md)
- **Roadmap:** [`docs/roadmap/v2.9-to-v3.0.md`](../../docs/roadmap/v2.9-to-v3.0.md)

## Support

- **Issues:** https://github.com/MIFUNEKINSKi/CloudClearingAPI/issues
- **Terraform Docs:** https://registry.terraform.io/providers/hashicorp/aws/latest/docs
