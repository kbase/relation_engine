"""
Make ajax requests to the ArangoDB server.
"""
import os
import requests
import json
import glob
import yaml

from .config import get_config

_CONF = get_config()


def server_status():
    """Get the status of our connection and authorization to the ArangoDB server."""
    try:
        resp = requests.get(_CONF['db_url'] + '/_api/endpoint', auth=(_CONF['db_user'], _CONF['db_pass']))
    except requests.exceptions.ConnectionError:
        return 'no_connection'
    if resp.ok:
        return 'connected_authorized'
    elif resp.status_code == 401:
        return 'unauthorized'
    else:
        return 'unknown_failure'


def run_query(query_text=None, cursor_id=None, bind_vars=None, batch_size=10000, full_count=False):
    """Run a query using the arangodb http api. Can return a cursor to get more results."""
    url = _CONF['api_url'] + '/cursor'
    req_json = {
        'batchSize': min(5000, batch_size),
        'memoryLimit': 16000000000,  # 16gb
    }
    if cursor_id:
        method = 'PUT'
        url += '/' + cursor_id
    else:
        method = 'POST'
        req_json['count'] = True
        req_json['query'] = query_text
        if full_count:
            req_json['options'] = {'fullCount': True}
        if bind_vars:
            req_json['bindVars'] = bind_vars
    # Initialize the readonly user
    _init_readonly_user()
    # Run the query as the readonly user
    resp = requests.request(
        method,
        url,
        data=json.dumps(req_json),
        auth=(_CONF['db_readonly_user'], _CONF['db_readonly_pass'])
    )
    resp_json = resp.json()
    if not resp.ok or resp_json['error']:
        raise ArangoServerError(resp.text)
    return {
        'results': resp_json['result'],
        'count': resp_json['count'],
        'has_more': resp_json['hasMore'],
        'cursor_id': resp_json.get('id'),
        'stats': resp_json['extra']['stats']
    }


def init_collections():
    """Initialize any uninitialized collections in the database from a set of schemas."""
    pattern = os.path.join(_CONF['spec_paths']['schemas'], '**', '*.yaml')
    for path in glob.iglob(pattern):
        coll_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = yaml.safe_load(fd)
        create_collection(coll_name, config)


def create_collection(name, config):
    """
    Create a single collection by name using some basic defaults.
    We ignore duplicates. For any other server error, an exception is thrown.
    Shard the new collection based on the number of db nodes (10 shards for each).
    """
    is_edge = config['type'] == 'edge'
    num_shards = os.environ.get('SHARD_COUNT', 30)
    url = _CONF['api_url'] + '/collection'
    # collection types:
    #   2 is a document collection
    #   3 is an edge collection
    collection_type = 3 if is_edge else 2
    print(f"Creating collection {name} (edge: {is_edge})")
    data = json.dumps({
        'keyOptions': {'allowUserKeys': True},
        'name': name,
        'type': collection_type,
        'numberOfShards': num_shards
    })
    resp = requests.post(url, data, auth=(_CONF['db_user'], _CONF['db_pass']))
    resp_json = resp.json()
    if not resp.ok:
        if 'duplicate' not in resp_json['errorMessage']:
            # Unable to create a collection
            raise ArangoServerError(resp.text)
    if config.get('indexes'):
        _create_indexes(name, config)


def _create_indexes(coll_name, config):
    """Create indexes for a collection"""
    url = _CONF['api_url'] + '/index'
    for idx_conf in config['indexes']:
        idx_type = idx_conf['type']
        idx_url = url + '#' + idx_type
        idx_conf['type'] = idx_type
        resp = requests.post(
            idx_url,
            params={'collection': coll_name},
            data=json.dumps(idx_conf),
            auth=(_CONF['db_user'], _CONF['db_pass'])
        )
        if not resp.ok:
            raise RuntimeError(resp.text)


def import_from_file(file_path, query):
    """Import documents from a file."""
    with open(file_path, 'rb') as file_desc:
        resp = requests.post(
            _CONF['api_url'] + '/import',
            data=file_desc,
            auth=(_CONF['db_user'], _CONF['db_pass']),
            params=query
        )
    if not resp.ok:
        raise ArangoServerError(resp.text)
    return resp.text


def _init_readonly_user():
    """
    Using the admin user, initialize an admin readonly user for use with ad-hoc queries.

    If the user cannot be created, we raise an ArangoServerError
    If the user already exists, or is successfully created, we return None and do not raise.
    """
    user = _CONF['db_readonly_user']
    # Check if the user exists, in which case this is a no-op
    resp = requests.get(
        _CONF['api_url'] + '/user/' + user,
        auth=(_CONF['db_user'], _CONF['db_pass'])
    )
    if resp.status_code == 200:
        return
    # Create the user
    resp = requests.post(
        _CONF['api_url'] + '/user',
        data=json.dumps({'user': user, 'passwd': _CONF['db_readonly_user']}),
        auth=(_CONF['db_user'], _CONF['db_pass'])
    )
    if resp.status_code != 201:
        raise ArangoServerError(resp.text)
    db_grant_path = _CONF['api_url'] + '/user/' + user + '/database/' + _CONF['db_name']
    # Grant read access to the current database
    resp = requests.put(
        db_grant_path,
        data='{"grant": "ro"}',
        auth=(_CONF['db_user'], _CONF['db_pass'])
    )
    if resp.status_code != 200:
        raise ArangoServerError(resp.text)
    # Grant read access to all collections
    resp = requests.put(
        db_grant_path + '/*',
        data='{"grant": "ro"}',
        auth=(_CONF['db_user'], _CONF['db_pass'])
    )
    if not resp.ok:
        raise ArangoServerError(resp.text)


class ArangoServerError(Exception):
    """A request to the ArangoDB server has failed (non-2xx)."""

    def __init__(self, resp_text):
        self.resp_text = resp_text
        self.resp_json = json.loads(resp_text)

    def __str__(self):
        return 'ArangoDB server error.'
