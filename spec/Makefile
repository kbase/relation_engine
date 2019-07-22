.PHONY: test

test:
	echo "Validating files.."
	docker-compose run spec python test/validate.py
	echo "Running tests.."
	docker-compose run spec sh -c "python /app/test/views/init_spec.py && python -m unittest discover /app/test/views"
