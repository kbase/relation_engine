# Integration Tests

## Quick Start

Integration tests may be run with:

```sh
make integration-tests
```

The only dependency is Docker.

Integration tests are also run with

```sh
make test
```

## Status

At present, integration tests only support the `data_sources` importer.

## How it works

First the RE_API and support services (arango, mock workspace and user profile) are started with `docker compose`. These are defined in the top level `docker-compose.yml` file.

Then the script `test/integration/scripts/run-integration-scripts.sh` is run.

This script first waits for the RE_API to become ready. The RE_API will populate the arango db with collections as soon as it starts, which may take a few seconds.

When the RE_API is ready, the integration tests located in `test/integration/tests` are run. The tests are run in a small (ish, 64MB at last count, compared to the base python image size of 42MB) test container.

When the tests complete, the RE_API and support services are shut down.

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

