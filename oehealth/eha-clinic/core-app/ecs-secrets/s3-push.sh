#!/usr/bin/env bash

# eha-clinic

aws s3 cp dev/eha-clinic s3://ecs-secrets-dev/eha-clinic --sse aws:kms --sse-kms-key-id arn:aws:kms:eu-west-1:387526361725:alias/eha-dev
aws s3 cp staging/eha-clinic s3://ecs-secrets-staging/eha-clinic --sse aws:kms --sse-kms-key-id arn:aws:kms:eu-west-1:387526361725:alias/eha-staging
aws s3 cp prod/eha-clinic s3://ecs-secrets-prod/eha-clinic --sse aws:kms --sse-kms-key-id arn:aws:kms:eu-west-1:387526361725:alias/eha-prod