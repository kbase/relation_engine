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


def create_test_docs(count):
    """Produce some test documents."""
    def doc(i):
        return '{"name": "name", "_key": "%s"}' % i
    return '\n'.join(doc(i) for i in range(0, count))


def create_test_edges(count):
    """Produce some test edges."""
    def doc(i):
        return '{"_from": "example_vertices/%s", "_to": "example_vertices/%s"}' % (i, i)
    return '\n'.join(doc(i) for i in range(0, count))


def save_test_docs(count, edges=False):
    if edges:
        docs = create_test_edges(count)
        collection = 'example_edges'
    else:
        docs = create_test_docs(count)
        collection = 'example_vertices'
    return requests.put(
        url + '/api/documents',
        params={'overwrite': True, 'collection': collection},
        data=docs,
        headers=headers
    ).json()


class TestApi(unittest.TestCase):

    def test_root(self):
        """Test root path for api."""
        resp = requests.get(url).json()
        self.assertEqual(resp['arangodb_status'], 'connected_authorized')
        self.assertTrue(resp['commit_hash'])
        self.assertTrue(resp['repo_url'])

    def test_update_specs(self):
        resp = requests.get(
            url + '/api/update_specs',
            headers={'Authorization': 'Bearer ' + auth_token}
        )
        resp_json = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp_json['status']))

    def test_list_views(self):
        resp = requests.get(url + '/api/views').json()
        self.assertTrue('list_all_documents_in_collection' in resp)

    def test_show_view(self):
        resp = requests.get(url + '/api/views/count_documents_in_collection').text
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

    def test_create_documents(self):
        """Test all valid cases for saving documents."""
        # Create
        resp = save_test_docs(3)
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_create_edges(self):
        """Test all valid cases for saving edges."""
        # Create
        resp = save_test_docs(3, edges=True)
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_update_documents(self):
        """Test updating existing documents."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'update', 'collection': 'example_vertices'},
            data=create_test_docs(3),
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_update_edge(self):
        """Test updating existing edge."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'update', 'collection': 'example_edges'},
            data=create_test_edges(3),
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_replace_documents(self):
        """Test replacing of existing documents."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'replace', 'collection': 'example_vertices'},
            data=create_test_docs(3),
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_save_documents_dupe_errors(self):
        """Test where we want to raise errors on duplicate documents."""
        save_test_docs(3)
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'error', 'collection': 'example_vertices', 'display_errors': '1'},
            data=create_test_docs(3),
            headers=headers
        ).json()
        self.assertEqual(resp['created'], 0)
        self.assertEqual(resp['errors'], 3)
        self.assertTrue(resp['details'])

    def test_save_documents_ignore_dupes(self):
        """Test ignoring duplicate, existing documents when saving."""
        resp = requests.put(
            url + '/api/documents',
            params={'on_duplicate': 'ignore', 'collection': 'example_vertices'},
            data=create_test_docs(3),
            headers=headers
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 3, 'error': False}
        self.assertEqual(resp, expected)

    def test_query(self):
        """Test a basic query that fetches some docs."""
        save_test_docs(3)
        resp = requests.post(
            url + '/api/query_results',
            params={'view': 'list_all_documents_in_collection'},
            data=json.dumps({'@collection': 'example_vertices'}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(len(resp['results']), 3)
        self.assertEqual(resp['count'], 3)
        self.assertEqual(resp['has_more'], False)
        self.assertEqual(resp['cursor_id'], None)
        self.assertTrue(resp['stats'])

    def test_query_with_cursor(self):
        """Test getting more data via a query cursor."""
        save_test_docs(count=200)
        resp = requests.post(
            url + '/api/query_results',
            params={'view': 'list_all_documents_in_collection'},
            data=json.dumps({'@collection': 'example_vertices'}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        cursor_id = resp['cursor_id']
        self.assertTrue(resp['cursor_id'])
        self.assertEqual(resp['has_more'], True)
        self.assertEqual(resp['count'], 200)
        self.assertTrue(len(resp['results']), 100)
        resp = requests.post(
            url + '/api/query_results',
            params={'cursor_id': cursor_id},
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertEqual(resp['count'], 200)
        self.assertEqual(resp['has_more'], False)
        self.assertEqual(resp['cursor_id'], None)
        self.assertTrue(len(resp['results']), 100)
        # Try to get the same cursor again
        resp = requests.post(
            url + '/api/query_results',
            params={'cursor_id': cursor_id},
            headers={'Authorization': 'Bearer ' + auth_token}
        ).json()
        self.assertTrue(resp['error'])
        self.assertEqual(resp['arango_message'], 'cursor not found')

    def test_query_no_name(self):
        resp = requests.post(
            url + '/api/query_results',
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
            url + '/api/query_results',
            params={'view': 'list_all_documents_in_collection'},
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
            url + '/api/query_results',
            params={'view': 'list_all_documents_in_collection'},
            data=json.dumps({'@collection': 123}),
            headers={
                'Authorization': 'Bearer ' + auth_token,
                'Content-Type': 'application/json'
            }
        ).json()
        self.assertEqual(resp['error'], 'ArangoDB server error.')
        self.assertTrue(resp['arango_message'])
