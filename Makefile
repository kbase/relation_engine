QUERY_TESTING_FILE = spec/test/stored_queries/test_query.py

.PHONY: test reset full_query_testing sampling_query_testing graph_query_testing

test:
	docker-compose build
	docker-compose run re_api sh scripts/run_tests.sh
	docker-compose down --remove-orphans

shell:
	docker-compose down --remove-orphans
	docker-compose build
	docker-compose run re_api sh

reset:
	docker-compose down --rmi all -v

full_query_testing:
	DO_QUERY_TESTING=full time python -m pytest -s $(QUERY_TESTING_FILE)

sampling_query_testing:
	DO_QUERY_TESTING=sampling time python -m pytest -s $(QUERY_TESTING_FILE)

compare_query_testing:
	DO_QUERY_TESTING=compare time python -m pytest -s $(QUERY_TESTING_FILE)

graph_query_testing:
	# invocation example:
	# make graph_query_testing data_new_fp="tmp/blah.json" data_old_fp="tmp/bleh.json"
	# where `data_new_fp` and `data_old_fp` are generated by `make compare_query_testing`
	DO_QUERY_TESTING=graph python $(QUERY_TESTING_FILE) $(data_new_fp) $(data_old_fp)
