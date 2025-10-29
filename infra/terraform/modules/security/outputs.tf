# CloudClearingAPI Security Module - Outputs
# Version: 2.9.1 (CCAPI-28.1)

output "kms_key_id" {
  description = "ID of KMS encryption key"
  value       = aws_kms_key.main.id
}

output "kms_key_arn" {
  description = "ARN of KMS encryption key"
  value       = aws_kms_key.main.arn
}

output "gee_credentials_secret_arn" {
  description = "ARN of GEE credentials secret"
  value       = aws_secretsmanager_secret.gee_credentials.arn
}

output "api_keys_secret_arn" {
  description = "ARN of API keys secret"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "ecs_task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "lambda_execution_role_arn" {
  description = "ARN of Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions role"
  value       = aws_iam_role.step_functions.arn
}

output "cicd_ecr_push_policy_arn" {
  description = "ARN of CI/CD ECR push policy"
  value       = aws_iam_policy.cicd_ecr_push.arn
}
