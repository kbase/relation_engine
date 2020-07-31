#!/bin/sh
set -e

# Set the number of gevent workers to number of cores * 2 + 1
# See: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
calc_workers="$(($(nproc) * 2 + 1))"
# Use the WORKERS environment variable, if present
workers=${WORKERS:-$calc_workers}

python -m relation_engine_server.wait_for_services
python -m relation_engine_server.utils.pull_spec

gunicorn \
  --worker-class gevent \
  --timeout 1800 \
  --workers $workers \
  --bind :5000 \
  ${DEVELOPMENT:+"--reload"} \
  relation_engine_server.main:app
