#!/bin/sh
set -e

gunicorn \
  --config src/relation_engine_server/utils/gunicorn_conf.py \
  src.relation_engine_server.server:app
