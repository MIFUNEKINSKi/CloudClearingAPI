# CloudClearingAPI Compute Module - Variables
# Version: 2.9.1 (CCAPI-28.1)

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "cloudclearing"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of ECS task role"
  type        = string
}

variable "gee_credentials_secret_arn" {
  description = "ARN of GEE credentials secret"
  type        = string
}

variable "api_keys_secret_arn" {
  description = "ARN of API keys secret"
  type        = string
}

variable "earthengine_project" {
  description = "Google Earth Engine project ID"
  type        = string
}

variable "task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "2048"
}

variable "task_memory" {
  description = "Memory for ECS task (MB)"
  type        = string
  default     = "8192"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "Number of days to retain ECS task logs"
  type        = number
  default     = 30
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "CloudClearingAPI"
    ManagedBy = "Terraform"
  }
}
