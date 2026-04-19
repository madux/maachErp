#!/bin/bash

set -ex

BUILD_DIR="core-app/build"

if [ -d $BUILD_DIR ]; then
  echo "Build directory exists skipping..."
else
  echo "Creating build directory...."
  mkdir -p $BUILD_DIR
fi

if [ "$TRAVIS_BRANCH" == "master" ]; then
  rm -rf $BUILD_DIR/*
  git config --global github.token $GITHUB_TOKEN
  git clone -b master --depth 1 git@github.com:eHealthAfrica/eha-clinic.git $BUILD_DIR/eha_clinic
  git clone -b 12.0 https://${GITHUB_TOKEN}@github.com/odoo/enterprise.git $BUILD_DIR/enterprise
elif [ "$TRAVIS_BRANCH" == "develop" ]; then
  rm -rf $BUILD_DIR/*
  git config --global github.token $GITHUB_TOKEN
  git clone -b develop --depth 1 git@github.com:eHealthAfrica/eha-clinic.git $BUILD_DIR/eha_clinic
  git clone -b 12.0 https://${GITHUB_TOKEN}@github.com/odoo/enterprise.git $BUILD_DIR/enterprise
fi
