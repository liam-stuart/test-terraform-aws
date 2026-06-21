data "aws_ecr_repository" "api_repo" {
  name = var.ECR_REPOSITORY_NAME
}