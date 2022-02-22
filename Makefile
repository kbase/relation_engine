QUERY_TESTING_FILE = spec/test/stored_queries/test_query.py

.PHONY: test reset full_query_testing sampling_query_testing

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

full_query_testing:
	DO_QUERY_TESTING=full time python -m pytest -s $(QUERY_TESTING_FILE)

sampling_query_testing:
	DO_QUERY_TESTING=sampling time python -m pytest -s $(QUERY_TESTING_FILE)
