# CloudClearingAPI Monitoring Infrastructure
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: CloudWatch alarms, SNS topics, dashboards

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# SNS Topic for Alarms
# ============================================================================
resource "aws_sns_topic" "alarms" {
  name              = "${var.project_name}-${var.environment}-alarms"
  display_name      = "CloudClearingAPI Alarms"
  kms_master_key_id = var.kms_key_id
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-alarms-topic"
      Environment = var.environment
    }
  )
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count     = length(var.alarm_email_endpoints)
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email_endpoints[count.index]
}

# ============================================================================
# CloudWatch Alarms - ECS Task Failures
# ============================================================================
resource "aws_cloudwatch_metric_alarm" "ecs_task_failed" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-task-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "TasksFailed"
  namespace           = "ECS/ContainerInsights"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when ECS tasks fail"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-task-failed-alarm"
      Environment = var.environment
    }
  )
}

# ============================================================================
# CloudWatch Alarms - High CPU Usage
# ============================================================================
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alert when ECS CPU usage is high"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-cpu-high-alarm"
      Environment = var.environment
    }
  )
}

# ============================================================================
# CloudWatch Alarms - High Memory Usage
# ============================================================================
resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alert when ECS memory usage is high"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  
  dimensions = {
    ClusterName = var.ecs_cluster_name
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-memory-high-alarm"
      Environment = var.environment
    }
  )
}

# ============================================================================
# CloudWatch Alarms - Cost Budget (optional)
# ============================================================================
resource "aws_budgets_budget" "monthly_cost" {
  count        = var.enable_cost_alerts ? 1 : 0
  name         = "${var.project_name}-${var.environment}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alarm_email_endpoints
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alarm_email_endpoints
  }
}

# ============================================================================
# CloudWatch Dashboard (optional)
# ============================================================================
resource "aws_cloudwatch_dashboard" "main" {
  count          = var.enable_dashboard ? 1 : 0
  dashboard_name = "${var.project_name}-${var.environment}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU %" }],
            [".", "MemoryUtilization", { stat = "Average", label = "Memory %" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Resource Utilization"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["ECS/ContainerInsights", "TaskCount", { stat = "Average" }],
            [".", "TasksFailed", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Task Metrics"
        }
      }
    ]
  })
}
