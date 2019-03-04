.PHONY: test

test:
	python test/validate.py
	echo "Running view tests"
	docker-compose run spec python /app/test/views/init_spec.py
	docker-compose run spec python -m unittest discover /app/test/views
