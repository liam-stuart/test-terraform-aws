resource "aws_dynamodb_table" "test-table" {
  name         = var.TEST_TABLE_NAME
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "uuid"
  attribute {
    name = "uuid"
    type = "S"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
}