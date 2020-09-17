#!/bin/sh
set -e
# show the commands we execute
set -o xtrace

# $IMAGE_NAME var is injected into the build so the tag is correct.
if [ -z "$IMAGE_NAME" ]; then
  export IMAGE_NAME="kbase/relation_engine_api:latest"
fi

export BRANCH=`git symbolic-ref --short HEAD`
export DATE=`date -u +"%Y-%m-%dT%H:%M:%SZ"`
export COMMIT=`git rev-parse --short HEAD`
docker build --file Dockerfile \
             --build-arg BUILD_DATE=$DATE \
             --build-arg VCS_REF=$COMMIT \
             --build-arg BRANCH=$BRANCH \
             -t ${IMAGE_NAME} .
docker push $IMAGE_NAME
