# Relation Engine API

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

## HTTP API

### GET /

Returns server status info

### GET /api/views

Return a list of view names.

_Example request_

```sh
$ curl -X GET http://relation_engine/api/views
```

_Example response_

```json
["example_view1", "example_view1"]
```

### GET /api/schemas

Fetch the registered schema names.

_Example request_
```sh
$ curl -X GET http://relation_engine/api/schemas
```

_Example response_

```json
{
  "vertices": ["vertex_examples1", "vertex_examples2"],
  "edges": ["edge_example1", "edge_example2"]
}
```

### GET /api/views/<name>

Get the AQL source code for a view

_Example request_

```sh
$ curl http://relation_engine/api/views/example_view1
```

Response has mimetype of text/plain

_Example response_

```json
// This is some AQL source code

for x in @@collection
  return x
```

### GET /api/schemas/<name>

Get the JSON source for a registered schema by name.

_Example request_

```sh
$ curl http://relation_engine/api/schemas/vertex_examples1
```

_Example response_

```json
{
  "type": "object",
  "required": ["_key"],
  "properties": {"_key": {"type": "string"}}
}
```

### POST /api/query_results

Run a query using a view or a cursor ID. Semantically, this is a GET, but it's a POST to allow better support for passing JSON in the request body (eg. Postman doesn't allow request body data in get requests)

_Example rquest_

```sh
$ curl -X POST -d '{"argument": "value"}' http://relation_engine/api/query?view=example
```

_Query params_
* `view` - required - string - name of the view to run as a query against the database
* `cursor_id` - required - string - ID of a cursor that was returned from a previous query with >100 results

Pass one of `view` or `cursor_id` -- not both.

_Request body_

When running a new query with a view, the request body should be a JSON object of all bind variables for the query. Anything with a `@name` in the query source should have an entry in the object here. For example, a query with bind vars for `@@collection` and `@value`, you will need to pass:

```json
{ "@collection": "collection_name", "value": "my_value"}
```

If you are using a cursor, the request body should be blank.

_Example response_

```json
{
  "results": [..],
  "count": 100,
  "has_more": true,
  "cursor_id": 123,
  "stats": {..}
}
```

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

#### Ad-hoc sysadmin queries

System admins can run ad-hoc queries by specifying a "query" property in the JSON request body.

```sh
$ curl -X POST \
    -d '{"query": "for v in coll sort rand() limit @count return v", "count": 1}' \
    http://relation_engine/api/query?view=example
```

This will return the same form of results as above.

### PUT /api/documents

Bulk-update documents by either creating, replacing, or updating.

_Example_

```sh
$ curl -X PUT http://relation_engine/api/documents?collection=genes&on_duplicate=update
```

_Query params_
* `collection` - required - string - name of the collection that we want to bulk-import into.
* `on_duplicate` - optional - "replace", "update", "ignore", "error" - Action to take when we find a duplicate document by `_key`. "replace" replaces the whole document. "update" merges in the new values. "ignore" takes no action. "error" cancels the entire transaction.
* `overwrite` - optional - boolean - whether to overwrite the whole collection (that is, delete all documents currently in the collection before creating the documents you provide)

_Request body_

The request body should be a series of JSON documents separated by line-breaks. For example:

```
{"_key": "1", "name": "x"}
{"_key": "2", "name": "y"}
```

_Example response_

```json
{"created": 3, "errors": 2, "empty": 0, "updated": 0, "ignored": 0, "error": false}
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
```

### GET /api/update_specs

Manually check and pull spec updates. Requires sysadmin auth.

_Example_

```
$ curl http://relation_engine/api/update_specs
```

_Query params_
* `init_collections` - optional - boolean - whether to initialize any new collections in arango
* `reset` - optional - boolean - whether to completely reset the spec data (do a clean download and overwrite)

## Python client API

> NOTE: Work in progress -- this is not yet available

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
```

List out all the current schemas

```py
schemas = rec.get_schemas(show_source=True)
```

Run a query:

```py
results = rec.query(view=view_name, bind_vars={'@collection': 'genes', 'value': 123})
```

Get more results from a cursor:

```py
more_results = rec.run_query(cursor_id=results['cursor_id'])
```

Save documents from python dictionaries:

```py
save_results = rec.save_documents(
  collection='genes',
  on_duplicate='update',
  docs=[
    {'_key': 'x', 'name': 'x'},
    {'_key': 'y', 'name': 'y'}
  ]
)
```

Bulk-save documents from a file:

```py
save_results = rec.save_documents(
  collection='genes',
  on_duplicate='update',
  from_file='my-file-path.json'
)
```

Where the file contains multiple JSON documents separated by line-breaks.

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
