"""
Make ajax requests to the ArangoDB server.
"""
import requests
import json

from .config import get_config


def server_status():
    """Get the status of our connection and authorization to the ArangoDB server."""
    config = get_config()
    try:
        resp = requests.get(config['db_url'] + '/_api/endpoint', auth=(config['db_user'], config['db_pass']))
    except requests.exceptions.ConnectionError:
        return 'no_connection'
    if resp.ok:
        return 'connected_authorized'
    elif resp.status_code == 401:
        return 'unauthorized'
    else:
        return 'unknown_failure'


def run_query(query_text=None, cursor_id=None, bind_vars=None, batch_size=100):
    """Run a query using the arangodb http api. Can return a cursor to get more results."""
    config = get_config()
    url = config['db_url'] + '/_api/cursor'
    req_json = {
        'batchSize': min(5000, batch_size),
        'memoryLimit': 16000000000  # 16gb
    }
    if cursor_id:
        method = 'PUT'
        url += '/' + cursor_id
    else:
        method = 'POST'
        req_json['count'] = True
        req_json['query'] = query_text
        if bind_vars:
            req_json['bindVars'] = bind_vars
    # Initialize the readonly user
    _init_readonly_user()
    # Run the query as the readonly user
    resp = requests.request(
        method,
        url,
        data=json.dumps(req_json),
        auth=(config['db_readonly_user'], config['db_readonly_pass'])
    )
    if not resp.ok:
        raise ArangoServerError(resp.text)
    resp_json = resp.json()
    if resp_json['error']:
        raise ArangoServerError(resp.text)
    return {
        'results': resp_json['result'],
        'count': resp_json['count'],
        'has_more': resp_json['hasMore'],
        'cursor_id': resp_json.get('id'),
        'stats': resp_json['extra']['stats']
    }


def init_collections(schemas):
    """Initialize any uninitialized collections in the database from a set of schemas."""
    edges = schemas['edges']
    vertices = schemas['vertices']
    for edge_name in edges:
        create_collection(edge_name, is_edge=True)
    for vertex_name in vertices:
        create_collection(vertex_name, is_edge=False)


def create_collection(name, is_edge):
    """
    Create a single collection by name using some basic defaults.
    We ignore duplicates. For any other server error, an exception is thrown.
    """
    config = get_config()
    url = config['db_url'] + '/_api/collection'
    # collection types:
    #   2 is a document collection
    #   3 is an edge collection
    collection_type = 3 if is_edge else 2
    data = json.dumps({
        'keyOptions': {'allowUserKeys': True},
        'name': name,
        'type': collection_type
    })
    resp = requests.post(url, data, auth=(config['db_user'], config['db_pass'])).json()
    if resp['error']:
        if 'duplicate' not in resp['errorMessage']:
            # Unable to create a collection
            raise ArangoServerError(resp.text)


def import_from_file(file_path, query):
    """Make a generic arango post request."""
    config = get_config()
    with open(file_path, 'rb') as file_desc:
        resp = requests.post(
            config['db_url'] + '/_api/import',
            data=file_desc,
            auth=(config['db_user'], config['db_pass']),
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
    config = get_config()
    user = config['db_readonly_user']
    # Check if the user exists, in which case this is a no-op
    resp = requests.get(
        config['db_url'] + '/_api/user/' + user,
        auth=(config['db_user'], config['db_pass'])
    )
    if resp.status_code == 200:
        return
    # Create the user
    resp = requests.post(
        config['db_url'] + '/_api/user',
        data=json.dumps({'user': user, 'passwd': config['db_readonly_user']}),
        auth=(config['db_user'], config['db_pass'])
    )
    if resp.status_code != 201:
        raise ArangoServerError(resp.text)
    # Grant read access to the current database
    resp = requests.put(
        config['db_url'] + '/_api/user/' + user + '/database/' + config['db_name'],
        data='{"grant": "ro"}',
        auth=(config['db_user'], config['db_pass'])
    )
    if resp.status_code != 200:
        raise ArangoServerError(resp.text)


class ArangoServerError(Exception):
    """A request to the ArangoDB server has failed (non-2xx)."""

    def __init__(self, resp_text):
        self.resp_text = resp_text
        self.resp_json = json.loads(resp_text)

    def __str__(self):
        return 'ArangoDB server error.'
