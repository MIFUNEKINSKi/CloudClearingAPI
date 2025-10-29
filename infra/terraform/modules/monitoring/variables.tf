# CloudClearingAPI Monitoring Module - Variables
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

variable "kms_key_id" {
  description = "ID of KMS key for SNS encryption"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of ECS cluster to monitor"
  type        = string
}

variable "alarm_email_endpoints" {
  description = "Email addresses for alarm notifications"
  type        = list(string)
  default     = []
}

variable "enable_cost_alerts" {
  description = "Enable AWS Budgets cost alerts"
  type        = bool
  default     = true
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "100"
}

variable "enable_dashboard" {
  description = "Enable CloudWatch dashboard"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "CloudClearingAPI"
    ManagedBy = "Terraform"
  }
}
