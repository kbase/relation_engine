#!/bin/sh

set -e

flake8 --max-complexity 10 src
mypy --ignore-missing-imports src
bandit -r src
sh scripts/start_server.sh &
python -m src.test.wait_for_api &&
python -m unittest discover src/test/ &&
PYTHONPATH=client_src python -m unittest discover client_src/test/
