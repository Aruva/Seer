# CloudWatch log groups
resource "aws_cloudwatch_log_group" "seer_prod" {
  name              = "/ecs/seer-prod"
  retention_in_days = 5

  tags = {
    Name        = "seer-prod-logs"
    Environment = "prod"
  }
}

resource "aws_cloudwatch_log_group" "seer_stage" {
  name              = "/ecs/seer-stage"
  retention_in_days = 1

  tags = {
    Name        = "seer-stage-logs"
    Environment = "stage"
  }
}
