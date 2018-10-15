# Relation Engine Document Schemas

Document schemas define a required format for each collection in the database. Schemas use the
[JSON Schema](https://json-schema.org/specification.html) specification and follow the [JSON5
format](https://json5.org/)

## Guidelines

- The filename should be the name of the collection that the schema applies to.
- All schemas should be in [JSON5 format](https://json5.org/) and follow the [JSON
  Schema](https://json-schema.org/) specification.
- You can add reusable JSON schema definitions by placing them in the
  [`./definitions`](/src/schemas/definitions) directory.
- When writing a new schema, also make a [migration script](/src/migrations) that can update the
  database.

## Testing your schema format

Run `make test` in the root of the repo, which will validate all the schemas in this directory. You
can also run `make test-schemas` or `make test-schema <schema-path>` to test schemas specifically.

## Resources

- Quickly validate JSON schemas: https://www.jsonschemavalidator.net/
