.PHONY: test reset

test:
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

start-ui-dev:
	cd local-ui-dev && docker-compose up re_api && docker-compose down && docker-compose rm --force
	
shell:
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run re_api sh

reset:
	docker-compose --rmi all -v
	docker-compose build
