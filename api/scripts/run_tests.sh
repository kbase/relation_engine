#!/bin/sh

set -e

flake8 --max-complexity 10 src
mypy --ignore-missing-imports src
bandit -r src
python -m unittest discover src/test/
