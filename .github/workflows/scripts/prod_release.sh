#! /usr/bin/env bash

export MY_ORG=$(echo "${GITHUB_REPOSITORY}" | awk -F / '{print $1}')
export MY_APP=$(echo "${GITHUB_REPOSITORY}" | awk -F / '{print $2}')
export DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export COMMIT=$(echo "$SHA" | cut -c -7)

echo "ISH is:" $ISH
echo "GITHUB_REF is:" $GITHUB_REF
echo "HEAD_REF is:" $GITHUB_HEAD_REF
echo "BASE_REF is:" $GITHUB_BASE_REF
echo "Release is:" $GITHUB_REF_NAME
echo $DOCKER_TOKEN | docker login ghcr.io -u $DOCKER_ACTOR --password-stdin
docker build --build-arg BUILD_DATE="$DATE" \
             --build-arg COMMIT="$COMMIT" \
             --build-arg BRANCH="$GITHUB_HEAD_REF" \
             --build-arg PULL_REQUEST="$PR" \
             --build-arg VERSION="$VER"  \
             --label us.kbase.vcs-pull-req="$PR" \
             -t ghcr.io/"$MY_ORG"/"$MY_APP":"$VER" \
             -t ghcr.io/"$MY_ORG"/"$MY_APP":"latest" .
docker push ghcr.io/"$MY_ORG"/"$MY_APP":"$VER"
docker push ghcr.io/"$MY_ORG"/"$MY_APP":"latest"
