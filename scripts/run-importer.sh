#!/usr/bin/env bash
#
# run-importer.sh
#
#

# Turn on command echoing if VERBOSE is set
if [ -n "${VERBOSE}" ]
then
  set -x
fi

if [ -z "${DATA_DIR}" ]
then
    echo "Error: required environment variable DATA_DIR not found"
    exit 1
fi

# In development mode, map the current directory (assuming run from repo root) to
# the top level /app directory in the container
MAP_APP=
if [ -n "${DEVELOPMENT}" ]
then
    MAP_APP="-v $(pwd):/app"
fi

cd importers && docker-compose run -v "${DATA_DIR}":/data ${MAP_APP} --rm importer