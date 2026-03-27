# Security Groups for Seer Infrastructure

# ALB Security Group - Internet facing
resource "aws_security_group" "alb" {
  name        = "seer-alb-sg"
  description = "Security group for Seer ALB"
  vpc_id      = module.vpc.vpc_id

  # Allow HTTP from internet
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTPS from internet
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "seer-alb-sg"
  }
}

# ECS Tasks Security Group - Application tier
resource "aws_security_group" "ecs_tasks" {
  name        = "seer-ecs-tasks-sg"
  description = "Security group for Seer ECS tasks"
  vpc_id      = module.vpc.vpc_id

  # Allow HTTP from ALB
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow all outbound traffic (for internet access, database, cache, etc.)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "seer-ecs-tasks-sg"
  }
}

# ElastiCache Security Group - Cache tier
resource "aws_security_group" "elasticache" {
  name        = "seer-elasticache-sg"
  description = "Security group for Seer ElastiCache Valkey"
  vpc_id      = module.vpc.vpc_id

  # Allow Valkey from ECS tasks
  ingress {
    description     = "Valkey from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # Allow minimal outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "seer-elasticache-sg"
  }
}
