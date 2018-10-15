# Relation Engine Spec

This repo holds the [views](src/views), [schemas](src/schemas), and [migrations](src/migrations) for the relation engine graph database service.

The views are stored [AQL queries](https://docs.arangodb.com/3.3/AQL/index.html) that can be used
by KBase apps to fetch data from the database.

Schemas are [JSON schemas](https://json-schema.org/) that define what form of data can be stored in
the database's collections.

Migrations are python modules that connect to the database and are responsible for transitioning
the data in a collection from an old schema to a newer one.

Versioning on collections:
- Schemas and migrations have a simple incremental version
- The database associates a version with each collection
- If a new schema/migration is added with a higher version, then the migration is run, the new
  schema is saved, and the version in the database is incremented.
- If there are multiple schemas/migrations that are newer for a collection, then each migration
  will get run in order until they have all been applied.
- Migrations can get rolled back (each migration has an `up` and `down` function).

Views and migrations both have python tests located in [`./src/test`](src/test)


_Questions_

- How do developers write and test new views and migrations and run them against test data?
  - Provide a small docker image with a subset of data from prod
