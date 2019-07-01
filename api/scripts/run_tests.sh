#!/bin/sh

set -e

flake8 --max-complexity 10 src
mypy --ignore-missing-imports src
bandit -r src
sh scripts/start_server.sh &
python -m src.relation_engine_server.wait_for_services
python -m unittest discover src/test/
