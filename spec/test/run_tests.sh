#!/bin/sh
set -e
python -m test.helpers wait_for_api
python -m test.validate
python -m unittest discover /app/test/stored_queries
