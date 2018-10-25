"""
Make ajax requests to the ArangoDB server
"""
import json
import requests
import os


db_url = os.environ.get('DB_URL', 'http://localhost:8529')
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', 'password')


test_query = """
for doc in @@collection
  collect with count into length
  return length
"""


def make_arango_request(path, data):
    data = {'query': test_query, 'bindVars': {'@collection': 'genes'}}
    print('-' * 80)
    print(db_url + path)
    print(data)
    resp = requests.post(db_url + path, data=json.dumps(data), auth=(db_user, db_pass))
    return resp.text
