#!/bin/sh

set -e

flake8 src
mypy --ignore-missing-imports src
python -m pyflakes src
bandit -r src
python -m unittest discover src/test/
