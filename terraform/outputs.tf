output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.argus_server.id
}

output "instance_public_ip" {
  description = "Public IPv4 address of the ARGUS server"
  value       = aws_instance.argus_server.public_ip
}

output "dashboard_url" {
  description = "Direct URL to access the ARGUS web dashboard"
  value       = "http://${aws_instance.argus_server.public_ip}/"
}

output "s3_bucket_name" {
  description = "Name of the S3 alert storage bucket"
  value       = aws_s3_bucket.alerts_bucket.bucket
}

output "cloudwatch_cpu_alarm" {
  description = "CloudWatch alarm for high CPU utilization"
  value       = aws_cloudwatch_metric_alarm.high_cpu_alarm.alarm_name
}

output "cloudwatch_status_alarm" {
  description = "CloudWatch alarm for instance status checks"
  value       = aws_cloudwatch_metric_alarm.instance_status_check.alarm_name
}
