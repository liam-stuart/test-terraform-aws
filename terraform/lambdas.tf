resource "aws_lambda_function" "post_data_lambda" {
  function_name = "post_data_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["endpoints.post_data.lambda_handler"]
  }
}

resource "aws_lambda_function" "process_lambda" {
  function_name = "process_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["processing.process.lambda_handler"]
  }
}

resource "aws_lambda_function" "retrieve_data_lambda" {
  function_name = "retrieve_data_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["endpoints.retrieve_data.lambda_handler"]
  }
}

resource "aws_lambda_function" "update_data_lambda" {
  function_name = "update_data_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["endpoints.update_data.lambda_handler"]
  }
}

resource "aws_lambda_function" "delete_data_lambda" {
  function_name = "delete_data_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["endpoints.delete_data.lambda_handler"]
  }
}

resource "aws_lambda_function" "authorise_lambda" {
  function_name = "authorise_lambda"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 30
  image_config {
    command = ["base.authorise.lambda_handler"]
  }
  environment {
    variables = {
      "AUTH0_DOMAIN" = var.AUTH0_DOMAIN
      "API_AUDIENCE" = var.API_AUDIENCE
    }
  }
}

resource "aws_lambda_event_source_mapping" "process_lambda_event" {
  event_source_arn  = aws_dynamodb_table.test-table.stream_arn
  function_name     = aws_lambda_function.process_lambda.function_name
  starting_position = "LATEST"
  depends_on = [
    aws_iam_role_policy_attachment.lambda_attach
  ]
  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT", "MODIFY"],
        dynamodb = {
          NewImage = {
            status = {
              S = ["processing"]
            }
          }
        }
      })
    }
  }
}