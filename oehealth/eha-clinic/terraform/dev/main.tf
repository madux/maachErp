module "rds" {
  source             = "git@github.com:eHealthAfrica/terraform.git//rds"
  environment        = "${var.environment}"
  project            = "${var.project}"
  cluster_name       = "${var.cluster_name}"
  project_billing_id = "${var.project_billing_id}"
  db_engine_version  = "${var.db_engine_version}"
}

module "odoo" {
  source             = "git@github.com:eHealthAfrica/terraform.git//generic_ecs_service"
  environment        = "${var.environment}"
  project            = "${var.project}"
  database_hostname  = "${module.rds.database_hostname}"
  domain             = "${var.domain}"
  application_memory = 1024
  memory_reservation = 512
  app                = "${var.app}"
  data_dir           = "/var/lib/odoo"
  url                = "dev"
  alb_idle_timeout   = 720
  http_rule_priority = 501
  project_billing_id = "${var.project_billing_id}"
  requested_by       = "Victor Okorobodo"
  github_repo        = "https://github.com/eHealthAfrica/eha-clinic"
}

