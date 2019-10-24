# Relation engine client

A pip-installable Python client module for accessing the methods of the Relation Engine API.

## Installation

Install with pip:

```sh
pip install --extra-index-url https://pypi.anaconda.org/kbase/simple \
    releng-client==0.0.1
```

## Usage

### Initialize the client

Pass in the URL of the Relation Engine API server you want to use, which is most likely one of the following:

* `https://kbase.us/services/relation_engine_api`
* `https://ci.kbase.us/services/relation_engine_api`
* `https://appdev.kbase.us/services/relation_engine_api`

Additionally, pass in a KBase auth token you would like to use for access control and document saving permissions when making requests to the API.

```py
from relation_engine_client import REClient

re_client = REClient("https://ci.kbase.us/services/relation_engine_api", "xyz_my_token")
```

You can leave off the token if you want to do unauthenticated queries for public data.

### Basic calls

#### Stored queries

To execute a stored/named query, run the following:

```
re_client.stored_query(query_name, bind_vars, raise_not_found=False)
```

Where:

* `bind_vars`: required - dict - variables to use in the query.
* `raise_not_found`: options - bool - defaults to False - whether to raise an RENotFound error if 0 docs are returned.

### Saving documents

```
re_client.save_docs(collection_name, docs, on_duplicate='error', display_errors=False)
```

Where:

* `collection_name`: required - str - name of the collection you are saving documents into
* `docs`: required - list of dict or single dict - json-serializable list of
  documents to save to the above collection
* `on_duplicate`: optional - one of 'replace', 'update', 'ignore', or 'error' defaults to 'error' - action to take when we have a duplicate document by
    `_key` while saving.
* `display_errors`: optional - bool - defaults to False - whether to return
  error messages for every document that failed to save.

#### Admin queries

To run an ad-hoc admin query, run:

```py
re_client.admin_query(aql_query_text, bind_vars)
```

You must have an auth token set in the client with the RE admin role.

### Exceptions

A few different exceptions can be thrown from each method, which you can import:

```py
from relation_engine_client.exceptions import REServerError, RERequestError, RENotFound
```

#### REServerError

An error was thrown by the server (status code 500).

Access the `.resp.text` property on the error object to see the response body from the API, or simply print the error to debug.

#### RERequestError

There was an invalid or missing parameter or header in the request.

Access the `.resp.text` property on the error object to see the response body from the API, or simply print the error to debug.

#### RENotFound

The `raise_not_found` argument was set to `True` and no documents were found in the query.

Access the `.req_body` and `.req_params` properties of the error object to see the request data, or simply print the error to debug.

## Development
