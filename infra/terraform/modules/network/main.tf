# CloudClearingAPI Network Infrastructure
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: VPC, subnets, routing, NAT, VPC endpoints

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
# VPC
# ============================================================================
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-vpc"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Internet Gateway
# ============================================================================
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-igw"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Public Subnets (for NAT Gateway, Load Balancers)
# ============================================================================
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-public-${var.availability_zones[count.index]}"
      Type        = "public"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Private Subnets (for ECS tasks, Lambda, EMR)
# ============================================================================
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-private-${var.availability_zones[count.index]}"
      Type        = "private"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Elastic IPs for NAT Gateways
# ============================================================================
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? length(var.availability_zones) : 0
  domain = "vpc"
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-nat-eip-${var.availability_zones[count.index]}"
      Environment = var.environment
    }
  )
  
  depends_on = [aws_internet_gateway.main]
}

# ============================================================================
# NAT Gateways (for private subnet internet access)
# ============================================================================
resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? length(var.availability_zones) : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-nat-${var.availability_zones[count.index]}"
      Environment = var.environment
    }
  )
  
  depends_on = [aws_internet_gateway.main]
}

# ============================================================================
# Route Tables - Public
# ============================================================================
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-public-rt"
      Type        = "public"
      Environment = var.environment
    }
  )
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ============================================================================
# Route Tables - Private
# ============================================================================
resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-private-rt-${var.availability_zones[count.index]}"
      Type        = "private"
      Environment = var.environment
    }
  )
}

resource "aws_route" "private_nat" {
  count                  = var.enable_nat_gateway ? length(var.availability_zones) : 0
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ============================================================================
# VPC Endpoints (for private access to AWS services)
# ============================================================================

# S3 Gateway Endpoint (free, for data lake access)
resource "aws_vpc_endpoint" "s3" {
  count        = var.enable_vpc_endpoints ? 1 : 0
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  
  route_table_ids = concat(
    [aws_route_table.public.id],
    aws_route_table.private[*].id
  )
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-s3-endpoint"
      Environment = var.environment
    }
  )
}

# ECR API Endpoint (for pulling Docker images)
resource "aws_vpc_endpoint" "ecr_api" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecr-api-endpoint"
      Environment = var.environment
    }
  )
}

# ECR DKR Endpoint (for Docker registry)
resource "aws_vpc_endpoint" "ecr_dkr" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-ecr-dkr-endpoint"
      Environment = var.environment
    }
  )
}

# Secrets Manager Endpoint (for secure credential access)
resource "aws_vpc_endpoint" "secretsmanager" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-secretsmanager-endpoint"
      Environment = var.environment
    }
  )
}

# CloudWatch Logs Endpoint (for logging)
resource "aws_vpc_endpoint" "logs" {
  count               = var.enable_vpc_endpoints ? 1 : 0
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-logs-endpoint"
      Environment = var.environment
    }
  )
}

# ============================================================================
# Security Group for VPC Endpoints
# ============================================================================
resource "aws_security_group" "vpc_endpoints" {
  count       = var.enable_vpc_endpoints ? 1 : 0
  name        = "${var.project_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-vpc-endpoints-sg"
      Environment = var.environment
    }
  )
}

# ============================================================================
# VPC Flow Logs (for network monitoring)
# ============================================================================
resource "aws_flow_log" "main" {
  count                = var.enable_flow_logs ? 1 : 0
  iam_role_arn         = aws_iam_role.flow_logs[0].arn
  log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  max_aggregation_interval = 60
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-vpc-flow-logs"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/${var.project_name}-flow-logs"
  retention_in_days = var.flow_logs_retention_days
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-vpc-flow-logs"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.project_name}-vpc-flow-logs-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-vpc-flow-logs-role"
      Environment = var.environment
    }
  )
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.project_name}-vpc-flow-logs-policy"
  role  = aws_iam_role.flow_logs[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
