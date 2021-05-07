#!/bin/sh

set -e

# Create tarball of the test spec directory
(cd /app/relation_engine_server/test/spec_release && \
  tar czvf spec.tar.gz sample_spec_release)

# Run code quality checks before tests; a failure here
# will prevent the tests from running.
source_dirs="/app/relation_engine_server /app/client_src /app/spec"
flake8 --max-complexity 20 $source_dirs
mypy --ignore-missing-imports $source_dirs
bandit -r $source_dirs

# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
coverage erase

# spec validation
python -m spec.validate

# run importer/, relation_engine_server/, and spec/ tests
coverage run --branch -m unittest discover -v importers relation_engine_server spec

# RE client tests
PYTHONPATH=client_src python -m unittest discover client_src/test
coverage html --omit=*/test_*
