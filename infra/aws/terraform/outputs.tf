output "vpc_id" {
  description = "VPC id for the environment."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet ids."
  value       = [for s in aws_subnet.public : s.id]
}

output "private_subnet_ids" {
  description = "Private subnet ids."
  value       = [for s in aws_subnet.private : s.id]
}

output "s3_raw_bucket" {
  description = "Raw layer S3 bucket name."
  value       = aws_s3_bucket.raw.bucket
}

output "s3_refined_bucket" {
  description = "Refined layer S3 bucket name."
  value       = aws_s3_bucket.refined.bucket
}

output "ecs_cluster_name" {
  description = "ECS cluster for workloads."
  value       = aws_ecs_cluster.this.name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs by app name."
  value       = { for k, repo in aws_ecr_repository.app : k => repo.repository_url }
}

output "secrets_arns" {
  description = "Secrets Manager ARNs created for the environment."
  value       = { for k, s in aws_secretsmanager_secret.app : k => s.arn }
}
