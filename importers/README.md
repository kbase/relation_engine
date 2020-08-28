# RE Importers

This directory holds python modules that import data into ArangoDB.

## Running importers

Configure importers through environment variables with the `RES_` prefix (which stands for Relation Engine Spec).

Global env vars:

* `RES_AUTH_TOKEN` - auth token to use when making requests to RE API - defaults to test value
* `RES_API_URL` - url to use for the RE API - defaults to test value

### djornl

```sh
RES_ROOT_DATA_PATH=/path/to/djornl_data \
python -m importers.djornl.parser
```
