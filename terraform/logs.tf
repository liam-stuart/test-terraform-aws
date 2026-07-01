resource "aws_cloudwatch_log_group" "post_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.post_data_lambda.function_name}"
}

resource "aws_cloudwatch_log_group" "process_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.process_lambda.function_name}"
}

resource "aws_cloudwatch_log_group" "retrieve_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.retrieve_data_lambda.function_name}"
}

resource "aws_cloudwatch_log_group" "update_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.update_data_lambda.function_name}"
}

resource "aws_cloudwatch_log_group" "delete_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.delete_data_lambda.function_name}"
}

resource "aws_cloudwatch_log_group" "authorise_lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.authorise_lambda.function_name}"
}
