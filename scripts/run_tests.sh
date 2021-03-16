#!/bin/sh

set -e

# Create tarball of the test spec directory
(cd /app/relation_engine_server/test/spec_release && \
  tar czvf spec.tar.gz sample_spec_release)

# TODO: why reformatting code?
# black .
flake8 --max-complexity 20 /app/relation_engine_server
mypy --ignore-missing-imports /app/relation_engine_server
bandit -r /app/relation_engine_server

# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
coverage erase
# spec validation
python -m spec.validate
# run importer/, relation_engine_server/, and spec/ tests
coverage run --branch -m unittest discover -v
# RE client tests
PYTHONPATH=client_src python -m unittest discover client_src/test
coverage html --omit=*/test_*
