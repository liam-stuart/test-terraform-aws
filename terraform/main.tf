terraform {
  backend "s3" {
    key          = "statefile.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {}