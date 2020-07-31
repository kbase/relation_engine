.PHONY: test reset

test:
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

shell:
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run re_api sh

reset:
	docker-compose --rmi all -v
	docker-compose build
