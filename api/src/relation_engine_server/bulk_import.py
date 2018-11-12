import tempfile
import flask
import json
import jsonschema
import hashlib

from . import spec_loader, arango_client


def bulk_import(query_params):
    """
    Stream lines of JSON from a request body, validating each one against a
    schema, then write them into a temporary file that can be passed into the
    arango client.
    """
    schema = spec_loader.get_schema(query_params['collection'])
    temp_fd = tempfile.NamedTemporaryFile()
    with open(temp_fd.name, 'a') as fd:
        for line in flask.request.stream:
            json_line = json.loads(line)
            jsonschema.validate(json_line, schema)
            json_line = _write_edge_key(json_line)
            fd.write(json.dumps(json_line) + '\n')
    resp_text = arango_client.bulk_import(temp_fd.name, query_params)
    temp_fd.close()  # Also deletes the file
    return resp_text


def _write_edge_key(json_line):
    """For edges, we want a deterministic key so there are no duplicates."""
    if "_key" not in json_line and "_from" in json_line and "_to" in json_line:
        json_line['_key'] = hashlib.blake2b(
            json_line["_from"].encode() + json_line["_to"].encode(), digest_size=8
        ).hexdigest()
    return json_line
