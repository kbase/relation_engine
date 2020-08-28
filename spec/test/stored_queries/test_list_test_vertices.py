import unittest
import requests

from spec.test.helpers import create_test_docs, get_config, check_spec_test_env

_CONF = get_config()
_QUERY_URL = _CONF['re_api_url'] + '/api/v1/query_results?view=list_test_vertices'


class TestListTestVertices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        check_spec_test_env()

    def test_valid(self):
        """Test a valid query."""
        docs_created = create_test_docs(
            'test_vertex',
            [
                {'is_public': True, '_key': 'a', 'ws_id': 10},  # public access
                {'is_public': False, '_key': 'b', 'ws_id': 1},  # private access
                {'is_public': False, '_key': 'c', 'ws_id': 99}  # no access
            ]
        )
        self.assertEqual(
            docs_created.json(),
            {'created': 3, 'details': [], 'empty': 0, 'error': False, 'errors': 0, 'ignored': 0, 'updated': 0},
        )
        resp = requests.post(
            _QUERY_URL,
            headers={'Authorization': 'valid_token'}  # gives access to workspaces [1,2,3]
        ).json()
        self.assertEqual(resp['count'], 2)
        # 'c' is inaccessible
        self.assertEqual({r['_key'] for r in resp['results']}, {'a', 'b'})

    def test_no_auth(self):
        """Test with blank auth."""
        docs_created = create_test_docs(
            'test_vertex',
            [
                {'is_public': True, '_key': 'a', 'ws_id': 10},  # public access
                {'is_public': False, '_key': 'b', 'ws_id': 1},  # private access
                {'is_public': False, '_key': 'c', 'ws_id': 99}  # no access
            ]
        )
        self.assertEqual(
            docs_created.json(),
            {'created': 3, 'details': [], 'empty': 0, 'error': False, 'errors': 0, 'ignored': 0, 'updated': 0},
        )
        resp = requests.post(_QUERY_URL).json()
        self.assertEqual(resp['count'], 1)
        # 'b' and 'c' are inaccessible
        self.assertEqual([r['_key'] for r in resp['results']], ['a'])
