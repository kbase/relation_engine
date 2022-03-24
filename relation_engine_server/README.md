# Relation Engine API

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

## Python client

There is a [pip-installable python client](client_src/README.md) that can be used to access the RE API.

## HTTP API v1

The API is a small, rest-ish service where all data is in JSON format. Replace the `{root_url}` in the examples below with one of:
 * Production: `https://kbase.us/services/relation_engine_api`
 * Staging: `https://ci.kbase.us/services/relation_engine_api`
 * App-dev: `https://appdev.kbase.us/services/relation_engine_api`

### Error responses

The majority of errors returned from the server have explanatory information in the response content in the following format:

```json

{
  "error": {
    "message": "A brief message explaining the error",
  }
}
```

Specific errors may have other fields giving more details, e.g. JSON parsing errors have `source_json`, `pos`, `lineno`, and `colno` describing the error; ArangoDB errors have an `arango_message` field.

### GET /

Returns server status info

### POST /api/v1/query_results

Run a query using a stored query or a cursor ID. Semantically, this is a GET, but it's a POST to allow better support for passing JSON in the request body (eg. Postman doesn't allow request body data in get requests)

_Example request_

```sh
curl -X POST -d '{"argument": "value"}' {root_url}/api/v1/query_results?stored_query=example
```

_Query params_
* `stored_query` - required - string - name of the stored query to run as a query against the database
* `cursor_id` - required - string - ID of a cursor that was returned from a previous query with >100 results
* `full_count` - optional - bool - If true, return a count of the total documents before any LIMIT is applied (for example, in pagination). This might make some queries run more slowly

Pass one of `stored_query` or `cursor_id` -- not both.

_Request body_

When running a new query, the request body can be a JSON object of all bind variables for the query. Anything with a `@name` in the query source should have an entry in the object here. For example, a query with bind vars for `@@collection` and `@value`, you will need to pass:

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

Results are limited to 100 items. To continue fetching additional results, use the `cursor_id` parameter.


#### Ad-hoc sysadmin queries

System admins can run ad-hoc queries by specifying a "query" property in the JSON request body.

```sh
curl -d '{"query": "for v in coll sort rand() limit @count return v", "count": 1}' \
    {root_url}/api/v1/query_results
```

This will return the same form of results as above.

**Note:** Currently, all queries are read-only. This includes stored queries and ad-hoc admin queries. Commands like `UPDATE` or `REMOVE` will fail.

### PUT /api/v1/documents

Bulk-update documents by either creating, replacing, or updating.

_Example_

```sh
curl -X PUT {root_url}/api/v1/documents?collection=genes&on_duplicate=update
```

_Query params_
* `collection` - required - string - name of the collection that we want to bulk-import into.
* `on_duplicate` - optional - "replace", "update", "ignore", "error" - Action to take when we find a duplicate document by `_key`. "replace" replaces the whole document. "update" merges in the new values. "ignore" takes no action. "error" cancels the entire transaction.
* `display_errors` - optional - bool - whether to return error messages for each document that failed to save in the response. This is disabled by default as it will slow down the response time.

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

#### JSON Schema error responses

If you try to update a collection and it fails validation against a JSON schema found in the [relation engine spec](spec/), then you will get a JSON error response with the following fields:

* `"message"` - Human readable message explaining the error
* `"failed_validator"` - The name of the validator that failed (eg. "required")
* `"value"` - The (possibly nested) value in your data that failed validation
* `"path"` - The path into your data where you can find the value that failed validation

### PUT /api/v1/specs/

Manually check and pull spec updates. Requires sysadmin auth.

_Example_

```
curl {root_url}/api/v1/update_specs
```

_Query params_
* `init_collections` - optional - boolean - defaults to true - whether to initialize any new collections in arango (also creates indexes and views)
* `release_url` - optional - string - the specific url of the release to download and use (as a tarball). If left blank, then the latest release from github is used (not including any pre-releases or drafts).

Every call to update specs will reset the spec data (do a clean download and overwrite).

### GET /api/v1/specs/collections

Get all collection names (returns an array of strings):

```sh
GET {root_url}/api/v1/specs/collections
```

Example response:

```json
["test_vertex", "test_edge"]
```

Get the schema for a specific collection

```sh
GET "{root_url}/api/v1/specs/collections?name=test_vertex"
```

Example response:

```json
{
  "name": "test_vertex",
  "type": "vertex",
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["_key"],
    "description": "An example vertex schema for testing",
    "properties": {
      "_key": {"type": "string"},
      "is_public": {"type": "boolean"},
      "ws_id": {"type": "integer"}
    }
  }
}
```

Get the schema for a particular document by its full ID

```sh
GET "{root_url}/api/v1/specs/collections?doc_id=test_vertex/1"
```

The response will have the same format as the example response above

### GET /api/v1/specs/data_sources

See also `GET /api/v1/data_sources` for a similar API that returns results in a slightly different format.

Get all data source names (returns an array of strings):

```sh
GET {root_url}/api/v1/specs/data_sources
```

Example response:

```json
["envo_ontology", "go_ontology", "gtdb"]
```

Get the schema for a specific data source

```sh
GET "{root_url}/api/v1/specs/data_sources?name=ncbi_taxonomy"
```

Example response:

```json
{
  "name": "ncbi_taxonomy",
  "category": "taxonomy",
  "title": "NCBI Taxonomy",
  "home_url": "https://www.ncbi.nlm.nih.gov/taxonomy",
  "data_url": "ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/",
  "logo_url": "https://kbase.us/ui-assets/images/third-party-data-sources/ncbi/logo-51-64.png"
}
```

Response JSON schema:

```json
{ "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "canonical identifier for this data source"
    },
    "category": {
      "type": "string",
      "description": "parent category, such as taxonomy or ontology"
    },
    "title": {
      "type": "string",
      "description": "human readable name for the data source"
    },
    "home_url": {
      "type": "string",
      "description": "full URL of the home page for the data source"
    },
    "data_url": {
      "type": "string",
      "description": "full URL from where the data can be downloaded"
    },
    "logo_url": {
      "type": "string",
      "description": "the URL of a logo image representing this data source"
    },
  }
}
```


### GET /api/v1/specs/stored_queries

Get all stored query names (returns an array of strings):

```sh
GET {root_url}/api/v1/specs/stored_queries
```

Example response:

```json
["fetch_test_vertices", "fetch_test_edges", "ncbi_fetch_taxon"]
```

Get the schema for a specific stored query

```sh
GET "{root_url}/api/v1/specs/stored_queries?name=ncbi_fetch_taxon"
```

Example response:

```json
{
  "stored_query": {
    "name": "ncbi_fetch_taxon",
    "params": {
      "type": "object",
      "required": [
        "id",
        "ts"
      ],
      "properties": {
        "id": {
          "type": "string",
          "title": "NCBI Taxonomy ID"
        },
        "ts": {
          "type": "integer",
          "title": "Versioning timestamp"
        }
      }
    },
    "query": "for t in ncbi_taxon\n    filter t.id == @id\n    filter t.created <= @ts AND t.expired >= @ts\n    limit 1\n    return t\n"
  }
}
```


### GET /api/v1/data_sources

See also `GET /api/v1/spec/data_sources` for the standard `/specs` API endpoint access to this data.

Fetch a list of data source names. Will return an array of strings.

Example response body:

```json
{"data_sources": ["x", "y", "z"]}
```
The response is nearly identical to that for `GET /api/v1/specs/data_sources`, but this data is held in an object under the key `data_sources`.


Response JSON schema:

```json
{ "type": "object",
  "properties": {
    "data_sources": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

### GET /api/v1/data_sources/{name}

Fetch the details for a data source by name. Will return an object of key/value details.

Example response body:

```json
{
  "data_source": {
    "name": "envo_ontology",
    "category": "ontology",
    "title": "Environment Ontology",
    "home_url": "http://www.obofoundry.org/ontology/envo.html",
    "data_url": "https://github.com/EnvironmentOntology/envo/releases",
    "logo_url": "https://ci.kbase.us/ui-assets/images/third-party-data-sources/envo/logo-119-64.png"
  }
}
```

Response JSON schema is the same as for `GET /api/v1/specs/data_sources?name=data_source_name`, but the data is held in an object under the key `data_source`.


## Administration

The following environment variables should be configured:

* `KBASE_AUTH_URL` - url of the KBase authentication (auth2) server to use
* `SHARD_COUNT` - number of shards to use when creating new collections
* `KBASE_WORKSPACE_URL` - url of the KBase workspace server to use (for authorizing workspace access)
* `DB_URL` - url of the arangodb database to use for http API access
* `DB_USER` - username for the arangodb database
* `DB_PASS` - password for the arangodb database
* `DB_READONLY_USER` - read-only username for the arangodb database
* `DB_READONLY_PASS` - read-only password for the arangodb database

### Update specs

To update specs while the server is running, use this curl command with an RE_ADMIN token:

```sh
curl -X PUT -H "Authorization: <mytoken>" \
  "https://ci.kbase.us/services/relation_engine_api/api/v1/specs?init_collections=1
```

## Deprecated Endpoints

#### GET `/api/v1/specs/schemas` (replaced by `/api/v1/specs/collections`)

This endpoint has been deprecated; queries should use `/api/v1/specs/collections` instead.


## Development

See the [Contribution Guidelines](/.github/CONTRIBUTING.md).

Run tests with:

```sh
make test
```

## Deployment

Deploy the image by running the `scripts/docker_deploy` script.

The image tag will be taken from the `VERSION` file found in the root of the repo.

## Project anatomy

* The main server code is in `./relation_engine_server`.
* Tests are in  `./relation_engine_server/test`
