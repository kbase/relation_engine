# Install data_sources dataset

The script and data within this directory allow one to load _data sources_ into the RE database via the RE API.

A default import data file is located in the `importers/data_sources/data` directory, containing data sources for
taxonomy and ontology sources.

This script has only been used in development thus far. In this case, a local RE API server is started first and
subsequently used as the target for importing.

> This document describes a procedure for loading data locally, but does not claim provenance over production data provisioning. This script should work fine for initial load, and can be used for subsequent updates if the script is pointed at a data file which contains just the new documents.

This

## Import via Docker container

Although the import script may be run directly from the host system via a virtual environment terminal, it is easier and
more reliable to run the import script within a Docker container.

### Requirements

- make
- docker

### Example

An RE API server should be available for importing to. In this example, we'll start the development server locally:

```bash
make start-dev-server
```

Then we run the container-based importer via the Makefile.

```bash
IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

Note that we communicate parameters to the import container via environment variables. Internally, these environment
variables are transformed to command line arguments for the import script.

In this case:

- `IMPORTER` determines which import script is run; the script should be located in `importers/IMPORTER/import.py`.
- `RE_API_URL` provides the url to the RE API server; in this case it is the hostname assigned to the RE API development
  server within the docker network.
- `AUTH_TOKEN` provides a KBase auth token to be used for RE API or other service requests. In this case, the
  development auth server recognizes `admin_token` and `nonadmin_token` as valid auth tokens.

The result should look like:

```bash
(venv) % IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
cd importers && docker-compose run --rm importer
WARNING: The DATA_DIR variable is not set. Defaulting to a blank string.
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
WARNING: The QUIET variable is not set. Defaulting to a blank string.
WARNING: The VERBOSE variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://re_api:5000
[importer] ℹ     data-dir: None
[importer] ℹ     dry-run: False
[importer] ℹ      (Taking data dir from default)
[importer] ℹ      data_dir: "/app/importers/data_sources/data"
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

### More examples

#### Inhibit messages (QUIET)

Use the `QUIET` variable to stop printing most information to the console. Setting it to any non-blank string will set
QUIET mode.

```bash
(venv) % QUIET=t IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
WARNING: The DATA_DIR variable is not set. Defaulting to a blank string.
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
WARNING: The VERBOSE variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
```

Note that informational lines are still printed. These are from `docker-compose`, and cannot be prevented.

#### Print more info (VERBOSE)

On the other hand, the printing of script lines may be enabled with the `VERBOSE` flag:

```bash
(venv) % VERBOSE=t QUIET=t IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
WARNING: The DATA_DIR variable is not set. Defaulting to a blank string.
WARNING: The DRY_RUN variable is not set. Defaulting to a blank string.
Creating importers_importer_run ... done
+ '[' -z data_sources ]
+ '[' -z http://re_api:5000 ]
+ '[' -z admin_token ]
+ export 'IMPORT_PATH=importers.data_sources.importer'
+ export 'ARGS=--re-api-url http://re_api:5000 --auth-token admin_token   --quiet'
+ python -m importers.data_sources.importer --re-api-url http://re_api:5000 --auth-token admin_token --quiet
```

Note the addition of the lines beginning with `+`: These are the actual script lines run by the container's entrypoint
script.

#### Use custom data (DATA_DIR)

Data may be imported from an arbitrary directory with the `DATA_DIR` environment variable. Within this directory must be
a JSON file named `data_sources.json`.

```bash
DATA_DIR=`pwd`/temp IMPORTER=data_sources RE_API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

### More

See the [importers docs](../README.md) for details.

## Direct import with Python

Set up a Python environment:

At top level of repo:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

Install Python dependencies:

```bash
pip install -r dev-requirement.txt
```

Run the data importer. Each importer is an independent script, but they will probably follow a pattern similar to this
example.

The import script uses a file named `data_sources.json` to populate the `data_sources_nodes` collection.

Here we install from the default built-in data source, in dry-run mode, which prevents saving to the database.

```bash
 (venv) % python -m importers.data_sources.importer --dry-run --re-api-url http://localhost:5000 --auth-token none                  
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://localhost:5000
[importer] ℹ     dry-run: True
[importer] ℹ     (Taking data dir from default)
[importer] ℹ     data-dir: "/Users/erikpearson/work/kbase/relation_engine/importers/data_sources/data"
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Dry run completed successfully
[importer] ⚠ REMEMBER: Data not loaded
[importer] ℹ Finished Import

```

Note that the import script reports that it is importing the default, base data. This data is located
in `importers/data_sources/data` and consists of a single file, `data_sources.json`. This file contains a good set of
valid taxonomy and ontology data sources which can be used to seed the database or in testing.

In the next example we use an external data source, in this case located in the `temp`:

```bash
(venv )% `python -m importers.data_sources.importer --dry-run --re-api-url http://localhost:5000 --auth-token none --data-dir temp`
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://localhost:5000
[importer] ℹ     dry-run: True
[importer] ℹ     (using provided data dir
[importer] ℹ     data-dir: "temp"
[importer] ✓ Data loaded and validated successfully
[importer] ✓ Dry run completed successfully
[importer] ⚠ REMEMBER: Data not loaded
[importer] ℹ Finished Import
```

The `quiet` option may be used to prevent printing of notes to the terminal:

```bash
(venv) % python -m importers.data_sources.importer --dry-run --re-api-url http://localhost:5000 --auth-token none --quiet
(venv) % 

```

Finally, to import the data, simply remove `--dry-run`.

In this example we'll first start up a local testing copy of the RE API server:

```bash
make start-dev-server
```

This makes the RE API available on the host machine at http://localhost:5000. (In a later section, we'll see that the
import script may (should) be run inside a docker container.)

```bash
python -m importers.data_sources.importer --re-api-url http://localhost:5000 --auth-token admin_token ```

```bash
(venv)  % python -m importers.data_sources.importer --re-api-url http://localhost:5000 --auth-token admin_token
[importer] ℹ Starting Import
[importer] ℹ Loading data
[importer] ℹ Parameters:
[importer] ℹ     re-api-url: http://localhost:5000
[importer] ℹ     dry-run: False
[importer] ℹ     (Taking data dir from default)
[importer] ℹ     data-dir: "/Users/erikpearson/work/kbase/relation_engine/importers/data_sources/data"
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

The test RE API Server should be shut down when done:

```bash
make stop-dev-server
```

### Files involved:

- `Makefile` (`make run-importer`)
- `Dockerfile.importer`
- `importers/import.sh`
- `importers/docker-compose.yaml`
- `importers/requirements.txt`

E.g.

Start the relation engine:

```bash
make start-dev
```

The relation engine will be running at on the host at `localhost:5000`, or internally at `re_api:5000` in the docker
network.

When running against a local RE instance like this, you'll need to point the importer at `re_api:5000`. For a
deployment, you would want to use the appropriate url, e.g. `https://ci.kbase.us/services/relation_engine`.

Run the importer

```bash
python -m importers.data_sources.importer --auth-token admin_token --api-url http://localhost:5000 
```

Note that

- `--auth-token admin_token` matches the mocking setup, so must be used for evaluating import with the local test
  container
- `--api-url http://localhost:5000` matches the RE api running in a local container

Clearly, if running against a deployed RE API, the url to that service must be used, and a real admin token for that
environment must be used.

> TODO: describe that admin url...
>
>

### Dependencies

- make
- docker

### Environment Variables

