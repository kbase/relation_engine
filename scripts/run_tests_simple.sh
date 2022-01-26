#!/bin/sh

set -e

# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
python -m pytest -s relation_engine_server/test/test_pull_spec.py
#python -m pytest -s spec/test/test_ensure_specs.py
#python -m pytest -s spec/test/stored_queries/test_fulltext_search.py
