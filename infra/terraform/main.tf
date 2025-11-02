# CloudClearingAPI Infrastructure as Code
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: Root Terraform configuration

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for state management
  # Uncomment after creating S3 bucket and DynamoDB table manually
  # backend "s3" {
  #   bucket         = "cloudclearing-terraform-state"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "cloudclearing-terraform-locks"
  #   kms_key_id     = "alias/terraform-state"
  # }
}

# ============================================================================
# Provider Configuration
# ============================================================================
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "CloudClearingAPI"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Repository  = "https://github.com/MIFUNEKINSKi/CloudClearingAPI"
    }
  }
}

# ============================================================================
# Data Sources
# ============================================================================
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# ============================================================================
# Local Variables
# ============================================================================
locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  azs            = slice(data.aws_availability_zones.available.names, 0, var.az_count)
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Network Module
# ============================================================================
module "network" {
  source = "./modules/network"
  
  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.azs
  
  enable_nat_gateway   = var.enable_nat_gateway
  enable_vpc_endpoints = var.enable_vpc_endpoints
  enable_flow_logs     = var.enable_flow_logs
  
  common_tags = local.common_tags
}

# ============================================================================
# Security Module
# ============================================================================
module "security" {
  source = "./modules/security"
  
  project_name   = var.project_name
  environment    = var.environment
  aws_region     = var.aws_region
  aws_account_id = local.aws_account_id
  
  s3_bucket_arns      = [
    module.data_lake.raw_bucket_arn,
    module.data_lake.staging_bucket_arn,
    module.data_lake.curated_bucket_arn,
    module.data_lake.logs_bucket_arn
  ]
  ecr_repository_arn = module.compute.ecr_repository_arn
  
  common_tags = local.common_tags
}

# ============================================================================
# Data Lake Module
# ============================================================================
module "data_lake" {
  source = "./modules/data_lake"
  
  project_name   = var.project_name
  environment    = var.environment
  aws_account_id = local.aws_account_id
  kms_key_id     = module.security.kms_key_id
  
  logs_retention_days        = var.logs_retention_days
  enable_event_notifications = false  # Will be enabled in Tier 3
  
  common_tags = local.common_tags
}

# ============================================================================
# Compute Module
# ============================================================================
module "compute" {
  source = "./modules/compute"
  
  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  
  kms_key_arn                 = module.security.kms_key_arn
  ecs_task_execution_role_arn = module.security.ecs_task_execution_role_arn
  ecs_task_role_arn           = module.security.ecs_task_role_arn
  gee_credentials_secret_arn  = module.security.gee_credentials_secret_arn
  api_keys_secret_arn         = module.security.api_keys_secret_arn
  
  earthengine_project = var.earthengine_project
  task_cpu            = var.ecs_task_cpu
  task_memory         = var.ecs_task_memory
  log_level           = var.log_level
  
  common_tags = local.common_tags
  
  depends_on = [module.security, module.network]
}

# ============================================================================
# Monitoring Module
# ============================================================================
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name     = var.project_name
  environment      = var.environment
  aws_region       = var.aws_region
  kms_key_id       = module.security.kms_key_id
  ecs_cluster_name = module.compute.ecs_cluster_name
  
  alarm_email_endpoints = var.alarm_email_endpoints
  enable_cost_alerts    = var.enable_cost_alerts
  monthly_budget_limit  = var.monthly_budget_limit
  enable_dashboard      = var.enable_dashboard
  
  common_tags = local.common_tags
  
  depends_on = [module.compute]
}

# ============================================================================
# Step Functions Module (Orchestration)
# ============================================================================
module "step_functions" {
  source = "./modules/step-functions"
  
  project_name = var.project_name
  environment  = var.environment
  
  # ECS Configuration
  ecs_cluster_arn             = module.compute.ecs_cluster_arn
  ecs_cluster_name            = module.compute.ecs_cluster_name
  monitor_task_definition_arn = module.compute.monitor_task_definition_arn
  ecs_task_role_arn           = module.security.ecs_task_role_arn
  ecs_execution_role_arn      = module.security.ecs_task_execution_role_arn
  private_subnet_ids          = module.network.private_subnet_ids
  ecs_security_group_id       = module.network.ecs_security_group_id
  
  # S3 Configuration
  s3_reports_bucket = module.data_lake.curated_bucket_name
  s3_cache_bucket   = module.data_lake.staging_bucket_name
  
  # Scheduler Configuration
  schedule_expression    = var.step_functions_schedule
  default_regions_count  = var.default_regions_count
  enable_web_scraping    = var.enable_web_scraping
  
  # Notifications
  success_email     = var.pipeline_success_email
  failure_email     = var.pipeline_failure_email
  slack_webhook_url = var.slack_webhook_url
  
  # Security
  kms_key_id = module.security.kms_key_id
  
  # Application
  gee_project_id = var.earthengine_project
  
  # Logging
  log_retention_days = var.logs_retention_days
  
  tags = local.common_tags
  
  depends_on = [module.compute, module.security, module.data_lake, module.network]
}
