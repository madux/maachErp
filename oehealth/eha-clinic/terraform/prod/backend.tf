terraform {
  backend "s3" {
    bucket = "eha-prod-state-files"
    key = "eha-clinic-v12-prod/terraform.tfstate"
    region = "eu-west-1"
    dynamodb_table = "eha-clinic-v12-prod-terraform-lock"
  }
}
