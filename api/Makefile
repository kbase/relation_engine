.PHONY: test reset

test:
	docker-compose run web sh scripts/run_tests.sh

reset:
	docker-compose down
	docker-compose rm -vf
	docker-compose build --no-cache
	docker-compose up
