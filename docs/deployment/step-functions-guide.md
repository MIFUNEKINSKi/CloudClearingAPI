# AWS Step Functions Orchestration Guide
**CloudClearingAPI v2.9.1-tier3 (CCAPI-29.0)**

Complete guide for deploying and managing the AWS Step Functions orchestration layer that automates weekly monitoring execution.

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment](#deployment)
5. [Configuration](#configuration)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Manual Execution](#manual-execution)
8. [Troubleshooting](#troubleshooting)
9. [Cost Management](#cost-management)

---

## Overview

### What is Step Functions Orchestration?

AWS Step Functions coordinates the CloudClearingAPI weekly monitoring pipeline as a **serverless workflow**. Instead of running `python run_weekly_java_monitor.py` manually or via cron, Step Functions:

1. **Schedules execution** automatically (every Monday 6am UTC via EventBridge)
2. **Runs ECS Fargate tasks** with proper resource allocation (2 vCPU, 4GB memory)
3. **Handles failures** with retry logic and dead letter queues
4. **Sends notifications** via SNS (email/Slack) on success or failure
5. **Publishes metrics** to CloudWatch for dashboarding

### Benefits Over Manual Execution

| Feature | Manual (`python` script) | Step Functions |
|---------|-------------------------|----------------|
| **Scheduling** | Cron job / manual trigger | EventBridge automatic |
| **Failure handling** | Exit code check only | Retry logic, catch blocks, DLQ |
| **Notifications** | None (requires custom code) | SNS topics (email/Slack) |
| **Observability** | CloudWatch logs only | Logs + metrics + X-Ray tracing |
| **Cost tracking** | Manual log analysis | CloudWatch dashboard + budgets |
| **Error isolation** | Script stops on error | Partial failure handling |

---

## Architecture

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                 EventBridge Scheduler                            │
│              cron(0 6 ? * MON *)                                │
│         (Every Monday 6am UTC)                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ Triggers
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          AWS Step Functions State Machine                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │  1. ValidateInputs (ECS Task - Quick Check)                │ │
│  │     └─> Verify GEE auth, S3 buckets exist                  │ │
│  │     └─> Retry: 2x, 30s interval                            │ │
│  │                                                             │ │
│  │  2. RunWeeklyMonitoring (ECS Task - Main Pipeline)         │ │
│  │     └─> Command: python run_weekly_java_monitor.py         │ │
│  │     └─> Resources: 2 vCPU, 4GB memory                      │ │
│  │     └─> Timeout: 2 hours (7200s)                           │ │
│  │     └─> Heartbeat: 10 minutes (600s)                       │ │
│  │     └─> Process 29 Java regions                            │ │
│  │     └─> Generate PDF reports → S3                          │ │
│  │                                                             │ │
│  │  3. CheckExecutionStatus (Choice State)                    │ │
│  │     ├─> Exit code 0 → ExtractResults                       │ │
│  │     └─> Exit code ≠ 0 → HandlePartialFailure               │ │
│  │                                                             │ │
│  │  4. PublishMetrics (CloudWatch PutMetricData)              │ │
│  │     └─> WeeklyMonitoringSuccess: 1                         │ │
│  │     └─> ExecutionDuration: <seconds>                       │ │
│  │                                                             │ │
│  │  5. NotifySuccess (SNS Publish)                            │ │
│  │     └─> Topic: pipeline-success                            │ │
│  │     └─> Subject: ✅ Weekly Monitoring Complete             │ │
│  │     └─> Body: Execution summary + S3 report links          │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ On Failure
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│         Error Handling Path                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • Catch block captures error details                      │ │
│  │  • NotifyFailure (SNS Publish)                             │ │
│  │    └─> Topic: pipeline-failure                             │ │
│  │    └─> Subject: 🚨 Pipeline FAILED                         │ │
│  │    └─> Body: Error details + CloudWatch logs link          │ │
│  │  • FailExecution (Terminal State)                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### State Machine Components

#### 1. ValidateInputs (Task State)
**Purpose:** Pre-flight checks before heavy processing

**What it validates:**
- GEE service account credentials exist in Secrets Manager
- GEE authentication succeeds (`ee.Initialize()`)
- S3 buckets (reports, cache) are accessible
- Config file (`config.yaml`) loads correctly

**Retry policy:**
- 2 attempts
- 30 second interval
- 2.0 backoff multiplier

**Why it matters:** Catches configuration errors in <30 seconds instead of wasting 1+ hour of ECS runtime.

#### 2. RunWeeklyMonitoring (Task State)
**Purpose:** Main pipeline execution

**Container command:**
```bash
python run_weekly_java_monitor.py --auto-confirm
```

**Environment variables:**
- `GEE_PROJECT_ID`: Google Earth Engine project ID
- `S3_REPORTS_BUCKET`: S3 bucket for PDF reports
- `S3_CACHE_BUCKET`: S3 bucket for OSM/scraper cache
- `LOG_LEVEL`: INFO (configurable)
- `ENVIRONMENT`: dev/staging/prod

**Resource allocation:**
- CPU: 2 vCPU (2048 units)
- Memory: 4GB (4096 MB)
- Network: Private subnet with NAT Gateway or VPC endpoints

**Timeout configuration:**
- Task timeout: 2 hours (7200s)
- Heartbeat: 10 minutes (600s) - task must report progress
- If heartbeat missed: State machine considers task stalled

**Retry policy:**
- Timeout errors: 1 retry after 60s
- ECS service errors: 2 retries with 2.0 backoff (120s, 240s intervals)

#### 3. CheckExecutionStatus (Choice State)
**Purpose:** Route based on container exit code

**Routing logic:**
```json
{
  "Variable": "$.monitoring.Containers[0].ExitCode",
  "NumericEquals": 0,
  "Next": "ExtractResults"
}
```

**Exit code meanings:**
- `0`: Full success (all 29 regions processed)
- `1-255`: Partial or complete failure (some regions failed/skipped)

#### 4. ExtractResults (Pass State)
**Purpose:** Transform raw ECS task output into structured data

**Output format:**
```json
{
  "execution_id": "weekly-monitoring-2025-10-29T06:00:00Z",
  "start_time": "2025-10-29T06:00:01.234Z",
  "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/ccapi-cluster-prod/abc123",
  "exit_code": 0,
  "s3_reports_bucket": "ccapi-reports-prod",
  "environment": "prod"
}
```

#### 5. PublishMetrics (Task State)
**Purpose:** Send custom metrics to CloudWatch

**Metrics published:**

| Metric Name | Value | Unit | Description |
|-------------|-------|------|-------------|
| `WeeklyMonitoringSuccess` | 1 | Count | Incremented on success |
| `ExecutionDuration` | `<seconds>` | Seconds | Total pipeline runtime |

**Namespace:** `CloudClearingAPI`  
**Dimensions:** `Environment=prod`

#### 6. NotifySuccess (Task State)
**Purpose:** Send success notification via SNS

**Email format:**
```
Subject: ✅ CloudClearingAPI Weekly Monitoring Complete - prod

Body:
- Summary: Successfully completed weekly monitoring for 29 Java regions
- Execution ID: weekly-monitoring-2025-10-29T06:00:00Z
- Start Time: 2025-10-29T06:00:01.234Z
- Duration: 5432 seconds (~1.5 hours)
- S3 Reports: s3://ccapi-reports-prod/weekly/
- Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=CloudClearingAPI-prod
```

#### 7. NotifyFailure (Task State)
**Purpose:** Send failure alert via SNS

**Email format:**
```
Subject: 🚨 CloudClearingAPI Pipeline FAILED - prod

Body:
- Summary: Critical failure in weekly monitoring pipeline
- Execution ID: weekly-monitoring-2025-10-29T06:00:00Z
- Error: {"error_type": "ECS.TaskFailed", "cause": "Container exited with code 1"}
- Logs: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group//aws/stepfunctions/ccapi-prod
- Action Required: Investigate logs and retry execution if appropriate
```

---

## Prerequisites

### 1. Completed Tier 2 (Docker + Terraform)

Ensure you have:
- ✅ Docker image built and pushed to ECR
- ✅ Terraform modules deployed (network, compute, security, data_lake, monitoring)
- ✅ ECS cluster running with task definitions
- ✅ S3 buckets created (reports, cache)
- ✅ GEE credentials in AWS Secrets Manager

Verify:
```bash
# Check ECS cluster exists
aws ecs describe-clusters --clusters ccapi-cluster-prod

# Check ECR image exists
aws ecr describe-images --repository-name ccapi-monitor-prod

# Check S3 buckets exist
aws s3 ls | grep ccapi

# Check Secrets Manager
aws secretsmanager list-secrets | grep gee-credentials
```

### 2. AWS CLI Configured

```bash
# Verify AWS CLI authentication
aws sts get-caller-identity

# Should return account ID and user/role ARN
```

### 3. Terraform Installed

```bash
terraform --version
# Terraform v1.5.0 or higher required
```

---

## Deployment

### Step 1: Update Terraform Variables

Edit `infra/terraform/terraform.tfvars` (or create if doesn't exist):

```hcl
# Environment
project_name = "ccapi"
environment  = "prod"
aws_region   = "us-east-1"

# Google Earth Engine
earthengine_project = "your-gee-project-id"

# Step Functions Configuration
step_functions_schedule  = "cron(0 6 ? * MON *)"  # Every Monday 6am UTC
default_regions_count    = 29
enable_web_scraping      = true

# Notification Configuration
pipeline_success_email = "reports@yourcompany.com"
pipeline_failure_email = "alerts@yourcompany.com"
# slack_webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"  # Optional

# ECS Task Resources
ecs_task_cpu    = "2048"  # 2 vCPU
ecs_task_memory = "4096"  # 4 GB

# Monitoring
alarm_email_endpoints = ["ops@yourcompany.com"]
monthly_budget_limit  = "200"  # USD

# Network
enable_nat_gateway   = true   # Required for internet access
enable_vpc_endpoints = true   # Reduces egress costs
```

### Step 2: Plan Terraform Changes

```bash
cd infra/terraform

# Initialize Terraform (if first time)
terraform init

# Review changes
terraform plan

# Should show:
# + module.step_functions.aws_sfn_state_machine.weekly_monitoring
# + module.step_functions.aws_cloudwatch_event_rule.weekly_schedule
# + module.step_functions.aws_sns_topic.pipeline_success
# + module.step_functions.aws_sns_topic.pipeline_failure
# + module.step_functions.aws_sqs_queue.dlq
# + module.step_functions.aws_iam_role.step_functions
# + module.step_functions.aws_iam_role.eventbridge
# + (8+ more resources)
```

### Step 3: Deploy Step Functions Module

```bash
terraform apply

# Review plan, type 'yes' to confirm

# Deployment time: ~2-3 minutes
```

### Step 4: Confirm SNS Email Subscriptions

After `terraform apply`, AWS sends confirmation emails:

1. Check your inbox for emails from `no-reply@sns.amazonaws.com`
2. Click "Confirm subscription" link
3. Repeat for both success and failure topics

**Without confirmation:** You won't receive notifications!

Verify subscriptions:
```bash
# Check success topic
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw pipeline_success_topic_arn)

# Check failure topic
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw pipeline_failure_topic_arn)

# Confirmed subscriptions show "SubscriptionArn": "arn:aws:sns:..."
# Pending show "SubscriptionArn": "PendingConfirmation"
```

### Step 5: Validate State Machine

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(terraform output -raw step_functions_state_machine_arn)

# Describe state machine
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN

# Check for "status": "ACTIVE"
```

### Step 6: Test Manual Execution (Optional)

Before waiting for Monday 6am, test manually:

```bash
# Start execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name manual-test-$(date +%Y%m%d-%H%M%S) \
  --input '{
    "execution_name": "manual-test",
    "regions_count": 3,
    "enable_scraping": false
  }'

# Get execution ARN from output, then monitor
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# Watch logs
aws logs tail /aws/stepfunctions/ccapi-prod --follow
```

---

## Configuration

### Scheduling Options

#### Change Execution Time

**Weekly on different day/time:**
```hcl
# Every Wednesday at 3am UTC
step_functions_schedule = "cron(0 3 ? * WED *)"

# Every Friday at 10pm UTC
step_functions_schedule = "cron(0 22 ? * FRI *)"
```

#### Change Frequency

**Daily:**
```hcl
# Every day at 6am UTC
step_functions_schedule = "cron(0 6 * * ? *)"
```

**Bi-weekly:**
```hcl
# Every other Monday (use Lambda to skip alternating weeks)
# Or manually disable/enable EventBridge rule
```

**On-demand only (disable automatic):**
```hcl
# Set schedule to invalid expression
step_functions_schedule = "cron(0 0 1 1 ? 2099)"  # Year 2099

# Or disable after deployment:
aws events disable-rule --name ccapi-weekly-schedule-prod
```

### Notification Channels

#### Email Only (Default)

```hcl
pipeline_success_email = "reports@yourcompany.com"
pipeline_failure_email = "alerts@yourcompany.com"
slack_webhook_url      = ""  # Empty = disabled
```

#### Slack Integration

1. Create Slack incoming webhook:
   - Go to https://api.slack.com/apps
   - Create app → Add "Incoming Webhooks"
   - Copy webhook URL

2. Add to Terraform:
   ```hcl
   slack_webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

3. Apply:
   ```bash
   terraform apply
   ```

#### PagerDuty Integration

```hcl
# Add PagerDuty email integration endpoint
pipeline_failure_email = "your-integration-key@events.pagerduty.com"
```

### Resource Allocation

#### For Small Datasets (<10 regions)

```hcl
ecs_task_cpu    = "1024"  # 1 vCPU
ecs_task_memory = "2048"  # 2 GB
```

#### For Standard Workload (29 regions)

```hcl
ecs_task_cpu    = "2048"  # 2 vCPU (recommended)
ecs_task_memory = "4096"  # 4 GB (recommended)
```

#### For Large Datasets (>50 regions)

```hcl
ecs_task_cpu    = "4096"  # 4 vCPU
ecs_task_memory = "8192"  # 8 GB
```

**Note:** Must be valid ECS Fargate combinations. See [AWS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html).

---

## Monitoring & Alerts

### CloudWatch Dashboard

Access the auto-generated dashboard:

```bash
# Get dashboard URL
echo "https://console.aws.amazon.com/cloudwatch/home?region=$(terraform output -raw aws_region)#dashboards:name=$(terraform output -raw dashboard_name)"
```

**Dashboard widgets:**
- Step Functions execution status (success/fail counts)
- Execution duration trend
- ECS task CPU/memory utilization
- S3 bucket size (reports)
- Cost trends

### CloudWatch Alarms

Two alarms are pre-configured:

#### 1. ExecutionsFailed
- **Trigger:** Any Step Functions execution fails
- **Period:** 5 minutes
- **Threshold:** >0 failures
- **Action:** Publish to failure SNS topic

#### 2. ExecutionTimeout
- **Trigger:** Execution exceeds 3 hours
- **Period:** 5 minutes
- **Threshold:** >10,800,000 milliseconds
- **Action:** Publish to failure SNS topic

### Custom Metrics

Query published metrics:

```bash
# Get success count (last 7 days)
aws cloudwatch get-metric-statistics \
  --namespace CloudClearingAPI \
  --metric-name WeeklyMonitoringSuccess \
  --dimensions Name=Environment,Value=prod \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Get execution duration (last 30 days)
aws cloudwatch get-metric-statistics \
  --namespace CloudClearingAPI \
  --metric-name ExecutionDuration \
  --dimensions Name=Environment,Value=prod \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 604800 \
  --statistics Average,Maximum
```

### Viewing Execution History

```bash
# List last 10 executions
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --max-results 10

# Filter by status
aws stepfunctions list-executions \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --status-filter FAILED \
  --max-results 20

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn> \
  --query 'output' \
  --output text | jq .
```

---

## Manual Execution

### Via AWS Console

1. Navigate to **Step Functions** console
2. Select `ccapi-weekly-monitoring-prod` state machine
3. Click **Start execution**
4. (Optional) Provide custom input:
   ```json
   {
     "execution_name": "manual-test-20251029",
     "regions_count": 5,
     "enable_scraping": false,
     "force_refresh": true
   }
   ```
5. Click **Start execution**
6. Monitor progress in **Graph view**

### Via AWS CLI

```bash
# Full 29-region execution
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --name manual-full-$(date +%Y%m%d-%H%M%S)

# Partial execution (3 regions, no scraping)
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --name manual-partial-$(date +%Y%m%d-%H%M%S) \
  --input '{
    "regions_count": 3,
    "enable_scraping": false
  }'

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn-from-previous-command> \
  --query 'status'
```

### Stopping Running Execution

```bash
# Stop execution
aws stepfunctions stop-execution \
  --execution-arn <execution-arn> \
  --cause "Manual cancellation - testing different configuration"

# Verify stopped
aws stepfunctions describe-execution \
  --execution-arn <execution-arn> \
  --query 'status'  # Should show "ABORTED"
```

---

## Troubleshooting

### Issue: State Machine Fails Immediately at ValidateInputs

**Symptoms:**
- Execution fails within 30 seconds
- Error: `ResourceNotFoundException` or `AccessDeniedException`

**Causes:**
1. GEE credentials missing from Secrets Manager
2. S3 buckets don't exist
3. IAM permissions insufficient

**Solutions:**

```bash
# 1. Check GEE credentials
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw gee_credentials_secret_arn) \
  --query 'SecretString'

# If empty, add credentials:
aws secretsmanager put-secret-value \
  --secret-id $(terraform output -raw gee_credentials_secret_arn) \
  --secret-string file://path/to/gee-service-account.json

# 2. Check S3 buckets exist
aws s3 ls | grep ccapi
# Should show: ccapi-curated-prod, ccapi-staging-prod, etc.

# 3. Check IAM policy
aws iam get-role-policy \
  --role-name ccapi-step-functions-prod \
  --policy-name ccapi-step-functions-policy-prod
# Verify "s3:GetObject", "s3:PutObject", "secretsmanager:GetSecretValue" actions
```

### Issue: RunWeeklyMonitoring Times Out After 2 Hours

**Symptoms:**
- Execution reaches `RunWeeklyMonitoring` state
- Times out after exactly 7200 seconds (2 hours)
- ECS task still shows "RUNNING"

**Causes:**
1. GEE API rate limiting (too many requests)
2. Web scraping taking too long
3. Network issues (NAT Gateway connectivity)

**Solutions:**

```bash
# 1. Increase timeout in state machine
# Edit infra/terraform/modules/step-functions/state_machine.asl.json
# Line 80: Change "TimeoutSeconds": 7200 to 10800 (3 hours)

# 2. Disable web scraping temporarily
# In terraform.tfvars:
enable_web_scraping = false

terraform apply

# 3. Check NAT Gateway connectivity
aws ec2 describe-nat-gateways \
  --filter "Name=tag:Project,Values=ccapi" \
  --query 'NatGateways[*].[NatGatewayId,State]'
# Should show "available"

# 4. Check VPC endpoints working
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$(terraform output -raw vpc_id)" \
  --query 'VpcEndpoints[*].[ServiceName,State]'
# All should show "available"
```

### Issue: SNS Notifications Not Received

**Symptoms:**
- Execution completes successfully
- No email received

**Causes:**
1. Email subscription not confirmed
2. Email in spam folder
3. SNS topic KMS key policy incorrect

**Solutions:**

```bash
# 1. Check subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw pipeline_success_topic_arn)

# If "SubscriptionArn": "PendingConfirmation":
# - Check email (including spam folder)
# - Resend confirmation:
aws sns subscribe \
  --topic-arn $(terraform output -raw pipeline_success_topic_arn) \
  --protocol email \
  --notification-endpoint your@email.com

# 2. Test SNS manually
aws sns publish \
  --topic-arn $(terraform output -raw pipeline_success_topic_arn) \
  --subject "Test Notification" \
  --message "This is a test from AWS CLI"

# 3. Check KMS key policy
aws kms get-key-policy \
  --key-id $(terraform output -raw kms_key_id) \
  --policy-name default \
  --query 'Policy' \
  --output text | jq .
# Verify SNS service principal has "kms:Decrypt" permission
```

### Issue: EventBridge Rule Not Triggering

**Symptoms:**
- No automatic executions on Monday 6am UTC
- EventBridge rule shows "Enabled"

**Causes:**
1. Rule schedule expression incorrect
2. IAM role lacks `states:StartExecution` permission
3. Dead letter queue filled up

**Solutions:**

```bash
# 1. Check rule status
aws events describe-rule \
  --name $(terraform output -raw eventbridge_schedule_rule)

# Verify:
# - "State": "ENABLED"
# - "ScheduleExpression": "cron(0 6 ? * MON *)"

# 2. Check IAM permissions
aws iam get-role-policy \
  --role-name ccapi-eventbridge-prod \
  --policy-name ccapi-eventbridge-policy-prod

# 3. Check DLQ messages
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw dlq_url) \
  --attribute-names ApproximateNumberOfMessages

# If messages > 0, inspect them:
aws sqs receive-message \
  --queue-url $(terraform output -raw dlq_url) \
  --max-number-of-messages 1

# 4. Manually trigger to test
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --name manual-eventbridge-test-$(date +%Y%m%d-%H%M%S)
```

### Issue: Partial Failure (Some Regions Succeed, Others Fail)

**Symptoms:**
- Execution completes but returns non-zero exit code
- SNS notification: "⚠️ Partial Failure"
- Some PDF reports in S3, others missing

**Expected Behavior:**
- This is normal! Individual regions can fail due to:
  - GEE image collection empty (no satellite data)
  - OSM API timeout (infrastructure query)
  - Web scraping failure (market data)

**Solutions:**

```bash
# 1. Review ECS task logs to identify failed regions
aws logs filter-log-events \
  --log-group-name /aws/ecs/ccapi-prod \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 day ago' +%s)000

# 2. Manually process failed regions
# SSH into environment with CloudClearingAPI code:
python -c "
from src.core.automated_monitor import AutomatedMonitor
import asyncio

async def rerun_region():
    monitor = AutomatedMonitor()
    result = await monitor.analyze_region('Failed Region Name')
    print(result)

asyncio.run(rerun_region())
"

# 3. For persistent failures, check region configuration
# in src/indonesia_expansion_regions.py
```

---

## Cost Management

### Monthly Cost Breakdown

**Step Functions:**
- State transitions: ~40 per execution
- Weekly executions: 4 per month
- Total transitions: 160
- Cost: $0.025 per 1,000 transitions = **$0.004/month**

**ECS Fargate:**
- vCPU: 2 × $0.04048/hour
- Memory: 4GB × $0.004445/GB/hour
- Total: $0.045/hour
- Duration: 1.5 hours per execution
- Weekly: 4 executions
- Cost: $0.045 × 1.5 × 4 = **$0.27/month**

**EventBridge:**
- Invocations: 4 per month
- First 1M free = **$0.00/month**

**SNS:**
- Email notifications: 8 per month (4 success + 4 failure)
- Email delivery: Free
- Cost: **$0.00/month**

**CloudWatch Logs:**
- Log volume: ~200MB per execution
- Monthly: 800MB
- Cost: $0.50 per GB = **$0.40/month**

**CloudWatch Metrics:**
- Custom metrics: 2 per execution
- Monthly: 8 metrics
- First 10,000 free = **$0.00/month**

**Total Step Functions Orchestration: ~$0.71/month**

**Note:** This excludes base infrastructure costs (NAT Gateway, S3 storage, VPC endpoints) which are shared with other components.

### Cost Optimization Strategies

#### 1. Reduce Execution Frequency

```hcl
# Bi-weekly instead of weekly
step_functions_schedule = "rate(14 days)"
# Savings: 50% reduction = ~$0.36/month
```

#### 2. Use Smaller ECS Tasks for Testing

```hcl
# Dev environment
ecs_task_cpu    = "1024"  # 1 vCPU instead of 2
ecs_task_memory = "2048"  # 2GB instead of 4GB
# Savings: ~50% on ECS costs in dev
```

#### 3. Disable Web Scraping

```hcl
# Use cached data only
enable_web_scraping = false
# Savings: Reduces execution time by ~20% = ~$0.05/month
```

#### 4. Adjust Log Retention

```hcl
# Reduce from 90 days to 30 days
logs_retention_days = 30
# Savings: ~60% on log storage
```

---

## Next Steps

After successfully deploying Step Functions orchestration:

1. **Monitor first automatic execution:** Wait for Monday 6am UTC, verify SNS notification received
2. **Review CloudWatch dashboard:** Confirm metrics populating correctly
3. **Test failure scenarios:** Intentionally break something (remove GEE creds) to verify alerts work
4. **Proceed to Tier 3:** Implement dbt data transformations (CCAPI-29.1)

---

**Last Updated:** October 29, 2025  
**Version:** v2.9.1-tier3 (CCAPI-29.0)  
**Status:** Production-Ready
