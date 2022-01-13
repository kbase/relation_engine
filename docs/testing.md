# Testing

All tests are run in docker containers. Tests are invoked with Makefile tasks.

Top level dependencies are:

- make
- docker

## Unit testing

```bash
make unit-tests
```

## Integration Testing

```bash
make integration-tests
```

## All Tests and code quality checks

```bash
make test
```

Note that after running this, files may have been reformatted by `black`. 
