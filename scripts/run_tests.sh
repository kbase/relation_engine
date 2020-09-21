#!/bin/sh

set -e

# Create tarball of the test spec directory
(cd /app/relation_engine_server/test/spec_release && \
  tar czvf spec.tar.gz sample_spec_release)

flake8 --max-complexity 15 /app
mypy --ignore-missing-imports /app
bandit -r /app
rm -rf /spec
mkdir /spec
mkdir /spec/repo
cp -r /app/spec/* /spec/repo/
# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
coverage erase
# spec validation
python -m spec.validate &&
# run importer/, relation_engine_server/, and spec/ tests
coverage run --branch -m unittest discover -v &&
# RE client tests
PYTHONPATH=client_src python -m unittest discover client_src/test &&
coverage html --omit=*/test_*
