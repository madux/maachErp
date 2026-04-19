terraform {
  backend "s3" {
	bucket = "eha-dev-state-files"
	key = "eha-clinic-v12-dev/terraform.tfstate"
	region = "eu-west-1"
	dynamodb_table = "eha-clinic-v12-dev-terraform-lock"
  }
}
