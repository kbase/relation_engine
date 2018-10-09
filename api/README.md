# Biochem Server with ArangoDB

## Development

Start up the server with `docker-compose up` or `make dev-server`.

Rebuild the server with `make dev-build`.

Run the tests with `make test`.

## Project anatomy

* Source code is in `./src`
* Tests are in  `./src/test`
* The server startup code is in `./src/arangodb_biochem_server/app.py`
* API v1 endpoints are in `./src/arangodb_biochem_server/api/api_v1.py`
