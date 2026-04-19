#!/usr/bin/env bash
set -e

COMMIT="${TRAVIS_COMMIT}"
BRANCH="${TRAVIS_BRANCH}"
export AWS_DEFAULT_REGION="eu-west-1"
IMAGE_REPO="387526361725.dkr.ecr.eu-west-1.amazonaws.com"
APP="odoo"
NGINX="odoo_nginx"

PROJECTS=( eha-clinic-v12 )

# clone modules
./core-app/scripts/clone.sh

case "$BRANCH" in
  develop)
    export ENV="dev"
    export CLUSTER_NAME="ehealth-africa"
    ;;
  stage)
    export ENV="staging"
    export CLUSTER_NAME="ehealth-africa"
    ;;
  master)
    echo "commit on master, setting ENV to production"
    export ENV="prod"
    export CLUSTER_NAME="ehealth-africa"
    ;;
  *)
    echo "Branch not found"
    exit 1
esac

$(aws ecr get-login --region="${AWS_DEFAULT_REGION}" --no-include-email)

cp core-app/.env.tmpl core-app/.env

# build Docker image
echo "Building Docker image"
docker-compose build

# for PROJECT in "${PROJECTS[@]}"
# do
#   # tag Docker image
#   echo "Tagging Docker image"
#   docker tag $APP "${IMAGE_REPO}/${PROJECT}-${APP}-${ENV}:latest"
#   docker tag $NGINX "${IMAGE_REPO}/${PROJECT}-${APP}-nginx-${ENV}:latest"

#   # push Docker image
#   docker push "${IMAGE_REPO}/${PROJECT}-${APP}-${ENV}:latest"
#   docker push "${IMAGE_REPO}/${PROJECT}-${APP}-nginx-${ENV}:latest"

#     # deploy Docker image
#   ecs deploy --timeout 600 ${CLUSTER_NAME}-${ENV} ${PROJECT}-${APP} -i ${APP} "${IMAGE_REPO}/${PROJECT}-${APP}-${ENV}:latest"
# done
