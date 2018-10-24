test:
	echo "TODO run all python tests in ./src/test against the test server"

test-server:
	echo "TODO run a single-node arango database server with pre-loaded test data"

build-dist:
	python setup.py sdist

publish:
	anaconda upload -i -u kbase dist/*.tar.gz
