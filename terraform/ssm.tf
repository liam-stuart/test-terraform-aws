resource "aws_ssm_parameter" "bucket_name" {
  name  = "/s3/bucket-name"
  type  = "String"
  value = aws_s3_bucket.test-bucket.id
}

resource "aws_ssm_parameter" "table_name" {
  name  = "/dynamo/table-name"
  type  = "String"
  value = aws_dynamodb_table.test-table.id
}