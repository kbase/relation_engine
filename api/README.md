# Relation Engine API

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

View the root path of the running server in your browser to get the Swagger API interface.

View `/v1` to get server status. All API endpoints are nested under `/v1` and are documented via the Swagger API.

## Using the client

A python client is provided and published on anaconda, installable via pip or conda:

```sh
$ pip install --extra-index-url https://pypi.anaconda.org/kbase/simple relation_engine_client==0.1
```

Then import it:

```py
import relation_engine_client as rec
```

List out all the current relation engine views:

```py
views = rec.get_views(show_source=True)
# returns an array of {name, source}
```

List out all the current schemas

```py
schemas = rec.get_schemas(show_source=True)
# returns an array of {name, source}
```

## Development

Copy `.env.development.example` or `.env.production.example` to `.env` and edit it, if needed.

The docker image is pushed to Docker Hub when new commits are made to master.

Start up the server `make dev-server`.

Run tests against the server with `make test`.

## Building and publishing the client

The client package is built with setuptools and published to anaconda, where it can then be installed via pip or conda.

```sh
$ make build-client
$ make publish-client
```

## Project anatomy

* Source code is in `./src`
* Tests are in  `./src/test`
* The main server code is in `./src/relation_engine_server/__main__.py`
* API v1 endpoints are in `./src/relation_engine_server/api/api_v1.py`
* A python client package is in `./src/relation_engine_client`
