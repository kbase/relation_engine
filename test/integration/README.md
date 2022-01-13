# Integration Tests

## Quick Start

Integration tests may be run with:

```sh
make integration-tests
```

The only dependency is `Docker` ( and `make`.)

Integration tests are also run with

```sh
make test
```

which runs unit tests and code quality checks.

## Status

At present, integration tests only support the `data_sources` importer.

## How it works

1. The Relation Engine API server and support services (arango, mock workspace and user profile) are started with `docker compose`. These are defined in the top level `docker-compose.yml` file.

2. Then the script `test/integration/scripts/run-integration-scripts.sh` is run.

   This script first waits for the RE API server to become ready. The RE API startup process will initialize the database collections, which may take a few seconds.

3. When the RE API is ready, any integration tests located in `test/integration/tests` are run. The tests are run in an isolated test container.

4. When the tests complete, the RE API and related services are shut down.

## Locations of files

- `Docker.testrunner`- the definition of the image which runs integration tests

- `Makefile` - defines the tasks
 
  - `make run-integration-tests` - just runs the integration test container
  - `make integration-tests` - runs full integration test cycle - starting services, running integration tests
  - `make test` - runs unit and integration tests.

- `test/integration` - all other integration test files, including:

  - `data` - integration test data
  - `scripts` - support scripts (just `run-integration-tests.sh` at present)
  - `tests` - all test files go in here
  - `utils` - other non-test python code used to support integration tests.
  - `requirements.txt` - python dependencies for running integration tests and utilities

