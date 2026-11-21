variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-2"
}

variable "environment" {
  description = "Environment name (e.g. dev, prod)"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type (Free Tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of existing EC2 Key Pair for SSH"
  type        = string
  default     = "argus-key"
}

variable "bucket_name" {
  description = "Unique S3 bucket name for alert logs"
  type        = string
  default     = "argus-alerts-vamsi-2026"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"
}
