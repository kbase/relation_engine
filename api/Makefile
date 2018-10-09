.PHONY: dev-server dev-build test test-local

dev-server:
	DEVELOPMENT=1 docker-compose up

dev-build:
	docker-compose down
	docker-compose build --build-arg DEVELOPMENT=1 --no-cache web

test:
	docker-compose run web make test-local

test-local:
	flake8 --max-complexity 5 src
	mypy --ignore-missing-imports src
	python -m pyflakes src
	bandit -r src
	python -m unittest discover src/test/
