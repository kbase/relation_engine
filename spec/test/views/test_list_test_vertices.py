import json
import unittest
import requests

_API_URL = 'http://re_api:5000/api'
_VERSION = 'v1'
_QUERY_URL = f'{_API_URL}/{_VERSION}/query_results?view=list_test_vertices'


def create_test_docs(docs):
    body = '\n'.join([json.dumps(d) for d in docs])
    return requests.put(
        f'{_API_URL}/{_VERSION}/documents',
        params={'overwrite': True, 'collection': 'test_vertex'},
        data=body,
        headers={'Authorization': 'admin_token'}
    ).json()


class TestListTestVertices(unittest.TestCase):

    def test_valid(self):
        """Test a valid query."""
        print(create_test_docs([
            {'is_public': True, '_key': 'a', 'ws_id': 10},  # public access
            {'is_public': False, '_key': 'b', 'ws_id': 1},  # private access
            {'is_public': False, '_key': 'c', 'ws_id': 99}  # no access
        ]))
        resp = requests.post(
            _QUERY_URL,
            headers={'Authorization': 'valid_token'}  # gives access to workspaces [1,2,3]
        ).json()
        self.assertEqual(resp['count'], 2)
        # 'c' is inaccessible
        self.assertEqual([r['_key'] for r in resp['results']], ['a', 'b'])

    def test_no_auth(self):
        """Test with blank auth."""
        print(create_test_docs([
            {'is_public': True, '_key': 'a', 'ws_id': 10},  # public access
            {'is_public': False, '_key': 'b', 'ws_id': 1},  # private access
            {'is_public': False, '_key': 'c', 'ws_id': 99}  # no access
        ]))
        resp = requests.post(_QUERY_URL).json()
        self.assertEqual(resp['count'], 1)
        # 'b' and 'c' are inaccessible
        self.assertEqual([r['_key'] for r in resp['results']], ['a'])
