#!/bin/sh
set -e
# show the commands we execute
set -o xtrace
export IMAGE_NAME="kbase/relation_engine_api:0.0.4"
sh hooks/build
docker push $IMAGE_NAME
