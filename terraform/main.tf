terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── 1. S3 Bucket for Alert Storage ───────────────────────────────────────────
resource "aws_s3_bucket" "alerts_bucket" {
  bucket        = var.bucket_name
  force_destroy = false

  tags = {
    Project     = "ARGUS"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "alerts_bucket_access" {
  bucket = aws_s3_bucket.alerts_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── 2. IAM Role & Instance Profile for EC2 ───────────────────────────────────
resource "aws_iam_role" "argus_ec2_role" {
  name = "ArgusEC2S3Role-tf"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = "ARGUS"
  }
}

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.argus_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "cloudwatch_access" {
  role       = aws_iam_role.argus_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "argus_instance_profile" {
  name = "ArgusEC2InstanceProfile-tf"
  role = aws_iam_role.argus_ec2_role.name
}

# ── 3. Security Group ────────────────────────────────────────────────────────
resource "aws_security_group" "argus_sg" {
  name        = "argus-security-group-tf"
  description = "Security group for ARGUS web server and alert monitoring"

  # SSH
  ingress {
    description = "SSH from allowed CIDR"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # HTTP
  ingress {
    description = "HTTP access for dashboard"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress - All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project = "ARGUS"
  }
}

# ── 4. AMI Lookup (Amazon Linux 2023) ─────────────────────────────────────────
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── 5. EC2 Instance with Automated User Data Bootstrap ───────────────────────
resource "aws_instance" "argus_server" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = var.instance_type
  key_name             = var.key_name
  iam_instance_profile = aws_iam_instance_profile.argus_instance_profile.name
  vpc_security_group_ids = [aws_security_group.argus_sg.id]

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    delete_on_termination = true
  }

  # Automated user_data bootstrap script
  user_data = <<-EOF
              #!/bin/bash
              dnf update -y
              dnf install -y docker git nginx
              systemctl enable --now docker
              systemctl enable --now nginx
              usermod -aG docker ec2-user

              # Clone application
              cd /home/ec2-user
              git clone https://github.com/vamsimuddada/Argus.git
              chown -R ec2-user:ec2-user Argus

              # Configure Environment
              echo "S3_BUCKET_NAME=${var.bucket_name}" > /home/ec2-user/Argus/.env
              echo "AWS_REGION=${var.aws_region}" >> /home/ec2-user/Argus/.env

              # Build and run container
              cd /home/ec2-user/Argus
              docker build -t argus .
              docker run -d --name argus-app --restart always -p 5000:5000 --env-file .env argus

              # Configure Nginx reverse proxy
              cp nginx.conf /etc/nginx/conf.d/argus.conf
              sed -i 's/listen       80;/listen       8080;/g' /etc/nginx/nginx.conf 2>/dev/null || true
              nginx -t && systemctl reload nginx
              EOF

  tags = {
    Name    = "argus-server"
    Project = "ARGUS"
  }
}

# ── 6. CloudWatch Metric Alarm for CPU Utilization ───────────────────────────
resource "aws_cloudwatch_metric_alarm" "high_cpu_alarm" {
  alarm_name          = "argus-ec2-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggers when ARGUS EC2 instance CPU exceeds 80% for 10 minutes"

  dimensions = {
    InstanceId = aws_instance.argus_server.id
  }

  tags = {
    Project = "ARGUS"
  }
}

# ── 7. CloudWatch Status Check Failed Alarm ──────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "instance_status_check" {
  alarm_name          = "argus-ec2-status-check-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Triggers immediately if EC2 system or instance status check fails"

  dimensions = {
    InstanceId = aws_instance.argus_server.id
  }

  tags = {
    Project = "ARGUS"
  }
}
