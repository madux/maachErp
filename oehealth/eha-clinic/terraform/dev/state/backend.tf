module "backend" {
  source      = "git@github.com:eHealthAfrica/terraform//backend"
  project     = "${var.project}"
  environment = "${var.environment}"
}
