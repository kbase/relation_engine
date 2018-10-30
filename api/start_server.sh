#!/bin/sh

# Set the number of gevent workers to number of cores * 2 + 1
# See: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
calc_workers="$(($(nproc) * 2 + 1))"
workers=${WORKERS:-$calc_workers}

gunicorn --worker-class gevent --timeout 1800 --workers $workers -b :5000 --reload src.relation_engine_server.app:app
