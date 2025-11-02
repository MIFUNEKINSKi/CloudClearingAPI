# Step Functions Module - Weekly Monitoring Orchestration
# CCAPI-29.0: AWS Step Functions for automated pipeline execution

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# Step Functions State Machine
# ============================================================================

resource "aws_sfn_state_machine" "weekly_monitoring" {
  name     = "${var.project_name}-weekly-monitoring-${var.environment}"
  role_arn = aws_iam_role.step_functions.arn

  definition = templatefile("${path.module}/state_machine.asl.json", {
    ecs_cluster_arn           = var.ecs_cluster_arn
    monitor_task_definition   = var.monitor_task_definition_arn
    subnet_ids                = jsonencode(var.private_subnet_ids)
    security_group_ids        = jsonencode([var.ecs_security_group_id])
    sns_success_topic_arn     = aws_sns_topic.pipeline_success.arn
    sns_failure_topic_arn     = aws_sns_topic.pipeline_failure.arn
    s3_reports_bucket         = var.s3_reports_bucket
    s3_cache_bucket           = var.s3_cache_bucket
    cloudwatch_log_group      = aws_cloudwatch_log_group.step_functions.name
    gee_project_id            = var.gee_project_id
    environment               = var.environment
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true  # AWS X-Ray for distributed tracing
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-weekly-monitoring-${var.environment}"
    Component   = "orchestration"
    ManagedBy   = "terraform"
    Environment = var.environment
  })
}

# ============================================================================
# EventBridge Scheduler - Weekly Execution
# ============================================================================

resource "aws_cloudwatch_event_rule" "weekly_schedule" {
  name                = "${var.project_name}-weekly-schedule-${var.environment}"
  description         = "Trigger CloudClearingAPI weekly monitoring every Monday at 6am UTC"
  schedule_expression = var.schedule_expression  # Default: "cron(0 6 ? * MON *)"

  tags = merge(var.tags, {
    Name = "${var.project_name}-weekly-schedule-${var.environment}"
  })
}

resource "aws_cloudwatch_event_target" "step_functions" {
  rule     = aws_cloudwatch_event_rule.weekly_schedule.name
  arn      = aws_sfn_state_machine.weekly_monitoring.arn
  role_arn = aws_iam_role.eventbridge.arn

  input = jsonencode({
    execution_name = "weekly-monitoring-$${aws.scheduler.scheduled-time}"
    regions_count  = var.default_regions_count  # 29 Java regions
    enable_scraping = var.enable_web_scraping
    force_refresh   = false
  })

  retry_policy {
    maximum_event_age       = 3600  # 1 hour
    maximum_retry_attempts  = 2
  }

  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}

# ============================================================================
# SNS Topics for Notifications
# ============================================================================

resource "aws_sns_topic" "pipeline_success" {
  name              = "${var.project_name}-pipeline-success-${var.environment}"
  display_name      = "CloudClearingAPI Pipeline Success Notifications"
  kms_master_key_id = var.kms_key_id

  tags = merge(var.tags, {
    Name = "${var.project_name}-pipeline-success-${var.environment}"
  })
}

resource "aws_sns_topic" "pipeline_failure" {
  name              = "${var.project_name}-pipeline-failure-${var.environment}"
  display_name      = "CloudClearingAPI Pipeline Failure Alerts"
  kms_master_key_id = var.kms_key_id

  tags = merge(var.tags, {
    Name      = "${var.project_name}-pipeline-failure-${var.environment}"
    Severity  = "high"
    AlertType = "operational"
  })
}

# Optional email subscriptions
resource "aws_sns_topic_subscription" "pipeline_success_email" {
  count     = var.success_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_success.arn
  protocol  = "email"
  endpoint  = var.success_email
}

resource "aws_sns_topic_subscription" "pipeline_failure_email" {
  count     = var.failure_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_failure.arn
  protocol  = "email"
  endpoint  = var.failure_email
}

# Optional Slack webhook integration
resource "aws_sns_topic_subscription" "pipeline_failure_slack" {
  count     = var.slack_webhook_url != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_failure.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# ============================================================================
# Dead Letter Queue for Failed Events
# ============================================================================

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project_name}-eventbridge-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days
  kms_master_key_id         = var.kms_key_id

  tags = merge(var.tags, {
    Name = "${var.project_name}-eventbridge-dlq-${var.environment}"
  })
}

resource "aws_sqs_queue_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.dlq.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.weekly_schedule.arn
          }
        }
      }
    ]
  })
}

# ============================================================================
# CloudWatch Log Group
# ============================================================================

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_id

  tags = merge(var.tags, {
    Name = "${var.project_name}-step-functions-logs-${var.environment}"
  })
}

# ============================================================================
# CloudWatch Alarms
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "execution_failed" {
  alarm_name          = "${var.project_name}-step-functions-failed-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert when Step Functions execution fails"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.weekly_monitoring.arn
  }

  alarm_actions = [aws_sns_topic.pipeline_failure.arn]

  tags = merge(var.tags, {
    Name = "${var.project_name}-step-functions-failed-alarm-${var.environment}"
  })
}

resource "aws_cloudwatch_metric_alarm" "execution_timeout" {
  alarm_name          = "${var.project_name}-step-functions-timeout-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Maximum"
  threshold           = 10800000  # 3 hours in milliseconds
  alarm_description   = "Alert when Step Functions execution exceeds 3 hours"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.weekly_monitoring.arn
  }

  alarm_actions = [aws_sns_topic.pipeline_failure.arn]

  tags = merge(var.tags, {
    Name = "${var.project_name}-step-functions-timeout-alarm-${var.environment}"
  })
}

# ============================================================================
# IAM Role for Step Functions
# ============================================================================

resource "aws_iam_role" "step_functions" {
  name               = "${var.project_name}-step-functions-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume.json

  tags = merge(var.tags, {
    Name = "${var.project_name}-step-functions-role-${var.environment}"
  })
}

data "aws_iam_policy_document" "step_functions_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "step_functions" {
  name   = "${var.project_name}-step-functions-policy-${var.environment}"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions.json
}

data "aws_iam_policy_document" "step_functions" {
  # ECS task execution permissions
  statement {
    effect = "Allow"
    actions = [
      "ecs:RunTask",
      "ecs:StopTask",
      "ecs:DescribeTasks"
    ]
    resources = [
      var.monitor_task_definition_arn,
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task/${var.ecs_cluster_name}/*"
    ]
  }

  # IAM pass role for ECS task role and execution role
  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      var.ecs_task_role_arn,
      var.ecs_execution_role_arn
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }

  # SNS notifications
  statement {
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [
      aws_sns_topic.pipeline_success.arn,
      aws_sns_topic.pipeline_failure.arn
    ]
  }

  # X-Ray tracing
  statement {
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords"
    ]
    resources = ["*"]
  }
}

# ============================================================================
# IAM Role for EventBridge
# ============================================================================

resource "aws_iam_role" "eventbridge" {
  name               = "${var.project_name}-eventbridge-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume.json

  tags = merge(var.tags, {
    Name = "${var.project_name}-eventbridge-role-${var.environment}"
  })
}

data "aws_iam_policy_document" "eventbridge_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "eventbridge" {
  name   = "${var.project_name}-eventbridge-policy-${var.environment}"
  role   = aws_iam_role.eventbridge.id
  policy = data.aws_iam_policy_document.eventbridge.json
}

data "aws_iam_policy_document" "eventbridge" {
  # Start Step Functions execution
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      aws_sfn_state_machine.weekly_monitoring.arn
    ]
  }
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
