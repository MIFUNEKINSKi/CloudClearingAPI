# CloudClearingAPI Security Infrastructure
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: IAM roles, KMS keys, Secrets Manager, least-privilege policies

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
# KMS Key for Data Encryption
# ============================================================================
resource "aws_kms_key" "main" {
  description             = "${var.project_name} data encryption key"
  deletion_window_in_days = var.kms_deletion_window_days
  enable_key_rotation     = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-kms-key"
      Environment = var.environment
    }
  )
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-${var.environment}"
  target_key_id = aws_kms_key.main.key_id
}

# ============================================================================
# Secrets Manager - Google Earth Engine Credentials
# ============================================================================
resource "aws_secretsmanager_secret" "gee_credentials" {
  name                    = "${var.project_name}/${var.environment}/gee-credentials"
  description             = "Google Earth Engine service account credentials"
  kms_key_id              = aws_kms_key.main.id
  recovery_window_in_days = var.secret_recovery_window_days
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-gee-credentials"
      Environment = var.environment
    }
  )
}

# Placeholder version (real credentials should be added manually or via CI/CD)
resource "aws_secretsmanager_secret_version" "gee_credentials" {
  secret_id = aws_secretsmanager_secret.gee_credentials.id
  secret_string = jsonencode({
    project_id = "your-gee-project-id"
    # Actual service account JSON should be added after Terraform apply
    placeholder = "Add GEE service account JSON via AWS Console or CLI"
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ============================================================================
# Secrets Manager - Web Scraping API Keys
# ============================================================================
resource "aws_secretsmanager_secret" "api_keys" {
  name                    = "${var.project_name}/${var.environment}/api-keys"
  description             = "API keys for web scraping and external services"
  kms_key_id              = aws_kms_key.main.id
  recovery_window_in_days = var.secret_recovery_window_days
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-api-keys"
      Environment = var.environment
    }
  )
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    smtp_username = ""
    smtp_password = ""
    webhook_url   = ""
    slack_token   = ""
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ============================================================================
# IAM Role - ECS Task Execution (for Fargate)
# ============================================================================
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-${var.environment}-ecs-task-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-task-execution-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for Secrets Manager access
resource "aws_iam_role_policy" "ecs_secrets_access" {
  name = "${var.project_name}-ecs-secrets-access"
  role = aws_iam_role.ecs_task_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.gee_credentials.arn,
          aws_secretsmanager_secret.api_keys.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

# ============================================================================
# IAM Role - ECS Task (application permissions)
# ============================================================================
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecs-task-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy" "ecs_task_s3_access" {
  name = "${var.project_name}-ecs-s3-access"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = concat(
          var.s3_bucket_arns,
          [for arn in var.s3_bucket_arns : "${arn}/*"]
        )
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_cloudwatch_logs" {
  name = "${var.project_name}-ecs-cloudwatch-logs"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/ecs/${var.project_name}*"
    }]
  })
}

# ============================================================================
# IAM Role - Lambda Functions (for event-driven processing)
# ============================================================================
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-${var.environment}-lambda-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-lambda-execution-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = concat(
          var.s3_bucket_arns,
          [for arn in var.s3_bucket_arns : "${arn}/*"]
        )
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

# ============================================================================
# IAM Role - Step Functions (for orchestration)
# ============================================================================
resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-${var.environment}-step-functions"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-step-functions-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy" "step_functions_execution" {
  name = "${var.project_name}-step-functions-execution"
  role = aws_iam_role.step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ecs:cluster" = "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:cluster/${var.project_name}-*"
          }
        }
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = "arn:aws:events:${var.aws_region}:${var.aws_account_id}:rule/StepFunctions*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy - Least Privilege for CI/CD
# ============================================================================
resource "aws_iam_policy" "cicd_ecr_push" {
  name        = "${var.project_name}-${var.environment}-cicd-ecr-push"
  description = "Allow CI/CD to push Docker images to ECR"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = var.ecr_repository_arn
      }
    ]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-cicd-ecr-push-policy"
      Environment = var.environment
    }
  )
}
