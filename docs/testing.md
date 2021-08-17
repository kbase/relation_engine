# Testing

All tests are run in docker containers, and the test scripts are run via the Makefile. Thus top level dependencies are:

- make
- docker

## Unit testing

### Quick

```bash
make unit-tests
```

## Integration Testing

```bash
make integration-tests
```

## All Tests

```bash
make test
```
