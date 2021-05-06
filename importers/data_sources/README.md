# Install data_sources dataset

The script and data within this directory allow one to load the _data sources_ into the RE database. The default RE base url is `http://localhost:5000`, as defined in `importers/utils/config.py`, which can be redefined with the environment variable `RES_API_URL`. 

This script has only been used in development thus far. In this case, the local RE Api container must be started via `make start-ui-dev`, as this starts the services with the `docker-compose.yaml` configuration located in `local-ui-dev`, which initializes all collections.

> This document describes a procedure for loading data locally, but does not claim provenance over production data provisioning. This script should work fine for initial load, and can be used for subsequent updates if the script is pointed at a data file which contains just the new documents.

## Procedure

Set up a Python environment:

At top level of repo:

```bash
python -m venv venv
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r dev-requirement.txt
```

> Tip: If you encounter an install error, you should first try updating pip:
> `pip install --upgrade pip`

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
