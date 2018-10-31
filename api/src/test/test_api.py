"""
Simple integration tests on the API itself.

We make actual ajax requests to the running docker container.
"""
import unittest
import requests
import os

url = 'http://web:5000'
auth_token = os.environ.get('KBASE_TEST_AUTH_TOKEN', '')


class TestApi(unittest.TestCase):

    def test_root(self):
        """Test root path for api."""
        resp = requests.get(url).json()
        self.assertEqual(resp['arangodb_status'], 'connected_authorized')
        self.assertEqual(resp['docs'], '/docs')
        self.assertTrue(resp['commit_hash'])
        self.assertTrue(resp['repo_url'])

    def test_list_views(self):
        resp = requests.get(url + '/api/views?show_source=1').json()
        self.assertTrue(len(resp['names']) > 0)
        for name in resp['names']:
            self.assertTrue(resp['content'][name])
        resp = requests.get(url + '/api/views').json()
        self.assertTrue(len(resp['names']) > 0)
        self.assertFalse(resp.get('content'))

    def test_list_schemas(self):
        resp = requests.get(url + '/api/schemas?show_source=1').json()
        self.assertTrue(len(resp['names']) > 0)
        for name in resp['names']:
            self.assertTrue(resp['content'][name])
        resp = requests.get(url + '/api/views').json()
        self.assertTrue(len(resp['names']) > 0)
        self.assertFalse(resp.get('content'))

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

    def test_save_documents_no_keys(self):
        """Test the case where some documents fail against their schema."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'ignore', 'collection': 'taxon'},
            data='{"name": "x"}\n{"name": "y"}',
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertEqual(resp['error'], "'_key' is a required property")
        self.assertEqual(resp['instance'], {'name': 'x'})
        self.assertTrue(resp['schema'])
        self.assertEqual(resp['validator'], 'required')
        self.assertEqual(resp['validator_value'], ['_key', 'name'])

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
            params={'collection': 'taxon'},
            data='\n',
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertTrue('Unable to parse' in resp['error'])
        self.assertEqual(resp['pos'], 1)
        self.assertEqual(resp['source_json'], '\n')

    def test_save_documents(self):
        """Test all valid cases for saving documents."""
        example_data = '\n'.join([
            '{"name": "x", "_key": "1"}',
            '{"name": "y", "_key": "2"}',
            '{"name": "z", "_key": "3"}'
        ])
        headers = {'Authorization': 'Bearer ' + auth_token}
        # Create
        resp = requests.put(
            url + '/api/documents',
            params={'overwrite': True, 'collection': 'taxon'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # update on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'update', 'collection': 'taxon'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # replace on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'replace', 'collection': 'taxon'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # error on duplicate
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'error', 'collection': 'taxon'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 3, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
        # ignore duplicates
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'ignore', 'collection': 'taxon'},
            data=example_data,
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 3, 'error': False}
        self.assertEqual(resp, expected)

    @unittest.skip('TODO')
    def test_query(self):
        resp = requests.post(
            url + '/api/query',
            params={'view': 'example'},
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        print('!', resp)
        pass
        # TODO valid query
        # TODO missing query name
        # TODO missing bind variables
        # TODO bind variable is invalid
