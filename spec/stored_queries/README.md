# Relation Engine Stored Queries

Stored queries are templated AQL queries that fetch data from the database.

Variables in stored queries are prefixed with `@`.

The params field in each stored query should be a JSON schema of the query's parameters.

## Required format

Each stored query file should have a set of comments at the top describing the purpose of the query.

## Using stored queries from the API

See the [API docs](https://github.com/kbase/relation_engine_api) to see how to run these queries using the API.
