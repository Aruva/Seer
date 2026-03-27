# Data sources for database secrets created by the db module
data "aws_secretsmanager_secret" "stage_db_password" {
  name = "seer/stage/db-details"
}

data "aws_secretsmanager_secret" "prod_db_password" {
  name = "seer/prod/db-details"
}
