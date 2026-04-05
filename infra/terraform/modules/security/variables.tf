# CloudClearingAPI Security Module - Variables
# Version: 2.9.1 (CCAPI-28.1)

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "cloudclearing"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "kms_deletion_window_days" {
  description = "Number of days before KMS key deletion"
  type        = number
  default     = 30
}

variable "secret_recovery_window_days" {
  description = "Number of days before secret permanent deletion"
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
