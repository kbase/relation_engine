#!/usr/bin/env bash
#
# import.sh
# Runs the given importer within a Docker container.
#

# Turn on command echoing if VERBOSE is set
if [ -n "${VERBOSE}" ]
then
  set -x
fi

#
# Required environment variables
#
if [ -z "${IMPORTER}" ]
then
    echo "Error: required environment variable IMPORTER not found"
    exit 1
fi

if [ -z "${RE_API_URL}" ]
then
    echo "Error: required environment variable RE_API_URL not found"
    exit 1
fi

if [ -z "${AUTH_TOKEN}" ]
then
    echo "Error: required environment variable AUTH_TOKEN not found"
    exit 1
fi


# Build up args based on environment variables
export IMPORT_PATH="importers.${IMPORTER}.importer"
export ARGS="--re-api-url $RE_API_URL --auth-token $AUTH_TOKEN ${DATA_DIR:+--data-dir $DATA_DIR} ${DRY_RUN:+--dry-run} ${QUIET:+--quiet}"

# E.g. IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer

# Run the importer
python -m $IMPORT_PATH $ARGS
