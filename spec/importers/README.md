# RE Importers

This directory holds python modules that import data into ArangoDB.

## Running importers

Configure importers through environment variables with the `RES_` prefix (which stands for Relation Engine Spec).

Global env vars:

* `RES_auth_token` - auth token to use when making requests to RE API - defaults to test value
* `RES_api_url` - url to use for the RE API - defaults to test value

### djornl

```py
RES_auth_token=admin_token \
RES_base_path=/path/to/djornl_data \
python -m importers.djornl.main
```
