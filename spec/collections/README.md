# Relation Engine Document Schemas

Document schemas define a required format for each collection in the database. Schemas use the
[JSON Schema](https://json-schema.org/specification.html) specification.

## Guidelines

- Every schema file should have `name`, `type` ("vertex" or "edge"), and `schema` (JSON schema) fields
- Every JSON schema should have a "$schema" field
- You can add reusable JSON schema definitions by placing them in the [`./definitions`](/src/schemas/definitions) directory.

## Testing your schema format

Run `make test` in the root of the repo, which will validate all the schemas in this directory. You
can also run `make test-schemas` or `make test-schema <schema-path>` to test schemas specifically.

## Resources

- Quickly validate JSON schemas: https://www.jsonschemavalidator.net/

## Data

### Ontologies

* Gene Ontology (GO): **[go/](/spec/collections/GO)**
* Environmental Ontology (ENVO): **[envo/](/spec/collections/ENVO)**

### Taxonomies

* Genome Taxonomy Database (GTDB): **[gtdb/](/spec/collections/gtdb)**
* Ribosomal Database Project (RDP): **[rdp/](/spec/collections/rdp)**
* SILVA: **[silva/](/spec/collections/silva)**
