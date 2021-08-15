# RE Importers

This directory holds python modules that import data into ArangoDB.

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

An example invocation:

```shell
 IMPORTER=data_sources API_URL=http://re_api:5000 AUTH_TOKEN=admin_token make run-importer
```

In this example, the following required environment variables were 

- `IMPORTER` sets the specific importer module path element; the path to an importer should be `importers/IMPORTER/import.py` in the filesystem or `importers.IMPORTER.import` in Python.
- `RE_API_URL` sets the url to a running Relation Engine server
- `AUTH_TOKEN` sets a KBase auth token with enough privileges to import data into RE.

There are no default values for these environment variables; if they are omitted the import script will display an error message and exit.

The following optional parameters may also be used:

- `DATA_DIR` - the directory, relative to the repo root, in which the import files may be located; note that each importer will have one or more data files, so this is a directory path
  - defaults to the  `data` directory within the importer directory; e.g. `importers/data_sources/data`.
- `DRY_RUN` - if set to any value, will ensure that the importer does not actual save data in RE; rather it will just load and validate the data.
- `QUIET` - if set, the import script should suppress printing messages
- `VERBOSE` - if set, diagnostic output should be printed by the initial shell script, and perhaps the importer library.

> BTW the example command above will actually work if the test `docker-compose` has been run locally with `make start-dev`.

### 
