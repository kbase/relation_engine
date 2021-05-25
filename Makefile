.PHONY: test reset

dev-network:
	docker network create kbase-dev || true

test: unit-tests integration-tests

unit-tests: dev-network
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

integration-tests: dev-network start-dev run-integration-tests stop-dev

run-integration-tests:
	cd test/integration && \
	docker-compose run testrunner && \
	docker-compose down

start-dev:
	SPEC_RELEASE_PATH=/opt/spec.tar.gz docker-compose up -d re_api

stop-dev:
	docker-compose down

dev-image:
	docker-compose build

shell: dev-network
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run re_api sh

reset:
	docker-compose --rmi all -v
	docker-compose build
