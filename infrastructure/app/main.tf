
terraform {
  required_version = ">= 1.11.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket = "seer-terraform-state"
    key    = "seer-infra"
    region = "us-east-2"
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Terraform   = "true"
      Environment = "shared"
      App         = "seer"
    }
  }
}
