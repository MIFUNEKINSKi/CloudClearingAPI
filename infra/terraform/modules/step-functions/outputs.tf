# Outputs for Step Functions Module

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.weekly_monitoring.arn
}

output "state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.weekly_monitoring.name
}

output "state_machine_id" {
  description = "ID of the Step Functions state machine"
  value       = aws_sfn_state_machine.weekly_monitoring.id
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule for weekly scheduling"
  value       = aws_cloudwatch_event_rule.weekly_schedule.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.weekly_schedule.name
}

output "sns_success_topic_arn" {
  description = "ARN of the SNS topic for success notifications"
  value       = aws_sns_topic.pipeline_success.arn
}

output "sns_failure_topic_arn" {
  description = "ARN of the SNS topic for failure notifications"
  value       = aws_sns_topic.pipeline_failure.arn
}

output "dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "ARN of the dead letter queue"
  value       = aws_sqs_queue.dlq.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group for Step Functions"
  value       = aws_cloudwatch_log_group.step_functions.name
}

output "step_functions_role_arn" {
  description = "ARN of the IAM role for Step Functions"
  value       = aws_iam_role.step_functions.arn
}

output "eventbridge_role_arn" {
  description = "ARN of the IAM role for EventBridge"
  value       = aws_iam_role.eventbridge.arn
}
