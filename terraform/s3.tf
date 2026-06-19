resource "aws_s3_bucket" "test-bucket" {
  bucket        = var.TEST_BUCKET_NAME
  force_destroy = true
}