## 0.0.6

### `relation_engine_server`

- `relation_engine_server/api_versions/api_v1.py`: add and/or document API endpoints:
  - /api/v1/specs/stored_queries
  - /api/v1/specs/data_sources

- `relation_engine_server/utils/spec_loader.py`: refactor to return a schema or the path to a schema file

### `importers`

- `importers/djornl`: use manifest file to specify the list of files to be parsed to create a dataset. Refactor file parsing for more flexibility.

### `spec`

- add `datasets` folder for dataset-specific schemas

----

## 0.0.5

Last release with RE components in two repositories, https://github.com/kbase/relation_engine_api and https://github.com/kbase/relation_engine_spec
