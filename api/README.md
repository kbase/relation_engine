# Relation Engine API

A simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

## HTTP API v1

The API is a small, rest-ish service where all data is in JSON format. Replace the `{root_url}` in the examples below with one of:
 * Production: `https://kbase.us/services/relation_engine_api`
 * Staging: `https://ci.kbase.us/services/relation_engine_api`
 * App-dev: `https://appdev.kbase.us/services/relation_engine_api`

### GET /

Returns server status info

### POST /api/v1/query_results

Run a query using a view or a cursor ID. Semantically, this is a GET, but it's a POST to allow better support for passing JSON in the request body (eg. Postman doesn't allow request body data in get requests)

_Example rquest_

```sh
curl -X POST -d '{"argument": "value"}' {root_url}/api/v1/query_results?view=example
```

_Query params_
* `view` - required - string - name of the view to run as a query against the database
* `cursor_id` - required - string - ID of a cursor that was returned from a previous query with >100 results
* `full_count` - optional - bool - If true, return a count of the total documents before any LIMIT is applied (for example, in pagination). This might make some queries run more slowly

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

Results are limited to 100 items. To continue fetching additional results, use the `cursor_id` parameter.


#### Ad-hoc sysadmin queries

System admins can run ad-hoc queries by specifying a "query" property in the JSON request body.

```sh
curl -d '{"query": "for v in coll sort rand() limit @count return v", "count": 1}' \
    {root_url}/api/query_results
```

This will return the same form of results as above.

**Note:** Currently, all queries are read-only. This includes view queries and ad-hoc admin queries. Commands like `UPDATE` or `REMOVE` will fail.

### PUT /api/v1/documents

Bulk-update documents by either creating, replacing, or updating.

_Example_

```sh
curl -X PUT {root_url}/api/documents?collection=genes&on_duplicate=update
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

### PUT /api/v1/specs/

Manually check and pull spec updates. Requires sysadmin auth.

_Example_

```
curl {root_url}/api/update_specs
```

_Query params_
* `init_collections` - optional - boolean - defaults to true - whether to initialize any new collections in arango
* `spec_url` - optional - string - the specific url of the release to download and use (as a tarball). If left blank, then the latest release from github is used (not including any pre-releases or drafts).

Every call to update specs will reset the spec data (do a clean download and overwrite).

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

## Development

See the [Contribution Guidelines](/.github/CONTRIBUTING.md).

Run tests with:

```sh
make test
```

## Deployment

The docker image is pushed to Docker Hub when new commits are made to master. The script that runs when pushing to docker hub is found in `hooks/build`.

## Project anatomy

* Source code is in `./src`
* Tests are in  `./src/test`
* The main server code is in `./src/relation_engine_server`.
