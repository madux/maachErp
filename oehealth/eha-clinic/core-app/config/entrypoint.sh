#!/bin/bash

set -ex

get_secrets() {
  aws s3 cp --sse AES256 s3://ecs-secrets-$ENV/$PROJECT - >> ~/.bashrc
}

generate_config() {
  envsubst < /etc/odoo/odoo.conf.tpl > /etc/odoo/odoo.conf
}

case "$1" in
  bash )
    bash
  ;;

  start )
    source ~/.bashrc
    generate_config
    #/entrypoint.sh odoo
    supervisord -n
  ;;
esac
