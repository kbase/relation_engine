# Relation Engine Migrations

Migrations are python scripts (using pyArango) that migrate (or roll back) the database to a new
schema version.

## Guidelines

- Every migration script has two functions -- `forward` and `backward -- for migrating the database forwards or backwards.
- Every migration should specify a collection name, the version we're migrating *from*, and version we're migrating *to*
