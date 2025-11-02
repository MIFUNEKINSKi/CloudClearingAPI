# Variables for Step Functions Module

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ccapi"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# ============================================================================
# ECS Configuration
# ============================================================================

variable "ecs_cluster_arn" {
  description = "ARN of the ECS cluster where tasks will run"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "monitor_task_definition_arn" {
  description = "ARN of the monitoring task definition"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ARN of the ECS execution role"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# ============================================================================
# S3 Configuration
# ============================================================================

variable "s3_reports_bucket" {
  description = "S3 bucket name for generated reports"
  type        = string
}

variable "s3_cache_bucket" {
  description = "S3 bucket name for cache data"
  type        = string
}

# ============================================================================
# Scheduler Configuration
# ============================================================================

variable "schedule_expression" {
  description = "EventBridge schedule expression for weekly execution"
  type        = string
  default     = "cron(0 6 ? * MON *)"  # Every Monday at 6am UTC
}

variable "default_regions_count" {
  description = "Default number of regions to process"
  type        = number
  default     = 29
}

variable "enable_web_scraping" {
  description = "Enable web scraping for land price data"
  type        = bool
  default     = true
}

# ============================================================================
# Notification Configuration
# ============================================================================

variable "success_email" {
  description = "Email address for success notifications (empty to disable)"
  type        = string
  default     = ""
}

variable "failure_email" {
  description = "Email address for failure notifications (empty to disable)"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for failure notifications (empty to disable)"
  type        = string
  default     = ""
  sensitive   = true
}

# ============================================================================
# Security Configuration
# ============================================================================

variable "kms_key_id" {
  description = "KMS key ID for encrypting SNS topics and SQS queues"
  type        = string
}

# ============================================================================
# Application Configuration
# ============================================================================

variable "gee_project_id" {
  description = "Google Earth Engine project ID"
  type        = string
}

# ============================================================================
# Logging Configuration
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# ============================================================================
# Tags
# ============================================================================

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
