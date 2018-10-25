"""
Make ajax requests to the ArangoDB server
"""
import json
import requests
import os


db_url = os.environ.get('DB_URL', 'http://localhost:8529')
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', 'password')


def make_arango_request(path, data):
    """Make a generic arango request."""
    resp = requests.post(db_url + path, data=json.dumps(data), auth=(db_user, db_pass))
    return resp.text
