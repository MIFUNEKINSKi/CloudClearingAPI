# CloudClearingAPI Terraform Outputs
# Version: 2.9.1 (CCAPI-28.1)

# ============================================================================
# Network Outputs
# ============================================================================
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.network.public_subnet_ids
}

# ============================================================================
# Security Outputs
# ============================================================================
output "kms_key_id" {
  description = "ID of KMS encryption key"
  value       = module.security.kms_key_id
}

output "gee_credentials_secret_arn" {
  description = "ARN of GEE credentials secret (add credentials via AWS Console)"
  value       = module.security.gee_credentials_secret_arn
}

output "api_keys_secret_arn" {
  description = "ARN of API keys secret (add keys via AWS Console)"
  value       = module.security.api_keys_secret_arn
}

# ============================================================================
# Data Lake Outputs
# ============================================================================
output "raw_bucket_name" {
  description = "Name of raw data S3 bucket"
  value       = module.data_lake.raw_bucket_id
}

output "staging_bucket_name" {
  description = "Name of staging data S3 bucket"
  value       = module.data_lake.staging_bucket_id
}

output "curated_bucket_name" {
  description = "Name of curated data S3 bucket"
  value       = module.data_lake.curated_bucket_id
}

output "logs_bucket_name" {
  description = "Name of logs S3 bucket"
  value       = module.data_lake.logs_bucket_id
}

# ============================================================================
# Compute Outputs
# ============================================================================
output "ecr_repository_url" {
  description = "URL of ECR repository for Docker images"
  value       = module.compute.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "Name of ECS cluster"
  value       = module.compute.ecs_cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of ECS cluster"
  value       = module.compute.ecs_cluster_arn
}

output "weekly_monitoring_task_definition_arn" {
  description = "ARN of weekly monitoring task definition"
  value       = module.compute.weekly_monitoring_task_definition_arn
}

# ============================================================================
# Monitoring Outputs
# ============================================================================
output "alarms_topic_arn" {
  description = "ARN of SNS topic for alarms"
  value       = module.monitoring.alarms_topic_arn
}

output "dashboard_name" {
  description = "Name of CloudWatch dashboard"
  value       = module.monitoring.dashboard_name
}

# ============================================================================
# Step Functions Outputs
# ============================================================================
output "step_functions_state_machine_arn" {
  description = "ARN of Step Functions state machine for weekly monitoring"
  value       = module.step_functions.state_machine_arn
}

output "step_functions_state_machine_name" {
  description = "Name of Step Functions state machine"
  value       = module.step_functions.state_machine_name
}

output "eventbridge_schedule_rule" {
  description = "Name of EventBridge rule for weekly execution"
  value       = module.step_functions.eventbridge_rule_name
}

output "pipeline_success_topic_arn" {
  description = "ARN of SNS topic for pipeline success notifications"
  value       = module.step_functions.sns_success_topic_arn
}

output "pipeline_failure_topic_arn" {
  description = "ARN of SNS topic for pipeline failure notifications"
  value       = module.step_functions.sns_failure_topic_arn
}

# ============================================================================
# Quick Start Commands
# ============================================================================
output "next_steps" {
  description = "Quick start commands"
  value = <<-EOT
    
    ╔════════════════════════════════════════════════════════════════╗
    ║       CloudClearingAPI Infrastructure Deployed ✓               ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Next Steps:
    
    1. Add GEE Credentials to Secrets Manager:
       aws secretsmanager put-secret-value \
         --secret-id ${module.security.gee_credentials_secret_arn} \
         --secret-string file://path/to/gee-service-account.json
    
    2. Push Docker Image to ECR:
       aws ecr get-login-password --region ${var.aws_region} | \
         docker login --username AWS --password-stdin ${module.compute.ecr_repository_url}
       docker tag cloudclearing-api:latest ${module.compute.ecr_repository_url}:latest
       docker push ${module.compute.ecr_repository_url}:latest
    
    3. Test ECS Task:
       aws ecs run-task \
         --cluster ${module.compute.ecs_cluster_name} \
         --task-definition ${module.compute.weekly_monitoring_task_definition_arn} \
         --launch-type FARGATE \
         --network-configuration "awsvpcConfiguration={subnets=[${join(",", module.network.private_subnet_ids)}],securityGroups=[${module.compute.ecs_tasks_security_group_id}]}"
    
    4. View Logs:
       aws logs tail /aws/ecs/${var.project_name}-${var.environment} --follow
    
    5. Access Dashboard:
       https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${module.monitoring.dashboard_name}
  EOT
}
