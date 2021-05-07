.PHONY: test reset

dev-network:
	docker network create kbase-dev || true

test: dev-network
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

start-dev: dev-network
	SPEC_RELEASE_PATH=/opt/spec.tar.gz docker-compose up re_api && docker-compose down && docker-compose rm --force

dev-image:
	docker-compose build

shell: dev-network
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run re_api sh

reset:
	docker-compose --rmi all -v
	docker-compose build
