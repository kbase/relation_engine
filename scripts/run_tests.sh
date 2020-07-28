#!/bin/sh

set -e

flake8 --max-complexity 10 --ignore=E501 src
mypy --ignore-missing-imports src
bandit -r src
sh /app/scripts/start_server.sh &
python -m src.test.wait_for_api &&
python -m unittest discover src/test/ &&
PYTHONPATH=src/client_src python -m unittest discover src/client_src/test/ &&
PYTHONPATH=src python -m unittest discover src/importers/test
