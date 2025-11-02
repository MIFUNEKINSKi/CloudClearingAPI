# CloudClearingAPI Terraform Variables
# Version: 2.9.1 (CCAPI-28.1)

# ============================================================================
# General Configuration
# ============================================================================
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

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "AZ count must be between 2 and 3."
  }
}

# ============================================================================
# Network Configuration
# ============================================================================
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services (reduces egress costs)"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs for network monitoring"
  type        = bool
  default     = false  # Disabled by default to reduce costs
}

# ============================================================================
# Application Configuration
# ============================================================================
variable "earthengine_project" {
  description = "Google Earth Engine project ID"
  type        = string
}

variable "log_level" {
  description = "Application log level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

# ============================================================================
# ECS Configuration
# ============================================================================
variable "ecs_task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "2048"
  validation {
    condition     = contains(["256", "512", "1024", "2048", "4096"], var.ecs_task_cpu)
    error_message = "ECS task CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = string
  default     = "8192"
}

# ============================================================================
# Monitoring & Alerts
# ============================================================================
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

# ============================================================================
# Data Retention
# ============================================================================
variable "logs_retention_days" {
  description = "Number of days to retain logs in S3"
  type        = number
  default     = 90
}

# ============================================================================
# Step Functions / Orchestration
# ============================================================================
variable "step_functions_schedule" {
  description = "EventBridge schedule expression for weekly monitoring"
  type        = string
  default     = "cron(0 6 ? * MON *)"  # Every Monday at 6am UTC
}

variable "default_regions_count" {
  description = "Default number of regions to process in weekly monitoring"
  type        = number
  default     = 29
}

variable "enable_web_scraping" {
  description = "Enable web scraping for land price data"
  type        = bool
  default     = true
}

variable "pipeline_success_email" {
  description = "Email address for pipeline success notifications (empty to disable)"
  type        = string
  default     = ""
}

variable "pipeline_failure_email" {
  description = "Email address for pipeline failure notifications (empty to disable)"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for pipeline notifications (empty to disable)"
  type        = string
  default     = ""
  sensitive   = true
}
