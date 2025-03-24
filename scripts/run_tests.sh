#!/bin/sh

set -e

# Create tarball of the test spec directory
(cd /app/relation_engine_server/test/spec_release && \
  tar czvf spec.tar.gz sample_spec_release)

echo "> black"
black .
echo "> flake8"
flake8 --max-complexity 20 /app
# echo "> mypy"
# mypy --ignore-missing-imports /app
echo "> bandit"
bandit -r -c .bandit.yaml /app

# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &

# spec validation
python -m spec.validate
# wait for the RE service to be up so integration tests can pass
python -m relation_engine_server.utils.wait_for api

# run importer/, relation_engine_server/, spec/, scripts/, and client_src/ tests
pytest -vv --cov=. --cov-branch --cov-report=term --cov-report=xml
