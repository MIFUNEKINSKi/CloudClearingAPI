# CloudClearingAPI Data Lake Module - Variables
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

variable "aws_account_id" {
  description = "AWS account ID for unique bucket naming"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for S3 encryption"
  type        = string
}

variable "logs_retention_days" {
  description = "Number of days to retain logs in S3"
  type        = number
  default     = 90
}

variable "enable_event_notifications" {
  description = "Enable S3 event notifications for Lambda processing"
  type        = bool
  default     = false
}

variable "raw_data_processor_lambda_arn" {
  description = "ARN of Lambda function for raw data processing"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "CloudClearingAPI"
    ManagedBy = "Terraform"
  }
}
