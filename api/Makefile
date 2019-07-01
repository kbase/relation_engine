.PHONY: test reset

test:
	docker-compose down
	docker-compose run web sh scripts/run_tests.sh
	docker-compose down

reset:
	docker-compose --rmi all -v
	docker-compose build
