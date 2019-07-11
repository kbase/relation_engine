"""
Simple integration tests on the API itself.

We make actual ajax requests to the running docker container.
"""
import unittest
import requests
import json
import os

# Use the mock auth tokens
NON_ADMIN_TOKEN = 'non_admin_token'
ADMIN_TOKEN = 'admin_token'
INVALID_TOKEN = 'invalid_token'

# Use the docker-compose url of the running flask server
URL = os.environ.get('TEST_URL', 'http://localhost:5000')
VERSION = 'v1'
API_URL = '/'.join([URL, 'api', VERSION])

HEADERS_NON_ADMIN = {'Authorization': 'Bearer ' + NON_ADMIN_TOKEN, 'Content-Type': 'application/json'}
HEADERS_ADMIN = {'Authorization': 'Bearer ' + ADMIN_TOKEN, 'Content-Type': 'application/json'}


def create_test_docs(count):
    """Produce some test documents."""
    def doc(i):
        return '{"name": "name", "_key": "%s", "is_public": true}' % i
    return '\n'.join(doc(i) for i in range(0, count))


def create_test_edges(count):
    """Produce some test edges."""
    def doc(i):
        return '{"_from": "test_vertex/%s", "_to": "test_vertex/%s"}' % (i, i)
    return '\n'.join(doc(i) for i in range(0, count))


def save_test_docs(count, edges=False):
    if edges:
        docs = create_test_edges(count)
        collection = 'test_edge'
    else:
        docs = create_test_docs(count)
        collection = 'test_vertex'
    return requests.put(
        API_URL + '/documents',
        params={'overwrite': True, 'collection': collection},
        data=docs,
        headers=HEADERS_ADMIN
    ).json()


class TestApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize collections before running any tests
        resp = requests.put(
            API_URL + '/specs',
            headers=HEADERS_ADMIN,
            params={'init_collections': '1'}
        )
        print('update_specs response', resp.text)

    def test_root(self):
        """Test root path for api."""
        resp = requests.get(URL + '/').json()
        self.assertEqual(resp['arangodb_status'], 'connected_authorized')
        self.assertTrue(resp['commit_hash'])
        self.assertTrue(resp['repo_url'])

    def test_config(self):
        """Test config fetch."""
        resp = requests.get(API_URL + '/config').json()
        self.assertTrue(len(resp['auth_url']))
        self.assertTrue(len(resp['workspace_url']))
        self.assertTrue(len(resp['kbase_endpoint']))
        self.assertTrue(len(resp['db_url']))
        self.assertTrue(len(resp['db_name']))
        self.assertTrue(len(resp['spec_url']))

    def test_update_specs(self):
        """Test the endpoint that triggers an update on the specs."""
        resp = requests.put(
            API_URL + '/specs',
            headers=HEADERS_ADMIN,
            params={'reset': '1', 'init_collections': '1'}
        )
        resp_json = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp_json['status']))

    def test_list_views(self):
        """Test the listing out of saved AQL views."""
        resp = requests.get(API_URL + '/specs/views').json()
        self.assertTrue('list_test_vertices' in resp)

    def test_list_schemas(self):
        """Test the listing out of registered JSON schemas for vertices and edges."""
        resp = requests.get(API_URL + '/specs/schemas').json()
        self.assertTrue('test_vertex' in resp['vertices'])
        self.assertTrue('test_edge' in resp['edges'])
        self.assertFalse('error' in resp)
        self.assertTrue(len(resp))

    def test_save_documents_missing_auth(self):
        """Test an invalid attempt to save a doc with a missing auth token."""
        resp = requests.put(
            API_URL + '/documents?on_duplicate=error&overwrite=true&collection'
        ).json()
        self.assertEqual(resp['error'], 'Missing header: Authorization')

    def test_save_documents_invalid_auth(self):
        """Test an invalid attempt to save a doc with a bad auth token."""
        resp = requests.put(
            API_URL + '/documents?on_duplicate=error&overwrite=true&collection',
            headers={'Authorization': 'Bearer ' + INVALID_TOKEN}
        ).json()
        self.assertEqual(resp['error'], '403 - Unauthorized')

    def test_save_documents_non_admin(self):
        """Test an invalid attempt to save a doc as a non-admin."""
        resp = requests.put(
            API_URL + '/documents?on_duplicate=error&overwrite=true&collection',
            headers=HEADERS_NON_ADMIN
        ).json()
        self.assertEqual(resp['error'], '403 - Unauthorized')

    def test_save_documents_invalid_schema(self):
        """Test the case where some documents fail against their schema."""
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'ignore', 'collection': 'test_vertex'},
            data='{"name": "x"}\n{"name": "y"}',
            headers=HEADERS_ADMIN
        ).json()
        self.assertEqual(resp['error'], "'_key' is a required property")
        self.assertEqual(resp['instance'], {'name': 'x'})
        self.assertTrue(resp['schema'])
        self.assertEqual(resp['validator'], 'required')
        self.assertEqual(resp['validator_value'], ['_key'])

    def test_save_documents_missing_schema(self):
        """Test the case where the collection/schema does not exist."""
        resp = requests.put(
            API_URL + '/documents',
            params={'collection': 'xyzabc'},
            data='',
            headers=HEADERS_ADMIN
        ).json()
        self.assertTrue('Schema does not exist' in resp['error'])

    def test_save_documents_invalid_json(self):
        """Test an attempt to save documents with an invalid JSON body."""
        resp = requests.put(
            API_URL + '/documents',
            params={'collection': 'test_vertex'},
            data='\n',
            headers=HEADERS_ADMIN
        ).json()
        self.assertTrue('Unable to parse' in resp['error'])
        self.assertEqual(resp['pos'], 1)
        self.assertEqual(resp['source_json'], '\n')

    def test_create_documents(self):
        """Test all valid cases for saving documents."""
        resp = save_test_docs(3)
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_create_edges(self):
        """Test all valid cases for saving edges."""
        resp = save_test_docs(3, edges=True)
        expected = {'created': 3, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_update_documents(self):
        """Test updating existing documents."""
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'update', 'collection': 'test_vertex'},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_update_edge(self):
        """Test updating existing edge."""
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'update', 'collection': 'test_edge'},
            data=create_test_edges(3),
            headers=HEADERS_ADMIN
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_replace_documents(self):
        """Test replacing of existing documents."""
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'replace', 'collection': 'test_vertex'},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 3, 'ignored': 0, 'error': False}
        self.assertEqual(resp, expected)

    def test_save_documents_dupe_errors(self):
        """Test where we want to raise errors on duplicate documents."""
        save_test_docs(3)
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'error', 'collection': 'test_vertex', 'display_errors': '1'},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN
        ).json()
        self.assertEqual(resp['created'], 0)
        self.assertEqual(resp['errors'], 3)
        self.assertTrue(resp['details'])

    def test_save_documents_ignore_dupes(self):
        """Test ignoring duplicate, existing documents when saving."""
        resp = requests.put(
            API_URL + '/documents',
            params={'on_duplicate': 'ignore', 'collection': 'test_vertex'},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN
        ).json()
        expected = {'created': 0, 'errors': 0, 'empty': 0, 'updated': 0, 'ignored': 3, 'error': False}
        self.assertEqual(resp, expected)

    def test_admin_query(self):
        """Test an ad-hoc query made by an admin."""
        save_test_docs(1)
        query = 'let ws_ids = @ws_ids for v in test_vertex sort rand() limit @count return v._id'
        resp = requests.post(
            API_URL + '/query_results',
            params={},
            headers=HEADERS_ADMIN,
            data=json.dumps({'query': query, 'count': 1})
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(len(resp['results']), 1)

    def test_admin_query_non_admin(self):
        """Test an ad-hoc query error as a non-admin."""
        query = 'let ws_ids = @ws_ids for v in test_vertex sort rand() limit @count return v._id'
        resp = requests.post(
            API_URL + '/query_results',
            params={},
            headers=HEADERS_NON_ADMIN,
            data=json.dumps({'query': query, 'count': 1})
        ).json()
        self.assertEqual(resp['error'], '403 - Unauthorized')

    def test_admin_query_invalid_auth(self):
        """Test the error response for an ad-hoc admin query without auth."""
        query = 'let ws_ids = @ws_ids for v in test_vertex sort rand() limit @count return v._id'
        resp = requests.post(
            API_URL + '/query_results',
            params={},
            headers={'Authorization': INVALID_TOKEN},
            data=json.dumps({'query': query, 'count': 1})
        ).json()
        self.assertEqual(resp['error'], '403 - Unauthorized')

    def test_query_with_cursor(self):
        """Test getting more data via a query cursor and setting batch size."""
        save_test_docs(count=20)
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices', 'batch_size': 10, 'full_count': True}
        ).json()
        self.assertTrue(resp['cursor_id'])
        self.assertEqual(resp['has_more'], True)
        self.assertEqual(resp['count'], 20)
        self.assertEqual(resp['stats']['fullCount'], 20)
        self.assertTrue(len(resp['results']), 10)
        cursor_id = resp['cursor_id']
        resp = requests.post(
            API_URL + '/query_results',
            params={'cursor_id': cursor_id}
        ).json()
        self.assertEqual(resp['count'], 20)
        self.assertEqual(resp['stats']['fullCount'], 20)
        self.assertEqual(resp['has_more'], False)
        self.assertEqual(resp['cursor_id'], None)
        self.assertTrue(len(resp['results']), 10)
        # Try to get the same cursor again
        resp = requests.post(
            API_URL + '/query_results',
            params={'cursor_id': cursor_id}
        ).json()
        self.assertTrue(resp['error'])
        self.assertEqual(resp['arango_message'], 'cursor not found')

    def test_query_no_name(self):
        """Test a query error with a view name that does not exist."""
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'nonexistent'}
        ).json()
        self.assertEqual(resp['error'], 'View does not exist.')
        self.assertEqual(resp['name'], 'nonexistent')

    def test_query_missing_bind_var(self):
        """Test a query error with a missing bind variable."""
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices'},
            data=json.dumps({'xyz': 'test_vertex'})
        ).json()
        self.assertEqual(resp['error'], 'ArangoDB server error.')
        self.assertTrue(resp['arango_message'])

    def test_auth_query_with_access(self):
        """Test the case where we query a collection with specific workspace access."""
        ws_id = 3
        # Remove all test vertices and create one with a ws_id
        requests.put(
            API_URL + '/documents',
            params={'overwrite': True, 'collection': 'test_vertex'},
            data=json.dumps({
                'name': 'requires_auth',
                '_key': '123',
                'ws_id': ws_id
            }),
            headers=HEADERS_ADMIN
        )
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices'},
            headers={'Authorization': 'valid_token'}  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['ws_id'], ws_id)

    def test_auth_query_no_access(self):
        """Test the case where we try to query a collection without the right workspace access."""
        # Remove all test vertices and create one with a ws_id
        requests.put(
            API_URL + '/documents',
            params={'overwrite': True, 'collection': 'test_vertex'},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 9999}',
            headers=HEADERS_ADMIN
        )
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices'},
            headers={'Authorization': 'valid_token'}  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp['count'], 0)

    def test_query_cannot_pass_ws_ids(self):
        """Test that users cannot set the ws_ids param."""
        ws_id = 99
        requests.put(
            API_URL + '/documents',
            params={'overwrite': True, 'collection': 'test_vertex'},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 99}',
            headers=HEADERS_ADMIN
        )
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices'},
            data=json.dumps({'ws_ids': [ws_id]}),
            headers={'Authorization': 'valid_token'}
        ).json()
        self.assertEqual(resp['count'], 0)

    def test_auth_query_invalid_token(self):
        """Test the case where we try to authorize a query using an invalid auth token."""
        requests.put(
            API_URL + '/documents',
            params={'overwrite': True, 'collection': 'test_vertex'},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 99}',
            headers=HEADERS_ADMIN
        )
        resp = requests.post(
            API_URL + '/query_results',
            params={'view': 'list_test_vertices'},
            data=json.dumps({'ws_ids': [1]}),
            headers={'Authorization': INVALID_TOKEN}
        )
        self.assertEqual(resp.status_code, 403)

    def test_auth_adhoc_query(self):
        """Test that the 'ws_ids' bind-var is set for RE_ADMINs."""
        ws_id = 99
        requests.put(
            API_URL + '/documents',
            params={'overwrite': True, 'collection': 'test_vertex'},
            data=json.dumps({'name': 'requires_auth', 'key': '1', 'ws_id': ws_id}),
            headers={'Authorization': 'valid_token'}
        )
        # This is the same query as list_test_vertices.aql in the spec
        query = 'for o in test_vertex filter o.is_public || o.ws_id IN @ws_ids return o'
        resp = requests.post(
            API_URL + '/query_results',
            data=json.dumps({'query': query}),
            headers={'Authorization': ADMIN_TOKEN}  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp['count'], 1)

    def test_queries_are_readonly(self):
        """Test that ad-hoc admin queries cannot do any writing."""
        save_test_docs(1)
        query = 'let ws_ids = @ws_ids for v in test_vertex remove v in test_vertex'
        resp = requests.post(
            API_URL + '/query_results',
            headers=HEADERS_ADMIN,
            data=json.dumps({'query': query})
        ).json()
        self.assertTrue(resp['error'])
        self.assertTrue('read only' in resp['arango_message'])
