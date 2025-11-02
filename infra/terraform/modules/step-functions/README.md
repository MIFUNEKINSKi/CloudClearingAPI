# Step Functions Module

Orchestrates weekly monitoring pipeline execution using AWS Step Functions with ECS Fargate integration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EventBridge Scheduler                        │
│                (Every Monday 6am UTC)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                Step Functions State Machine                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. ValidateInputs (ECS Task)                               │ │
│  │    └─> Verify GEE auth, S3 access, config                 │ │
│  │                                                             │ │
│  │ 2. RunWeeklyMonitoring (ECS Task - 2 vCPU, 4GB)           │ │
│  │    └─> Execute run_weekly_java_monitor.py                 │ │
│  │    └─> Process 29 Java regions                            │ │
│  │    └─> Generate PDF reports                               │ │
│  │                                                             │ │
│  │ 3. CheckExecutionStatus (Choice State)                     │ │
│  │    ├─> Exit code 0 → ExtractResults                       │ │
│  │    └─> Exit code ≠ 0 → HandlePartialFailure               │ │
│  │                                                             │ │
│  │ 4. PublishMetrics (CloudWatch Metrics)                     │ │
│  │    └─> Success count, duration, region stats              │ │
│  │                                                             │ │
│  │ 5. NotifySuccess (SNS) OR NotifyFailure (SNS)             │ │
│  │    └─> Email/Slack notifications                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Outputs                                     │
│  • S3 Reports Bucket: Weekly PDFs                               │
│  • S3 Cache Bucket: OSM/scraper cache                           │
│  • CloudWatch Logs: Execution traces                            │
│  • CloudWatch Metrics: Success/failure rates                    │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Scheduled Execution:** EventBridge triggers every Monday 6am UTC
- **ECS Fargate Integration:** Runs monitoring as containerized task (no server management)
- **Retry Logic:** Automatic retries for transient failures (timeouts, ECS service issues)
- **Error Handling:** Comprehensive catch blocks with SNS notifications
- **Metrics Publishing:** CloudWatch custom metrics for success rate and duration
- **X-Ray Tracing:** Distributed tracing for debugging
- **Dead Letter Queue:** Captures failed EventBridge invocations

## Resources Created

| Resource | Purpose |
|----------|---------|
| `aws_sfn_state_machine.weekly_monitoring` | Main orchestration workflow |
| `aws_cloudwatch_event_rule.weekly_schedule` | Monday 6am UTC trigger |
| `aws_sns_topic.pipeline_success` | Success notifications |
| `aws_sns_topic.pipeline_failure` | Failure alerts |
| `aws_sqs_queue.dlq` | Dead letter queue for EventBridge |
| `aws_cloudwatch_log_group.step_functions` | Execution logs |
| `aws_cloudwatch_metric_alarm.execution_failed` | Failure alarm |
| `aws_cloudwatch_metric_alarm.execution_timeout` | Timeout alarm (>3 hours) |
| `aws_iam_role.step_functions` | IAM role for state machine |
| `aws_iam_role.eventbridge` | IAM role for EventBridge |

## Usage

### Basic Configuration

```hcl
module "step_functions" {
  source = "./modules/step-functions"

  project_name = "ccapi"
  environment  = "prod"

  # ECS Configuration
  ecs_cluster_arn             = module.compute.ecs_cluster_arn
  ecs_cluster_name            = module.compute.ecs_cluster_name
  monitor_task_definition_arn = module.compute.monitor_task_definition_arn
  ecs_task_role_arn           = module.security.ecs_task_role_arn
  ecs_execution_role_arn      = module.security.ecs_execution_role_arn
  private_subnet_ids          = module.network.private_subnet_ids
  ecs_security_group_id       = module.network.ecs_security_group_id

  # S3 Configuration
  s3_reports_bucket = module.data_lake.reports_bucket_name
  s3_cache_bucket   = module.data_lake.cache_bucket_name

  # Notifications
  failure_email = "alerts@yourcompany.com"
  success_email = "reports@yourcompany.com"

  # Application
  gee_project_id = var.gee_project_id
  kms_key_id     = module.security.kms_key_id

  tags = local.common_tags
}
```

### With Custom Schedule

```hcl
module "step_functions" {
  source = "./modules/step-functions"
  
  # ... other config ...
  
  # Run every Wednesday at 3am UTC instead
  schedule_expression = "cron(0 3 ? * WED *)"
}
```

### With Slack Notifications

```hcl
module "step_functions" {
  source = "./modules/step-functions"
  
  # ... other config ...
  
  failure_email     = "alerts@yourcompany.com"
  slack_webhook_url = var.slack_webhook_url  # From Secrets Manager or variables
}
```

## State Machine Workflow

### State Definitions

1. **ValidateInputs**
   - Type: ECS Task (sync)
   - Purpose: Quick validation (<30s) before heavy processing
   - Checks: GEE auth, S3 bucket access, config validity
   - Retry: 2 attempts, 30s interval

2. **RunWeeklyMonitoring**
   - Type: ECS Task (sync)
   - Purpose: Main monitoring pipeline execution
   - Timeout: 2 hours (7200s)
   - Heartbeat: 10 minutes (600s)
   - Retry: 1 timeout retry + 2 ECS service error retries
   - Resources: 2 vCPU, 4GB memory

3. **CheckExecutionStatus**
   - Type: Choice
   - Routes based on container exit code
   - Success (0) → ExtractResults
   - Failure (≠0) → HandlePartialFailure

4. **PublishMetrics**
   - Type: CloudWatch PutMetricData
   - Metrics: Success count, execution duration
   - Namespace: `CloudClearingAPI`
   - Dimensions: Environment

5. **NotifySuccess / NotifyFailure**
   - Type: SNS Publish
   - Includes execution ID, logs link, S3 report location
   - Email subject prefixes: ✅ (success), 🚨 (failure), ⚠️ (partial)

### Error Handling Strategy

```
Any State Error
      │
      ├─> Transient errors (timeout, ECS service)
      │   └─> Retry with exponential backoff
      │
      └─> Permanent errors (invalid config, auth failure)
          └─> Skip retries → NotifyFailure → FailExecution
```

## Monitoring

### CloudWatch Alarms

**ExecutionsFailed:**
- Triggers when any execution fails
- Evaluation: 1 period, 5 minutes
- Action: Publish to failure SNS topic

**ExecutionTimeout:**
- Triggers when execution exceeds 3 hours
- Indicates: Stuck task or runaway process
- Action: Publish to failure SNS topic

### Custom Metrics

Published to `CloudClearingAPI` namespace:

| Metric | Unit | Description |
|--------|------|-------------|
| `WeeklyMonitoringSuccess` | Count | Incremented on successful completion |
| `ExecutionDuration` | Seconds | Total pipeline runtime |

### Viewing Execution Logs

```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn <arn> \
  --max-results 10

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>

# View CloudWatch logs
aws logs tail /aws/stepfunctions/ccapi-prod \
  --follow \
  --format short
```

## Cost Estimation

**State Machine Executions:**
- $0.025 per 1,000 state transitions
- Weekly execution: ~10 transitions
- Monthly: ~$0.01

**ECS Fargate:**
- 2 vCPU: $0.04048/hour
- 4GB memory: $0.004445/hour
- Total: ~$0.045/hour
- 2-hour execution: ~$0.09/week
- Monthly: ~$0.36

**EventBridge:**
- First 1M invocations/month: Free
- Negligible cost

**SNS:**
- $0.50 per 1M requests
- Email notifications: Free
- Monthly: <$0.01

**CloudWatch Logs:**
- $0.50 per GB ingested
- ~100MB per execution
- Monthly: ~$0.02

**Total: ~$0.40/month** (excluding ECS costs, which are same as manual execution)

## Troubleshooting

### Execution Failed Immediately

**Symptom:** State machine fails at `ValidateInputs`

**Causes:**
- GEE service account credentials missing/invalid
- S3 buckets don't exist or no access
- ECS task definition not found

**Solution:**
```bash
# Check ECS task can start
aws ecs run-task \
  --cluster ccapi-cluster-prod \
  --task-definition ccapi-monitor:latest \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"

# Check task logs
aws logs tail /ecs/ccapi-monitor --follow
```

### Execution Times Out

**Symptom:** State machine fails at `RunWeeklyMonitoring` with timeout

**Causes:**
- Network issues (NAT Gateway down, VPC endpoints misconfigured)
- GEE API rate limiting
- Web scraping timeouts

**Solution:**
1. Increase timeout in `state_machine.asl.json` (line 80)
2. Check VPC endpoint connectivity:
   ```bash
   # From ECS task
   nslookup s3.amazonaws.com
   nslookup earthengine.googleapis.com
   ```
3. Review CloudWatch logs for bottlenecks

### SNS Notifications Not Received

**Symptom:** No emails despite execution completion

**Causes:**
- Email subscription not confirmed
- SNS topic KMS key policy incorrect

**Solution:**
```bash
# Check subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:123456789012:ccapi-pipeline-success-prod

# Resend confirmation
aws sns subscribe \
  --topic-arn <arn> \
  --protocol email \
  --notification-endpoint your@email.com

# Check KMS key policy allows SNS
aws kms get-key-policy \
  --key-id <key-id> \
  --policy-name default
```

### Partial Failures

**Symptom:** Pipeline completes but some regions failed

**Behavior:**
- State machine marks as failed
- SNS notification sent with partial failure details
- Successful regions' reports still in S3

**Resolution:**
- Review ECS task logs for specific region failures
- Retry execution or manually process failed regions

## Manual Execution

### Via AWS Console

1. Navigate to Step Functions console
2. Select `ccapi-weekly-monitoring-prod`
3. Click "Start execution"
4. Provide input (optional):
   ```json
   {
     "execution_name": "manual-test-20251029",
     "regions_count": 29,
     "enable_scraping": true,
     "force_refresh": false
   }
   ```

### Via AWS CLI

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:ccapi-weekly-monitoring-prod \
  --name manual-execution-$(date +%Y%m%d-%H%M%S) \
  --input '{
    "regions_count": 29,
    "enable_scraping": true
  }'
```

## Disabling Automatic Execution

```bash
# Disable EventBridge rule
aws events disable-rule \
  --name ccapi-weekly-schedule-prod

# Re-enable later
aws events enable-rule \
  --name ccapi-weekly-schedule-prod
```

## Security Considerations

- **Least Privilege IAM:** Step Functions role can only run specific ECS task definitions
- **Network Isolation:** ECS tasks run in private subnets with no public IP
- **KMS Encryption:** SNS topics and SQS DLQ encrypted at rest
- **X-Ray Tracing:** Helps identify security issues in distributed workflow
- **VPC Endpoints:** No internet traffic for AWS service calls (S3, ECR, CloudWatch)

## Dependencies

This module requires:
- `modules/network` - VPC, subnets, security groups
- `modules/compute` - ECS cluster, task definitions
- `modules/security` - IAM roles, KMS keys
- `modules/data_lake` - S3 buckets

## Outputs

See `outputs.tf` for all exported values. Key outputs:
- `state_machine_arn` - For manual execution triggers
- `sns_failure_topic_arn` - For custom alert integrations
- `log_group_name` - For log queries and dashboards
