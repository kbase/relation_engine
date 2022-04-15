# Relation Engine Spec

This repo holds the [stored queries](spec/stored_queries), [collections](spec/collections), and [migrations](migrations) for the relation engine graph database service.

These specifications are used by the [Relation Engine API](relation_engine_server).

* **[Stored queries](spec/stored_queries)** are stored [AQL queries](https://docs.arangodb.com/3.5/AQL/index.html) that can be used
by KBase apps to fetch data from the database.
* **[Collections, or document schemas,](spec/collections)** are [JSON schemas](https://json-schema.org/) that define what form of data can be stored in the database's collections.
* **[Datasets](spec/datasets)** contain partial and full schemas specific to a certain dataset.
* **[Data sources](spec/data_sources)** contain general information about where some of our imported data comes from.
* **[Views](spec/views)** are raw ArangoSearch view configuration files
* **[Analyzers](spec/analyzers)** are analyzer configuration files

## Development

### Running tests

Tests are located in the [spec/tests](spec/tests) directory, and are run as part of the test suite triggered by `scripts/run_tests.sh`.
