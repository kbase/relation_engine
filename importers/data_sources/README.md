# Install data_sources dataset

The script and data within this directory allow one to load the _data sources_ into the RE database via the RE API. The default RE API base url is `http://localhost:5000`, as defined in `importers/utils/config.py`, which can be redefined with the environment variable `RE_API_URL`.

A set of data files is located in the `importers/data_sources/data` directory, which will be used unless the `RES_ROOT_DATA_PATH` environment variable is set before calling the importer script.

This script has only been used in development thus far. In this case, the local RE API container must be started via `make start-ui-dev`, as this starts the services with the `docker-compose.yaml` configuration located in `local-ui-dev`, which initializes all collections.

> This document describes a procedure for loading data locally, but does not claim provenance over production data provisioning. This script should work fine for initial load, and can be used for subsequent updates if the script is pointed at a data file which contains just the new documents.

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

Run the data importer. Each importer is an independent script, but they will probably follow a pattern similar to this example.

The script uses the `data_sources.json` import data to populate the `data_sources_nodes` collection.

Here we install from the default built-in data source, in dry-run mode, which prevents actual Arango changes:

```bash
(venv) % python -m importers.data_sources.importer --dry-run    
[importer] Taking data dir from default
[importer] data_dir: "/Users/erikpearson/work/kbase/sprints/2020Q4/relation_engine/importers/data_sources/data"
[importer] Dry run completed successfully
[importer] done
```

And here we use an external data source, in this case located in the `temp` directory of the current user's home directory, which is typically available in the `$HOME` environment variable.

```bash
(venv) % RES_ROOT_DATA_PATH="${HOME}/temp" python -m importers.data_sources.importer --dry-run
[importer] Taking data dir from environment variable "RES_ROOT_DATA_PATH"
[importer] data_dir: "/Users/erikpearson/work/kbase/sprints/2020Q4/relation_engine/_temp"
[importer] Dry run completed successfully
[importer] done
```

Finally, to import the data, simply remove `--dry-run`.

```bash
(venv) % python -m importers.data_sources.importer
[importer] Taking data dir from default
[importer] data_dir: "/Users/erikpearson/work/kbase/sprints/2020Q4/relation_engine/importers/data_sources/data"
[importer] Saved docs to collection data_sources_nodes!
[importer]     created: 6
[importer]     empty: 0
[importer]     error: False
[importer]     errors: 0
[importer]     ignored: 0
[importer]     updated: 0
[importer] done 
```


## Import via Docker container

Generally this is the preferred method for running the importer.

A container is run, the importer is invoked against a running instance of the Relation Engine API.

E.g. 

Start the relation engine:

```bash
make start-dev
```

The relation engine will be running at on the host at `localhost:5000`, or internally at `re_api:5000` in the docker network.

When running against a local RE instance like this, you'll need to point the importer at `re_api:5000`. For a deployment, you would want to use the appropriate url, e.g. `https://ci.kbase.us/services/relation_engine`.

Run the importer 

```bash
python -m importers.data_sources.importer --auth-token admin_token --api-url http://localhost:5000 
```

Note that 

- `--auth-token admin_token` matches the mocking setup, so must be used for evaluating import with the local test container
- `--api-url http://localhost:5000` matches the RE api running in a local container

Clearly, if running against a deployed RE API, the url to that service must be used, and a real admin token for that environment must be used.

> TODO: describe that admin url...
> 
> 

### Dependencies

- make
- docker

### Environment Variables

