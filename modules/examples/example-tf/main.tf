# Provider Configuration
provider "aws" {
  region = var.aws_region
}

terraform {
  required_version = ">= 0.13"
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.38"
    }
  }
}

# App specific module(s)
resource "random_id" "RANDOM_ID" {
  byte_length = "2"
}


module "s3_sample" {
  source        = "./modules/s3"
  bucket_name = "example-tf-${var.aws_region}-${random_id.RANDOM_ID.hex}"
}