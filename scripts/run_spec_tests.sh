#!/bin/sh
set -e
python -m test.helpers wait_for_api && \
python -m test.validate && \
PYTHONPATH=/app/src python -m unittest discover /app/test/stored_queries
