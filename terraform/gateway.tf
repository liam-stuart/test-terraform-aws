resource "aws_api_gateway_rest_api" "my_api" {
  name = "my-terraform-api"
  body = templatefile("../src/docs/swagger.yaml", {
    post_data_invoke_arn     = aws_lambda_function.post_data_lambda.invoke_arn
    retrieve_data_invoke_arn = aws_lambda_function.retrieve_data_lambda.invoke_arn
    update_data_invoke_arn   = aws_lambda_function.update_data_lambda.invoke_arn
    delete_data_invoke_arn   = aws_lambda_function.delete_data_lambda.invoke_arn
    authorise_invoke_arn     = aws_lambda_function.authorise_lambda.invoke_arn
  })
}

resource "aws_api_gateway_deployment" "my_api_deploy" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.my_api.body))
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "my_api_stage" {
  deployment_id = aws_api_gateway_deployment.my_api_deploy.id
  rest_api_id   = aws_api_gateway_rest_api.my_api.id
  stage_name    = "staging"
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  stage_name  = aws_api_gateway_stage.my_api_stage.stage_name
  method_path = "*/*"
  settings {
    logging_level      = "INFO"
    data_trace_enabled = true
    metrics_enabled    = true
  }
  depends_on = [aws_api_gateway_account.global_settings]
}
resource "aws_lambda_permission" "api_gw_invoke_post" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_data_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*/*/*"
}

resource "aws_lambda_permission" "api_gw_invoke_retrieve" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.retrieve_data_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*/*/*"
}

resource "aws_lambda_permission" "api_gw_invoke_update" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.update_data_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*/*/*"
}

resource "aws_lambda_permission" "api_gw_invoke_delete" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_data_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*/*/*"
}

resource "aws_lambda_permission" "api_gw_invoke_authorise" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorise_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*"
}