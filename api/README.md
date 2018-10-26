# Biochem Server with ArangoDB

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

View the root path of the running server in your browser to get the Swagger API interface.

View `/v1` to get server status. All API endpoints are nested under `/v1` and are documented via the Swagger API.

## Development

Copy `.env.development.example` or `.env.production.example` to `.env` and edit it, if needed.

The docker image is pushed to Docker Hub when new commits are made to master.

Start up the server `make dev-server`.

Run tests against the server with `make test`.

## Project anatomy

* Source code is in `./src`
* Tests are in  `./src/test`
* The main server code is in `./src/relation_engine_api/__main__.py`
* API v1 endpoints are in `./src/relation_engine_api/api/api_v1.py`
