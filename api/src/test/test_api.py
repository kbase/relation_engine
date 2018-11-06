"""
Simple integration tests on the API itself.

We make actual ajax requests to the running docker container.
"""
import unittest
import requests
import json
import os

url = os.environ.get('TEST_URL', 'http://web:5000')
auth_token = os.environ.get('KBASE_TEST_AUTH_TOKEN', '')
headers = {'Authorization': 'Bearer ' + auth_token}
example_data = '\n'.join([
    '{"name": "x", "_key": "1"}',
    '{"name": "y", "_key": "2"}',
    '{"name": "z", "_key": "3"}'
])


def create_docs():
    """Generic function to create a few docs -- reused in a couple places in the tests."""
    return requests.put(
        url + '/api/documents',
        params={'overwrite': True, 'collection': 'example_vertices'},
        data=example_data,
        headers=headers
    ).json()


class TestApi(unittest.TestCase):

    def test_root(self):
        """Test root path for api."""
        resp = requests.get(url).json()
        self.assertEqual(resp['arangodb_status'], 'connected_authorized')
        self.assertTrue(resp['commit_hash'])
        self.assertTrue(resp['repo_url'])

    def test_list_views(self):
        resp = requests.get(url + '/api/views').json()
        self.assertTrue('example' in resp)

    def test_show_view(self):
        resp = requests.get(url + '/api/views/example').text
        self.assertTrue('Return count of documents' in resp)

    def test_list_schemas(self):
        resp = requests.get(url + '/api/schemas').json()
        self.assertTrue('example_vertices' in resp['vertices'])
        self.assertTrue('example_edges' in resp['edges'])
        self.assertFalse('error' in resp)
        self.assertTrue(len(resp))

    def test_show_schema(self):
        resp = requests.get(url + '/api/schemas/example_edges').text
        self.assertTrue('_from' in resp)
        resp = requests.get(url + '/api/schemas/example_vertices').text
        self.assertTrue('_key' in resp)

    def test_save_documents_no_auth(self):
        # Missing bearer
        resp = requests.put(url + '/api/documents?on_duplicate=error&overwrite=true&collection').json()
        self.assertTrue('Missing header' in resp['error'])
        # Invalid bearer
        resp = requests.put(
            url + '/api/documents?on_duplicate=error&overwrite=true&collection',
            headers={'Authorization': 'Bearer xyz'}
        ).json()
        self.assertTrue('Unauthorized' in resp['error'])

    def test_save_documents_invalid_schema(self):
        """Test the case where some documents fail against their schema."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'ignore', 'collection': 'example_vertices'},
            data='{"name": "x"}\n{"name": "y"}',
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertEqual(resp['error'], "'_key' is a required property")
        self.assertEqual(resp['instance'], {'name': 'x'})
        self.assertTrue(resp['schema'])
        self.assertEqual(resp['validator'], 'required')
        self.assertEqual(resp['validator_value'], ['_key'])

    def test_save_documents_missing_schema(self):
        """Test the case where the collection/schema does not exist."""
        resp = requests.put(
            url + '/api/documents',
            params={'collection': 'xyzabc'},
            data='',
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertTrue('Schema does not exist' in resp['error'])

    def test_save_documents_invalid_json(self):
        resp = requests.put(
            url + '/api/documents',
            params={'collection': 'example_vertices'},
            data='\n',
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertTrue('Unable to parse' in resp['error'])
        self.assertEqual(resp['pos'], 1)
        self.assertEqual(resp['source_json'], '\n')

    def test_save_documents_and_query(self):
        """Test all valid cases for saving documents."""
        # Create
        resp = create_docs()
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # update on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'update', 'collection': 'example_vertices'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # replace on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'replace', 'collection': 'example_vertices'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # error on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'error', 'collection': 'example_vertices'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 3, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # ignore duplicates
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'ignore', 'collection': 'example_vertices'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 3, 'error': False}
        self.assertEqual(resp, expected)

    def test_query(self):
        """Test a query that fetches some docs."""
        create_docs()
        resp = requests.post(
            url + '/api/query',
            params={'view': 'example'},
            data=json.dumps({'@collection': 'example_vertices'}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(resp['results'], [3])
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['has_more'], False)
        self.assertEqual(resp['cursor_id'], None)
        self.assertTrue(resp['stats'])

    def test_query_no_name(self):
        resp = requests.post(
            url + '/api/query',
            params={'view': 'nonexistent'},
            data=json.dumps({'@collection': 'example_vertices'}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(resp['error'], 'View does not exist.')
        self.assertEqual(resp['name'], 'nonexistent')

    def test_query_missing_bind_var(self):
        resp = requests.post(
            url + '/api/query',
            params={'view': 'example'},
            data=json.dumps({'xyz': 'example_vertices'}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(resp['error'], 'ArangoDB server error.')
        self.assertTrue(resp['arango_message'])

    def test_query_incorrect_collection(self):
        resp = requests.post(
            url + '/api/query',
            params={'view': 'example'},
            data=json.dumps({'@collection': 123}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(resp['error'], 'ArangoDB server error.')
        self.assertTrue(resp['arango_message'])
