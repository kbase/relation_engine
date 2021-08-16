.PHONY: test reset

dev-network:
	docker network create kbase-dev || true

test: unit-tests integration-tests

unit-tests: dev-network
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

integration-tests: dev-network start-dev-server run-integration-tests stop-dev-server

run-integration-tests:
	@cd test/integration && docker-compose run --rm testrunner

run-importer:
	@sh scripts/run-importer.sh

start-dev-server:
	SPEC_RELEASE_PATH=/opt/spec.tar.gz docker-compose up -d re_api

stop-dev-server:
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

interpreter-container:
	cd dev/interpreter && sh build.sh
