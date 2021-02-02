# Local UI Development

This directory contains tools and instructions for using the RE api in a local development context which allows close operation with other kbase services in a custom docker network.

This is enabled by running on the docker network `kbase-dev`.

The `docker-compose.yaml` in this directory takes care of that.

In addition, the configuration ensures that the entire schema set is loaded into Arango. This facilitates the usage of any collection during development. 

You'll need to take care of data loading.

## Build and start the image

From the repo root:

```bash
make start-ui-dev
```

## Install your data

This is just an example of how one can load data using an importer, with the simple example of `data_sources`.

Set up a Python environment:

```bash
virtualenv venv
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r dev-requirement.txt
```

Run your data importer. Each importer is an independent script, but they will probably follow a pattern similar to this example.

This example uses the `data_sources.json` import data to populate the `data_sources_nodes` collection.

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

## Point services to relation-engine-api

Within the `kbase-dev` docker network, the RE api is associated with the host `relation-engine-api`, and is bound to port `5000` as KBase services typically are.

By setting the base url for a client to `http://relation-engine-api:5000`

### Example taxonomy api

The taxonomy api can be run in a local-ui-dev mode as well, in which case it is configured with the correct RE api base url in the `docker-compose.yaml` file.

```bash
make start-ui-dev
```

### Example kbase-ui

Finally, if you have `kbase-ui` set up for local development, you can use the `dynamic-services` option to trap calls to a given dynamic service and route them within the local docker network.

Below is an example which allows one to have normal `CI` requests routed to the local taxonomy api, which itself talks to the local Re api.


```bash
make start dynamic-services="taxonomy-re-api"
```

E.g. I'm using the following url to probe the taxonomy api:

```bash
https://ci.kbase.us:443/dynserv/5a120b167a19b7b5fb87a11c7c35f704a225c156.taxonomy-re-api
```

The kbase-ui local dev proxy has added a reverse proxy which matches the above url (it ignores the git hash part the url).
