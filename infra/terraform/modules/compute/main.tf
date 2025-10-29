# CloudClearingAPI Compute Infrastructure
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: ECS Fargate cluster, ECR repository, task definitions

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# ECR Repository
# ============================================================================
resource "aws_ecr_repository" "main" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key_arn
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecr"
      Environment = var.environment
    }
  )
}

resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name
  
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ============================================================================
# ECS Cluster
# ============================================================================
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-cluster"
      Environment = var.environment
    }
  )
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name
  
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
  
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 4
  }
}

# ============================================================================
# CloudWatch Log Group for ECS Tasks
# ============================================================================
resource "aws_cloudwatch_log_group" "ecs_tasks" {
  name              = "/aws/ecs/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-logs"
      Environment = var.environment
    }
  )
}

# ============================================================================
# ECS Task Definition - Weekly Monitoring
# ============================================================================
resource "aws_ecs_task_definition" "weekly_monitoring" {
  family                   = "${var.project_name}-${var.environment}-weekly-monitoring"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn
  
  container_definitions = jsonencode([
    {
      name      = "cloudclearing-monitor"
      image     = "${aws_ecr_repository.main.repository_url}:latest"
      essential = true
      
      environment = [
        {
          name  = "EARTHENGINE_PROJECT"
          value = var.earthengine_project
        },
        {
          name  = "LOG_LEVEL"
          value = var.log_level
        },
        {
          name  = "CACHE_DIR"
          value = "/app/cache"
        },
        {
          name  = "OUTPUT_DIR"
          value = "/app/output"
        }
      ]
      
      secrets = [
        {
          name      = "GOOGLE_APPLICATION_CREDENTIALS"
          valueFrom = var.gee_credentials_secret_arn
        },
        {
          name      = "SMTP_USERNAME"
          valueFrom = "${var.api_keys_secret_arn}:smtp_username::"
        },
        {
          name      = "SMTP_PASSWORD"
          valueFrom = "${var.api_keys_secret_arn}:smtp_password::"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_tasks.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "weekly-monitoring"
        }
      }
      
      mountPoints = []
      volumesFrom = []
      
      healthCheck = {
        command     = ["CMD-SHELL", "python -c 'import earthengine as ee; import src.core.automated_monitor; print(\"OK\")'"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 10
      }
    }
  ])
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-weekly-monitoring-task"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Security Group for ECS Tasks
# ============================================================================
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-${var.environment}-ecs-tasks"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id
  
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-tasks-sg"
      Environment = var.environment
    }
  )
}

# ============================================================================
# ECS Service (Placeholder - for scheduled tasks via Step Functions)
# ============================================================================
# Note: Actual service creation will be managed by Step Functions for scheduled runs
# This is a placeholder for future continuous services (e.g., API endpoint)

# resource "aws_ecs_service" "api" {
#   name            = "${var.project_name}-${var.environment}-api"
#   cluster         = aws_ecs_cluster.main.id
#   task_definition = aws_ecs_task_definition.weekly_monitoring.arn
#   desired_count   = var.enable_continuous_service ? 1 : 0
#   launch_type     = "FARGATE"
#   
#   network_configuration {
#     subnets          = var.private_subnet_ids
#     security_groups  = [aws_security_group.ecs_tasks.id]
#     assign_public_ip = false
#   }
#   
#   tags = merge(
#     var.common_tags,
#     {
#       Name        = "${var.project_name}-api-service"
#       Environment = var.environment
#     }
#   )
# }
