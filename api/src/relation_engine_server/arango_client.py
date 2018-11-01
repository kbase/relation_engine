"""
Make ajax requests to the ArangoDB server.
"""
import requests
import json
import os

db_url = os.environ.get('DB_URL', 'http://localhost:8529')
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', 'password')


def server_status():
    """Get the status of our connection and authorization to the ArangoDB server."""
    try:
        resp = requests.get(db_url + '/_api/endpoint', auth=(db_user, db_pass))
    except requests.exceptions.ConnectionError:
        return 'no_connection'
    if resp.ok:
        return 'connected_authorized'
    elif resp.status_code == 401:
        return 'unauthorized'
    else:
        return 'unknown_failure'


def run_query(query_text=None, cursor_id=None, bind_vars={}):
    """Run a query using the arangodb http api. Can return a cursor to get more results."""
    url = db_url + '/_api/cursor'
    req_json = {
        'batchSize': 100,
        'memoryLimit': 16000000000,  # 16gb
        'count': True,
    }
    if cursor_id:
        url += '/' + cursor_id
    else:
        req_json['bindVars'] = bind_vars
        req_json['query'] = query_text

    resp = requests.post(
        url,
        data=json.dumps(req_json),
        auth=(db_user, db_pass)
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


def bulk_import(file_path, query):
    """Make a generic arango post request."""
    with open(file_path, 'rb') as file_desc:
        resp = requests.post(
            db_url + '/_api/import',
            data=file_desc,
            auth=(db_user, db_pass),
            params=query
        )
    if not resp.ok:
        raise ArangoServerError(resp.text)
    return resp.text


class ArangoServerError(Exception):
    """A request to the ArangoDB server has failed (non-2xx)."""

    def __init__(self, resp_text):
        self.resp_text = resp_text
        self.resp_json = json.loads(resp_text)

    def __str__(self):
        return 'ArangoDB server error.'
