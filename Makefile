.PHONY: test reset

test: api-test spec-test

api-test:
	docker-compose build
	docker-compose run web sh scripts/run_tests.sh
	docker-compose down --remove-orphans

api-shell:
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run web sh

reset:
	docker-compose --rmi all -v
	docker-compose build

spec-test:
	docker-compose build
	docker-compose -f docker-compose-spec.yaml run spec sh scripts/run_spec_tests.sh
	docker-compose down --remove-orphans

spec-shell:
	docker-compose down --remove-orphans
	docker-compose -f docker-compose-spec.yaml build
	docker-compose -f docker-compose-spec.yaml run spec bash
