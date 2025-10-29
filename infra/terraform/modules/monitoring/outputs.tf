# CloudClearingAPI Monitoring Module - Outputs
# Version: 2.9.1 (CCAPI-28.1)

output "alarms_topic_arn" {
  description = "ARN of SNS topic for alarms"
  value       = aws_sns_topic.alarms.arn
}

output "dashboard_name" {
  description = "Name of CloudWatch dashboard"
  value       = var.enable_dashboard ? aws_cloudwatch_dashboard.main[0].dashboard_name : null
}
