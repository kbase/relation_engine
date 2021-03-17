# Local UI Development

This directory contains tools and instructions for using the RE api in a local development context which allows close operation with other kbase services in a custom docker network.

This is enabled by running on the docker network `kbase-dev`.

The `docker-compose.yaml` in this directory takes care of that.

In addition, the configuration ensures that the entire schema set is loaded into Arango. This facilitates the usage of any collection during development.

You'll need to take care of data loading.

## Build and start the image

From the repo root:

```bash
make start-dev
```

## Install your data

At present, only instructions for installing the `data_sources` are provided. Clearly a complete local workflow would involve installing major chunks of the RE graph.

see [importers/data_sources/README.md](../importers/data_sources/README.md#procedure).

## Point services to relation-engine-api

Within the `kbase-dev` docker network, the RE api is associated with the host `relation-engine-api`, and is bound to port `5000` as KBase services typically are.

### Example: Taxonomy RE API

The [Taxonomy RE API](https://github.com/kbase/taxonomy_re_api) can be run in a _local-ui-dev mode_ as well, in which case it is configured with the correct RE api base url in the `docker-compose.yaml` file.

```bash
git clone https://github.com/kbase/taxonomy_re_api
cd taxonomy_re_api
make start-ui-dev
```

### Example kbase-ui

Finally, if you have `kbase-ui` set up for local development, you can use the `dynamic-services` option to trap calls to a given dynamic service and route them within the local docker network.

Below is an example which allows one to have normal `CI` requests routed to the local taxonomy api, which itself talks to the local Re api.

First route ci.kbase.us locally:

```bash
sudo vi /etc/hosts
```

add 

```bash
127.0.0.1       ci.kbase.us
```

Then start kbase-ui, configuring the development proxy to route requests normally targeted at `https://ci.kbase.us:443/dynserv/5a120b167a19b7b5fb87a11c7c35f704a225c156.taxonomy-re-api` to `http://taxonomy-re-api:5000`.

```bash
make start dynamic-services="taxonomy-re-api"
```

Note that the Taxonomy RE Api service will not be fully functional unless the entire graph enabling taxonomy is loaded.

However, this workflow is still useful for probing Taxonomy RE API methods. 

E.g. I'm using the following url to probe the taxonomy api, which should return the data source definition for "ncbi_taxonomy".

```bash
curl -X POST https://ci.kbase.us:443/dynserv/5a120b167a19b7b5fb87a11c7c35f704a225c156.taxonomy-re-api \
    -H 'Authorization: <YOUR TOKEN HERE>>' \
    -d '{
	"params": [{"ns": ["ncbi_taxonomy"]}],
	"method": "taxonomy_re_api.get_data_sources",
	"version": "1.1",
	"id": "x"
}'```

```bash
https://ci.kbase.us:443/dynserv/5a120b167a19b7b5fb87a11c7c35f704a225c156.taxonomy-re-api
```

The kbase-ui local dev proxy has added a reverse proxy which matches the above url (it ignores the git hash part the url).
