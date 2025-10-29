# CloudClearingAPI Data Lake Module - Outputs
# Version: 2.9.1 (CCAPI-28.1)

output "raw_bucket_id" {
  description = "ID of raw data bucket"
  value       = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  description = "ARN of raw data bucket"
  value       = aws_s3_bucket.raw.arn
}

output "staging_bucket_id" {
  description = "ID of staging data bucket"
  value       = aws_s3_bucket.staging.id
}

output "staging_bucket_arn" {
  description = "ARN of staging data bucket"
  value       = aws_s3_bucket.staging.arn
}

output "curated_bucket_id" {
  description = "ID of curated data bucket"
  value       = aws_s3_bucket.curated.id
}

output "curated_bucket_arn" {
  description = "ARN of curated data bucket"
  value       = aws_s3_bucket.curated.arn
}

output "logs_bucket_id" {
  description = "ID of logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN of logs bucket"
  value       = aws_s3_bucket.logs.arn
}
