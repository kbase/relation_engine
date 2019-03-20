#!/bin/sh

set -e

flake8 --max-complexity 5 src
mypy --ignore-missing-imports src
python -m pyflakes src
bandit -r src
python -m unittest discover src/test/
