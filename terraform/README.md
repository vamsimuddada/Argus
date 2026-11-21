# ARGUS — Infrastructure as Code (Terraform)

This Terraform module automates the entire AWS cloud infrastructure for **ARGUS**, provisioning the compute, networking, identity, storage, and monitoring components in a single `terraform apply`.

## Architecture Provisioned

- **Compute:** EC2 `t3.micro` instance running Amazon Linux 2023 with automated `user_data` bootstrap (Docker, Nginx, Git).
- **Networking:** Security Group with restricted ingress (SSH, HTTP/80, HTTPS/443) and full egress.
- **Identity & Access Management:** IAM Role & Instance Profile with `AmazonS3FullAccess` and `CloudWatchAgentServerPolicy` (least privilege, zero hardcoded credentials).
- **Storage:** Amazon S3 bucket with all public access blocked.
- **Monitoring:** CloudWatch Metric Alarms for high CPU utilization (>80%) and EC2 status check failures.

## Quickstart

### Prerequisites
- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (>= 1.5.0)
- AWS CLI configured (`aws configure`) or environment credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

### Usage

```bash
cd terraform

# 1. Initialize working directory
terraform init

# 2. Review execution plan
terraform plan

# 3. Apply infrastructure
terraform apply -auto-approve
```

### Outputs

After provisioning completes, Terraform outputs the live endpoints:
- `instance_public_ip`
- `dashboard_url`
- `s3_bucket_name`
- `cloudwatch_cpu_alarm`
