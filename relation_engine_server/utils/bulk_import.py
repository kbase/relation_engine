import time
import os
import tempfile
import flask
import json
import hashlib

from relation_engine_server.utils import json_validation
from . import spec_loader
from .arango_client import import_from_file


def bulk_import(query_params):
    """
    Stream lines of JSON from a request body, validating each one against a
    schema, then write them into a temporary file that can be passed into the
    arango client.
    """
    schema = spec_loader.get_schema(query_params['collection'])
    # We can't use a context manager here
    # We need to close the file to have the file contents readable
    #  and we need to prevent deletion of the temp file on close (default behavior of tempfiles)
    temp_fd = tempfile.NamedTemporaryFile(mode='a', delete=False)
    try:
        # Stream request data line-by-line
        # Parse each line to json, validate the schema, and write to a file
        for line in flask.request.stream:
            json_line = json.loads(line)
            json_validation.Validator(schema['schema']).validate(json_line)
            json_line = _write_edge_key(json_line)
            json_line['updated_at'] = int(time.time() * 1000)
            temp_fd.write(json.dumps(json_line) + '\n')
        temp_fd.close()
        resp_json = import_from_file(temp_fd.name, query_params)
    finally:
        # Always remove the temp file
        os.remove(temp_fd.name)
    return resp_json


def _write_edge_key(json_line):
    """For edges, we want a deterministic key so there are no duplicates."""
    if "_key" not in json_line and "_from" in json_line and "_to" in json_line:
        json_line['_key'] = hashlib.blake2b(
            json_line["_from"].encode() + json_line["_to"].encode(), digest_size=8
        ).hexdigest()
    return json_line
