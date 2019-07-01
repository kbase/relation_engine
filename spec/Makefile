.PHONY: test

test:
	python test/validate.py
	echo "Running view tests"
	docker-compose run spec sh -c "python /app/test/views/init_spec.py && python -m unittest discover /app/test/views"
