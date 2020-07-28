.PHONY: test reset

test:
	docker-compose down
	docker-compose build
	docker-compose run web sh scripts/run_tests.sh
	docker-compose down

api-shell:
	docker-compose down
	docker-compose build
	docker-compose run web sh

reset:
	docker-compose --rmi all -v
	docker-compose build

spec-test:
	docker-compose build
	docker-compose -f docker-compose-spec.yaml run spec sh /app/test/run_tests.sh
	docker-compose down

spec-shell:
	docker-compose down
	docker-compose -f docker-compose-spec.yaml build
	docker-compose -f docker-compose-spec.yaml run spec bash
