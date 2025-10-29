# CloudClearingAPI Compute Module - Outputs
# Version: 2.9.1 (CCAPI-28.1)

output "ecr_repository_url" {
  description = "URL of ECR repository"
  value       = aws_ecr_repository.main.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of ECR repository"
  value       = aws_ecr_repository.main.arn
}

output "ecs_cluster_id" {
  description = "ID of ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_arn" {
  description = "ARN of ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_cluster_name" {
  description = "Name of ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "weekly_monitoring_task_definition_arn" {
  description = "ARN of weekly monitoring task definition"
  value       = aws_ecs_task_definition.weekly_monitoring.arn
}

output "weekly_monitoring_task_definition_family" {
  description = "Family of weekly monitoring task definition"
  value       = aws_ecs_task_definition.weekly_monitoring.family
}

output "ecs_tasks_security_group_id" {
  description = "ID of ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "ecs_tasks_log_group_name" {
  description = "Name of ECS tasks CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs_tasks.name
}
