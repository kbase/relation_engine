#!/bin/sh
set -e
# show the commands we execute
set -o xtrace
export IMAGE_NAME="kbase/relation_engine_api:local_build"
sh hooks/build
docker push $IMAGE_NAME
