# CloudClearingAPI Data Lake Infrastructure
# Version: 2.9.1 (CCAPI-28.1)
# Purpose: S3 buckets for raw, staging, and curated data with lifecycle policies

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
# S3 Bucket - Raw Data (Landing Zone)
# ============================================================================
resource "aws_s3_bucket" "raw" {
  bucket = "${var.project_name}-${var.environment}-raw-${var.aws_account_id}"
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-raw-data"
      DataTier    = "raw"
      Environment = var.environment
      Description = "Raw satellite imagery, OSM data, web scraping results"
    }
  )
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket = aws_s3_bucket.raw.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  
  rule {
    id     = "transition-to-intelligent-tiering"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
  }
  
  rule {
    id     = "transition-to-glacier"
    status = "Enabled"
    
    filter {
      prefix = "archive/"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
  
  rule {
    id     = "expire-temp-data"
    status = "Enabled"
    
    filter {
      prefix = "temp/"
    }
    
    expiration {
      days = 7
    }
  }
}

# ============================================================================
# S3 Bucket - Staging/Processing (Work Zone)
# ============================================================================
resource "aws_s3_bucket" "staging" {
  bucket = "${var.project_name}-${var.environment}-staging-${var.aws_account_id}"
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-staging-data"
      DataTier    = "staging"
      Environment = var.environment
      Description = "Processed scoring results, intermediate calculations"
    }
  )
}

resource "aws_s3_bucket_versioning" "staging" {
  bucket = aws_s3_bucket.staging.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "staging" {
  bucket = aws_s3_bucket.staging.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "staging" {
  bucket = aws_s3_bucket.staging.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "staging" {
  bucket = aws_s3_bucket.staging.id
  
  rule {
    id     = "transition-to-intelligent-tiering"
    status = "Enabled"
    
    transition {
      days          = 14
      storage_class = "INTELLIGENT_TIERING"
    }
  }
  
  rule {
    id     = "expire-temp-processing"
    status = "Enabled"
    
    filter {
      prefix = "temp/"
    }
    
    expiration {
      days = 3
    }
  }
}

# ============================================================================
# S3 Bucket - Curated/Analytics (Serving Zone)
# ============================================================================
resource "aws_s3_bucket" "curated" {
  bucket = "${var.project_name}-${var.environment}-curated-${var.aws_account_id}"
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-curated-data"
      DataTier    = "curated"
      Environment = var.environment
      Description = "Final PDF reports, JSON analytics, historical trends"
    }
  )
}

resource "aws_s3_bucket_versioning" "curated" {
  bucket = aws_s3_bucket.curated.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "curated" {
  bucket = aws_s3_bucket.curated.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  
  rule {
    id     = "transition-to-intelligent-tiering"
    status = "Enabled"
    
    transition {
      days          = 7
      storage_class = "INTELLIGENT_TIERING"
    }
  }
  
  rule {
    id     = "archive-old-reports"
    status = "Enabled"
    
    filter {
      prefix = "reports/"
    }
    
    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

# ============================================================================
# S3 Bucket - Logs & Audit
# ============================================================================
resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-${var.environment}-logs-${var.aws_account_id}"
  
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-logs"
      DataTier    = "logs"
      Environment = var.environment
      Description = "Access logs, CloudTrail logs, VPC flow logs"
    }
  )
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    
    expiration {
      days = var.logs_retention_days
    }
  }
  
  rule {
    id     = "transition-logs"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Enable logging for raw bucket
resource "aws_s3_bucket_logging" "raw" {
  bucket = aws_s3_bucket.raw.id
  
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/raw/"
}

# Enable logging for staging bucket
resource "aws_s3_bucket_logging" "staging" {
  bucket = aws_s3_bucket.staging.id
  
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/staging/"
}

# Enable logging for curated bucket
resource "aws_s3_bucket_logging" "curated" {
  bucket = aws_s3_bucket.curated.id
  
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3-access-logs/curated/"
}

# ============================================================================
# S3 Bucket Notifications (for event-driven processing)
# ============================================================================
resource "aws_s3_bucket_notification" "raw_events" {
  count  = var.enable_event_notifications ? 1 : 0
  bucket = aws_s3_bucket.raw.id
  
  lambda_function {
    lambda_function_arn = var.raw_data_processor_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "satellite/"
    filter_suffix       = ".tif"
  }
  
  lambda_function {
    lambda_function_arn = var.raw_data_processor_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "osm/"
    filter_suffix       = ".json"
  }
}

# ============================================================================
# S3 Intelligent-Tiering Configuration
# ============================================================================
resource "aws_s3_bucket_intelligent_tiering_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  name   = "entire-bucket"
  
  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }
  
  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "staging" {
  bucket = aws_s3_bucket.staging.id
  name   = "entire-bucket"
  
  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 60
  }
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  name   = "entire-bucket"
  
  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }
  
  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 365
  }
}
