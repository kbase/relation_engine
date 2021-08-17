# Changelog for kbase/relation_engine

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for data_sources collection
  - collection definition
  - stored queries (one for all, one filtered by ns)
  - importer
  - sample data which can be used to populate RE for testing, etc.
- Support to make development alongside a downstream api (e.g. Taxonomy API) easier.
- Support for integration tests
  - add integration tests for data_sources importing
- Python docker container for usage with PyCharm or other IDEs which can use a Python docker container with an interpreter.

## [0.0.12] - 2021-01-29

### Added

- In the API, show the source file path or URL when updating the specs

## [0.0.11] - 2020-11-19

### Changed

- DJORNL edge spec (`spec/collections/djornl/djornl_edge.yaml``) updated to indicate whether or not the edge is directed.
- DJORNL parser and test suite updated accordingly.

## [0.0.10] - 2020-10-08

### Changed

- Clean up some of the configuration logic, and add the `SPEC_REPO_URL` env var instead of hard-coding
- Bundle the spec tarball in the docker image so other programs can use the image for testing

## [0.0.9] - 2020-10-05

### Fixed

- Fixed the function that concatenates parts of the query for the API

## [0.0.8] - 2020-09-18

### Fixed

- Remove need for authentication when waiting for the ArangoDB dependency to start (this is a staging server restriction)

## [0.0.7] - 2020-09-18

### Fixed

- Modified the docker deployment script so it can be used to release to the staging server

## [0.0.6] - 2020-08-20

### Added

- `relation_engine_server/api_versions/api_v1.py`: add and/or document API endpoints:
  - `/api/v1/specs/stored_queries`
  - `/api/v1/specs/data_sources`
- `spec/datasets`: new directory for dataset-specific schemas, e.g. DJORNL parser manifest, `spec/datasets/djornl/manifest.schema.json`
- `spec/test/test_manifest_schema.py`: to test the manifest schema against example input
- `importers/djornl/parser.py`: use manifest file to specify the files to be parsed and loaded into ArangoDB

### Changed

- `relation_engine_server/utils/spec_loader.py`: refactor to return a schema or the path to a schema file
- `importers/djornl/parser.py`: refactor parsing code to be more flexible and parse multiple files
- `spec/collections/djornl/*`, `spec/stored_queries/djornl/*`, `spec/views/djornl/*`, and `spec/test/djornl`: rename DB fields and headers in test files

### Removed

- `spec/test/djornl`: delete unneeded test files

## [0.0.5]

Last release with RE components in two repositories, <https://github.com/kbase/relation_engine_api> and <https://github.com/kbase/relation_engine_spec>
