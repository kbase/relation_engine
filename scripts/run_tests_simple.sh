#!/bin/sh

set -e

# Create tarball of the test spec directory
(cd /app/relation_engine_server/test/spec_release && \
  tar czvf spec.tar.gz sample_spec_release)

# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
python -m pytest -s relation_engine_server/test/test_api_v1.py
#python -m pytest -s spec/test/test_ensure_specs.py
#python -m pytest -s spec/test/stored_queries/test_fulltext_search.py
