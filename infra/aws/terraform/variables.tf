variable "project_name" {
  description = "Project name used in AWS resource names."
  type        = string
  default     = "pqr-lakehouse"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region where resources are created."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets (at least 2)."
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets (at least 2)."
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable a single NAT Gateway (extra cost)."
  type        = bool
  default     = false
}

variable "ecr_repositories" {
  description = "ECR repositories to create."
  type        = list(string)
  default     = ["streamlit", "metabase", "prefect", "dask"]
}

variable "log_retention_days" {
  description = "CloudWatch log retention for app groups."
  type        = number
  default     = 14
}
