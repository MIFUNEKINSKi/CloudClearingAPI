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

- **Network:** VPC with public/private subnets across 2 AZs; **NAT Gateways optional** (`enable_nat_gateway`)
- **Data Lake:** 4 S3 buckets (raw, staging, curated, logs) with lifecycle policies
- **Security:** IAM roles, KMS encryption keys, Secrets Manager for credentials
- **Compute:** ECS Fargate cluster, ECR repository, task definitions
- **Monitoring:** CloudWatch alarms, SNS topics, dashboards, cost budgets
- **Orchestration (root module):** Step Functions state machine + EventBridge schedule for weekly ECS RunTask

## Cost estimate

- **Dev with NAT (`enable_nat_gateway = true`):** on the order of **~\$35–45+/month** (NAT is the main fixed line item) plus Fargate while tasks run.
- **Dev without NAT (`enable_nat_gateway = false`):** **no NAT hourly charges**; Step Functions uses **public subnets** and **`AssignPublicIp: ENABLED`** for the monitoring task. Remaining cost is mostly **Fargate (per run)**, S3/ECR/logs — often **low single-digit \$**/month for a weekly job if sized modestly.
- **\$0:** do not apply, or **`terraform destroy`** when you are not demoing — IaC in Git remains the portfolio artifact.

See **[`docs/deployment/cost-aware-aws.md`](../../docs/deployment/cost-aware-aws.md)** and [`docs/deployment/terraform-guide.md`](../../docs/deployment/terraform-guide.md).

## Module structure

```
modules/
├── network/         # VPC, subnets, routing, optional NAT, VPC endpoints
├── data_lake/       # S3 buckets with intelligent tiering
├── security/        # IAM, KMS, Secrets Manager
├── compute/         # ECS Fargate, ECR, task definitions
├── monitoring/      # CloudWatch, SNS, budgets
└── step-functions/  # Weekly pipeline state machine (wired from root main.tf)
```

## Required Variables

**Minimum configuration in `terraform.tfvars`:**

```hcl
environment         = "dev"
earthengine_project = "your-gee-project-id"  # REQUIRED

pipeline_success_email = "your-email@example.com"
pipeline_failure_email = "your-email@example.com"

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

- **Cost-aware dev (no NAT):** [`docs/deployment/cost-aware-aws.md`](../../docs/deployment/cost-aware-aws.md)
- **Full Guide:** [`docs/deployment/terraform-guide.md`](../../docs/deployment/terraform-guide.md)
- **Docker Setup:** [`docs/deployment/docker-setup.md`](../../docs/deployment/docker-setup.md)
- **Roadmap:** [`DEVELOPMENT_ROADMAP.md`](../../DEVELOPMENT_ROADMAP.md) (canonical) · [`docs/roadmap/v2.9-to-v3.0.md`](../../docs/roadmap/v2.9-to-v3.0.md)

## Support

- **Issues:** https://github.com/MIFUNEKINSKi/CloudClearingAPI/issues
- **Terraform Docs:** https://registry.terraform.io/providers/hashicorp/aws/latest/docs
