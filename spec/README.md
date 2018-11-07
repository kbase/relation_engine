# Relation Engine Spec

This repo holds the [views](views), [schemas](schemas), and [migrations](migrations) for the relation engine graph database service.

These specifications are used by the [Relation Engine API]()

* **Views** are stored [AQL queries](https://docs.arangodb.com/3.3/AQL/index.html) that can be used
by KBase apps to fetch data from the database.
* **Schemas** are [JSON schemas](https://json-schema.org/) that define what form of data can be stored in
the database's collections.
* **Migrations** are python modules that connect to the database and are responsible for transitioning the data in a collection from an old schema to a newer one.

## Development

### Running tests

The tests will validate JSON schema syntax and will look for any duplicate schema or view names.

Using python 3.5+, run `make test`.
