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
        self.assertEqual(resp['arangodb_status'], 'Connected and authorized.')
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
        resp = requests.put(url + '/api/documents?on_duplicate=error&overwrite=true&collection').json()
        self.assertTrue('Missing header' in resp['error'])
        resp = requests.put(
            url + '/api/documents?on_duplicate=error&overwrite=true&collection',
            headers={'Authorization': 'Bearer xyz'}
        ).json()
        self.assertTrue('Unauthorized' in resp['error'])

    def test_save_documents_with_create(self):
        resp = requests.put(
            url + '/api/documents',
            params={
                'overwrite': True,
                'collection': 'genes'
            },
            data='\n'.join([
                '{"name": "x", "_key": "1"}',
                '{"name": "y", "_key": "2"}',
                '{"name": "z", "_key": "3"}'
            ]),
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)
