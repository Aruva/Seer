# ECR repository for Seer application
resource "aws_ecr_repository" "seer" {
  name                 = "seer-app"
  image_tag_mutability = "MUTABLE"

  tags = {
    Name = "seer-ecr"
  }
}

# ECR lifecycle policy to manage image retention
# Note: We only expire untagged images to avoid accidentally deleting prod/stage/latest
# Old git SHA tagged images should be cleaned up manually using scripts/cleanup-ecr.sh
# Example: ./scripts/cleanup-ecr.sh 180 seer-app
resource "aws_ecr_lifecycle_policy" "seer" {
  repository = aws_ecr_repository.seer.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Delete untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
