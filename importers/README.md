# RE Importers

This directory holds python modules that import data into the Relation Engine (RE) database (ArangoDB.)

## Running importers directly

Configure importers through environment variables with the `RES_` prefix (which stands for Relation Engine Spec).

Global env vars:

* `RES_AUTH_TOKEN` - auth token to use when making requests to RE API - defaults to test value
* `RES_API_URL` - url to use for the RE API - defaults to test value

### djornl

```sh
RES_ROOT_DATA_PATH=/path/to/djornl_data \
python -m importers.djornl.parser
```

## Running importers in a Docker container

Some importers are configured to run directly in a container. These importers work slightly differently. They do not use namespaced environment variables to pass parameters to the import script, but rather command line arguments. However, environment variables are still used to pass information to the `docker-compose` command.

### Invocation

#### Environment Variables

##### Required

* `DATA_DIR` - directory in which import data is located
* `IMPORTER` - name of the importer subdirectory
* `RE_API_URL` - url to a running instance of the RE_API
* `AUTH_TOKEN` - a KBase auth token (RE admin token for import to kbase)

##### Optional

* `QUIET` - if set, disables printing of messages
* `VERBOSE` - if set, enables printing of executed script lines

##### Command

```bash
DATA_DIR IMPORTER RE_API_URL AUTH_TOKEN [QUIET VERBOSE] make run-importer
```

### Overview

* `make run-importer` with environment variables providing parameterization
* `scripts/run-importer.sh` ensures required environment variables are present; runs the importer container
* `importer/docker-compose.yaml` controls execution of the import docker container; capturing environment variables
* `importer/importer.sh` - entrypoint script for import invokes the import Python script, converting shell environment variables to command line arguments

### Requirements

* make
* docker

### Example

An RE API server should be available for importing to operate against. In this example, we'll start the development server locally:

```bash
make start-dev-server
```

Then we run the container-based importer via the Makefile.

```bash
DATA_DIR=`pwd`/importers/data_sources/data IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

Note that we communicate parameters to the import container via environment variables. Internally, these environment variables are transformed to command line arguments for the import script.

> We could also use make arguments, but this project uses environment variables already.

In this case:

* `DATA_DIR` indicates an absolute path to the import data on the host system; it will be made available to the import script's container via volume mounting.
* `IMPORTER` determines which import script is run; the script should be located in `importers/IMPORTER/import.py`.
* `RE_API_URL` provides the url to the RE API server; in this case the hostname `re_api` assigned to the RE API development container, and it is exposed at port 5000.
  server within the docker network.
* `AUTH_TOKEN` provides a KBase auth token to be used for RE API or other service requests. In this case, the development RE API and auth server recognizes `admin_token` and `nonadmin_token` as valid auth tokens.

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

### More examples

#### Inhibit messages (`QUIET`)

Use the `QUIET` variable to stop printing most information to the console. Setting it to any non-blank string will set QUIET mode.

```bash
% QUIET=t DATA_DIR=`pwd`/importers/data_sources/data  IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
WARNING: The VERBOSE variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
```

Note that informational lines are still printed. These are from `docker-compose`, and cannot be prevented.

#### Print more info (`VERBOSE`)

On the other hand, the printing of script lines may be enabled with the `VERBOSE` flag:

```bash
% VERBOSE=t QUIET=t DATA_DIR=`pwd`/importers/data_sources/data  IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
+ '[' -z /Users/erikpearson/work/kbase/sprints/2021Q2/relation_engine/importers/data_sources/data ']'
+ MAP_APP=
+ '[' -n '' ']'
+ cd importers
+ docker-compose run -v /Users/erikpearson/work/kbase/sprints/2021Q2/relation_engine/importers/data_sources/data:/data --rm importer
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
+ '[' -z data_sources ]
+ '[' -z http://re_api:5000 ]
+ '[' -z admin_token ]
+ export 'IMPORT_PATH=importers.data_sources.importer'
+ export 'ARGS=--data-dir /data --re-api-url http://re_api:5000 --auth-token admin_token  --quiet'
+ python -m importers.data_sources.importer --data-dir /data --re-api-url http://re_api:5000 --auth-token admin_token --quiet
```

Note the addition of the lines beginning with `+`: These are the actual script lines run by the container's entrypoint script.

#### Use custom data (`DATA_DIR`)

Data may be imported from an arbitrary directory with the `DATA_DIR` environment variable. Within this directory must be a JSON file named `data_sources.json`.

```bash
DATA_DIR=`pwd`/temp IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

#### Dry Run

The "dry run" mode will cause the importer to load and verify the data, but it will not save it to the database.

As with the other importer switches, `DRY_RUN` is enabled by setting the environment variable to any non-empty string.

```bash
% DRY_RUN=t DATA_DIR=`pwd`/importers/data_sources/data IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
WARNING: The QUIET variable is not set. Defaulting to a blank string.
WARNING: The VERBOSE variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://re_api:5000
[importer] ℹ     dry-run: True
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Dry run completed successfully
[importer] ⚠ REMEMBER: Data not loaded
[importer] ℹ Finished Import
```

Note the warning message towards the bottom, `⚠ REMEMBER: Data not loaded`. 
