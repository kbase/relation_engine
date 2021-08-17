# Data Sources

## Background

A data source describes a taxonomy or ontology namespace. Taxonomies and ontologies are created and managed by external organizations and roughly (or specifically, in the case of many ontologies) conform to the same data model. When imported into RE, each taxonomy and ontology is associated with a namespace identifier. Each data source is uniquely identified by this namespace identifier.

A data source describes the data organization (e.g. name, description, url) and characteristics of the data model. Generally the data model for taxonomies within RE are consistent within taxonomies, and ontologies are self-consistent as well. Assuming there is a "base" data model for taxonomies and ontologies, the data source describes any differences from that base model. More concretely, the data source provides a set of additional fields beyond the base model. This allows front end code to display taxonomy and ontology items in both a consistent manner (exploiting the base model) but with specificity (as informed by the data source definition.)

A default import data file is located in the `importers/data_sources/data` directory, containing data sources for taxonomy and ontology sources.

## Purpose

This document describes a procedure for loading data_sources into RE.

## Import via Docker container

Although the import script may be run directly from the host system via Python, it is easier and more reliable to run the import script within a Docker container.

See the [import doc](../README.md) for details on usage of the importer container.

### Example

#### Start a development RE API server

First, an RE API server must be available for importing to operate against. In this example, we'll start the development server locally:

```bash
make start-dev-server
SPEC_RELEASE_PATH=/opt/spec.tar.gz docker-compose up -d re_api
Creating relation_engine_workspace_1 ... done
Creating relation_engine_arangodb_1  ... done
Creating relation_engine_auth_1      ... done
Creating relation_engine_re_api_1    ... done
```

Note that this instance of the server uses the full Spec release to populate the database. This ensures that all collections are adequately set up, and ready for population.

#### Import data sources

Next, we run the container-based importer via the Makefile.

```bash
DATA_DIR=`pwd`/importers/data_sources/data IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

Note that we communicate parameters to the import container via environment variables. Internally, these environment variables are transformed to command line arguments for the import script.

In this case:

- `DATA_DIR` indicates an absolute path to the `data_sources` canonical data on the host system.
- `IMPORTER` indicates that we want to run the `data_sources` importer; the script is located in `importers/data_sources/import.py`.
- `RE_API_URL` provides the url to the RE API server; we are using the RE API development server, which is assigned the hostname `re_api` and port 5000; this hostname is only available inside the docker network, which is where the import script runs.
  server within the docker network.
- `AUTH_TOKEN` provides a KBase auth token to be used for RE API or other service requests. In this case, the development RE API and auth server recognizes `admin_token` and `nonadmin_token` as valid auth tokens.

The result should look like:

```bash
% DATA_DIR=`pwd`/importers/data_sources/data IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
WARNING: The QUIET variable is not set. Defaulting to a blank string.
WARNING: The VERBOSE variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://re_api:5000
[importer] ℹ     dry-run: False
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Saved docs to collection data_sources_nodes!
[importer] ℹ      created: 0
[importer] ℹ      empty: 0
[importer] ℹ      error: False
[importer] ℹ      errors: 0
[importer] ℹ      ignored: 0
[importer] ℹ      updated: 6
[importer] ℹ Finished Import
```

See the [importers docs](../README.md) for details.

## Direct import with Python

> Note that this method represents the original way to run the importer; now that the containerized workflow is in place, it may not be necessary to support direct import explicitly like this, although documenting the operation of the import script is still a good thing.

### Set up a Python environment

At top level of repo:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### Install Python dependencies

```bash
pip install -r dev-requirement.txt
```

### Ensure an RE API server is available

In this case, we will start up the local development server:

```bash
make start-dev-server
```

The relation engine will be running at on the host at `localhost:5000`, or internally at `re_api:5000` in the docker network.

When running against a local RE instance like this, you'll need to point the importer at `re_api:5000`. For a deployment, you would want to use the appropriate url, e.g. `https://ci.kbase.us/services/relation_engine`.

### Run an import in `dry-run` mode

The import script uses a file named `data_sources.json` to populate the `data_sources_nodes` collection.

Here we install from the default built-in data source, in dry-run mode, which prevents saving to the database.

```bash
(venv) % python -m importers.data_sources.importer --dry-run --re-api-url http://localhost:5000 --auth-token admin_token --data-dir importers/data_sources/data
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://localhost:5000
[importer] ℹ     dry-run: True
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Dry run completed successfully
[importer] ⚠ REMEMBER: Data not loaded
[importer] ℹ Finished Import
```

Let us tease this apart:

- we invoke the data_sources importer main script with `-m importers.data_sources.importer`
- we indicate this is a dry run with the `--dry-run` switch
- we specify the url for the RE API server we want to import into; in this case it is the url to the development server we started earlier, which operates on `localhost:5000` since it is operating inside the docker container, and port 5000 is exposed
- we use the KBase auth token `admin_token`, which is configured in the development server
- we use the built-in data in `importers/data_sources/data`.

The data is located in `importers/data_sources/data` and consists of a single file, `data_sources.json`. This file contains a good set of valid taxonomy and ontology data sources which can be used to seed the database or in testing.

In actual usage all of these arguments would be tailored to the actual task; the url would point to an actual RE API instance, the data would either update existing data sources or add new ones, and the token would be a real KBase token associated with an account which has admin privileges for RE.

#### Perform the import

Of course, our goal is to actually import data, so after an initial `--dry-run` to prove that the data is valid, we would want to perform a real import:

```bash
(venv)  % python -m importers.data_sources.importer --re-api-url http://localhost:5000 --auth-token admin_token --data-dir importers/data_sources/data
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://localhost:5000
[importer] ℹ     dry-run: False
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Saved docs to collection data_sources_nodes!
[importer] ℹ      created: 6
[importer] ℹ      empty: 0
[importer] ℹ      error: False
[importer] ℹ      errors: 0
[importer] ℹ      ignored: 0
[importer] ℹ      updated: 0
[importer] ℹ Finished Import
```

Note that the script reports that '6' documents were created.

#### Shut down server

The test RE API Server should be shut down when done:

```bash
make stop-dev-server
```

### Other Options

The `--quiet` switch may be used to prevent printing of notes to the terminal; off by default.

The `--verbose` switch may be used to have shell scripts echo their command lines; useful for debugging; off by default.

### Files involved

#### General usage

- `Makefile` (`make run-importer`)
- `Dockerfile.importer`
- `importers/import.sh`
- `importers/docker-compose.yaml`
- `importers/requirements.txt`

#### `data_sources` importer

- `importers`
  - `data_sources`
    - `data`
      - `data_sources.json`
    - `test/data`
    - `importer.py`
    - `README.md`

E.g.

Start the relation engine:

```bash
make start-dev
```
