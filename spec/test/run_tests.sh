#!/bin/sh
set -e
python -m test.validate
python /app/test/views/init_spec.py
python -m unittest discover /app/test/views
