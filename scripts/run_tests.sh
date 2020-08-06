#!/bin/sh

set -e

flake8 --max-complexity 15 /app
mypy --ignore-missing-imports /app
bandit -r /app
mkdir /spec
mkdir /spec/repo
cp -r /app/spec/* /spec/repo/
# start server, using the specs in /spec/repo
sh /app/scripts/start_server.sh &
# spec validation
python -m spec.validate &&
# spec stored query tests
python -m unittest discover spec/test &&
# importer tests
python -m unittest discover importers/test &&
# RE API tests
python -m unittest discover relation_engine_server/test &&
# RE client tests
PYTHONPATH=client_src python -m unittest discover client_src/test
