# Relation Engine Spec

This repo holds the [stored queries](stored_queries), [schemas](schemas), and [migrations](migrations) for the relation engine graph database service.

These specifications are used by the [Relation Engine API]()

* **Stored queries** are stored [AQL queries](https://docs.arangodb.com/3.3/AQL/index.html) that can be used
by KBase apps to fetch data from the database.
* **Schemas** are [JSON schemas](https://json-schema.org/) that define what form of data can be stored in
the database's collections.
* **Data sources** (in `data_sources/`) contains some general information about where some of our imported data comes from.
* **Views** (in `views/`) are raw ArangoSearch view configuration files

## Development

### Running tests

Run tests with `make test`.
