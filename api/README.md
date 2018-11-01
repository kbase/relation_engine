# Relation Engine API

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

View the root path of the running server in your browser to get the Swagger API interface.

View `/v1` to get server status. All API endpoints are nested under `/v1` and are documented via the Swagger API.

## HTTP API

### GET /api/views

Return a list of view names and optionally the AQL source code for each.

_Example_

```sh
$ curl -X GET http://relation_engine/api/views?show_source=1
```

_Query params_
* `show_source` - optional - boolean - whether to show the full AQL source for each view

_Response JSON schema_

```json
{ "type": "object",
  "properties": {
    "names": {
      "type": "array",
      "item": "string",
      "description": "Array of view names"
    },
    "content": {
      "type": "object",
      "description": "An object where keys are view names and properties are AQL source."
    }
  }
}
```

The `"content"` property is returned only if the `show_source` query parameter is truthy.

### GET /api/schemas

Return a list of schema names and optionall the JSON schema source for each.

_Example_

```sh
$ curl -X GET http://relation_engine/api/schemas?show_source=1
```

_Query params_
* `show_source` - optional - boolean - whether to show the full JSON source for each schema

_Response JSON schema_
```json
{ "type": "object",
  "properties": {
    "names": {
      "type": "array",
      "item": "string",
      "description": "Array of schema names"
    },
    "content": {
      "type": "object",
      "description": "An object where keys are schema names and properties are JSON schemas."
    }
  }
}
```

### POST /query

Run a new query using a view.

_Example_

```sh
$ curl -X - POST http://relation_engine/api/query?view=example
```

_Query params_
* `view` - required - string - name of the view to run as a query against the database

_Response JSON schema_

```json
{ "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "description": "Result data from running with a maximum of 100 entries."
    },
    "count": {
      "type": "integer",
      "description": "Total count of results."
    },
    "has_more": {
      "type": "boolean",
      "description": "Whether additional results can be fetched with the cursor_id."
    },
    "cursor_id": {
      "type": "string",
      "description": "A cursor ID that you can use to fetch more results, if they are present."
    },
    "stats": {
      "type": "object",
      "description": "Information about how this query affected the database and its run-time."
    }
  }
}
```

Results are limited to 100 items. To continue fetching additional results, use the `cursor_id` below:

### GET /query_cursor

Fetch more results from existing query results using a cursor ID

_Example_

```sh
$ curl -X GET http://relation_engine/api/query_cursor?id=123123123
```

_Query params_
* `id` - required - string - cursor ID as found in the query results object above when `has_more` is true.

The response JSON will match the same JSON schema as the one for the response under `POST /query`

### PUT /documents

Bulk-update documents by either creating, replacing, or updating.

_Example_

```sh
$ curl -X PUT http://relation_engine/api/documents?collection=genes&
```

_Query params_
* `collection` - required - string - name of the collection that we want to bulk-import into.
* `on_duplicate` - optional - "replace", "update", "ignore", "error" - Action to take when we are saving a duplicate document by matching `_key`. "replace" replaces the whole document. "update" merges in the new values. "ignore" takes no action. "error" cancels the entire transaction.
* `overwrite` - optional - boolean - whether to overwrite the whole collection (that is, delete all documents currently in the collection before creating the documents you provide)

_Request body_

The request body should be a series of JSON documents separated by line-breaks. For example:

```
{"_key": "1", "name": "x"}
{"_key": "2", "name": "y"}
```

_Response JSON schema_

```json
{ "type": "object",
  "properties": {
    "created": {
      "type": "integer",
      "description": "Count of documents that were created."
    },
    "errors": {
      "type": "integer",
      "description": "Count of documents that had an error in saving."
    },
    "empty": {
      "type": "integer",
      "description": "Count of empty lines in the import."
    },
    "updated": {
      "type": "integer",
      "description": "Count of documents that were updated with an attribute merge."
    },
    "ignored": {
      "type": "integer",
      "description": "Count of documents that were not imported due to a match."
    },
    "error": {
      "type": "boolean",
      "description": "Whether the entire save operation was cancelled due to an error."
    }
  }
}
expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
```

## Python client API

A python client is provided and published on anaconda, installable via pip or conda:

```sh
$ pip install --extra-index-url https://pypi.anaconda.org/kbase/simple relation_engine_client==0.1
```

Then import it:

```py
import relation_engine_client as rec
```

You can set the environment variable `RELATION_ENGINE_URL` to set the URL of the HTTP API you want to use.

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

Copy `.env.example` to `.env`. Start the server with `docker-compose up`.

Run tests with `make test`.

The docker image is pushed to Docker Hub when new commits are made to master. The script that runs when pushing to docker hub is found in `hooks/build`.

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
