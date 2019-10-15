import unittest
import os
from uuid import uuid4

from src.relation_engine_client import REClient
from src.relation_engine_client.exceptions import RERequestError, RENotFound

_API_URL = os.environ.get('RE_API_URL', 'http://localhost:5000')
_VERT_COLL = 'test_vertex'
_EDGE_COLL = 'test_edge'
_TOK_ADMIN = 'admin_token'
_TOK_USER = 'non_admin_token'
_TOK_INVALID = 'invalid_token'


class TestREClientIntegration(unittest.TestCase):
    """Integration tests for the REClient package."""

    @classmethod
    def setUpClass(cls):
        cls.client = REClient(_API_URL, _TOK_ADMIN)
        pass

    def test_admin_query_ok(self):
        _id = self._save_test_vert()
        bind_vars = {'id': _id}
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        result = self.client.admin_query(query, bind_vars)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['_key'], _id)

    def test_admin_empty_query(self):
        bind_vars = {'id': 'xyz'}
        with self.assertRaises(RERequestError) as err:
            self.client.admin_query("", bind_vars)
        self.assertEqual(err.resp.status_code, 400)

    def test_admin_missing_param(self):
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        with self.assertRaises(RERequestError) as err:
            self.client.admin_query(query, bind_vars={})
        self.assertEqual(err.resp.status_code, 400)

    def test_admin_raise_not_found(self):
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        _id = str(uuid4())
        bind_vars = {'id': _id}
        with self.assertRaises(RENotFound) as err:
            self.client.admin_query(query, bind_vars, raise_not_found=True)
        self.assertTrue(_id in err.req_body)

    def test_admin_bad_params(self):
        # No params
        with self.assertRaises(TypeError):
            self.client.admin_query()
        # Wrong type for query
        with self.assertRaises(TypeError):
            self.client.admin_query(123)
        # Wrong type for bind_vars
        with self.assertRaises(TypeError):
            self.client.admin_query("", 123)

    def test_stored_query_ok(self):
        _id = self._save_test_vert()
        bind_vars = {'id': _id}
        qname = 'fetch_test_vertex'
        result = self.client.stored_query(qname, bind_vars)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['_key'], _id)

    def test_stored_query_invalid_args(self):
        # TODO
        pass

    def test_stored_query_unknown_query(self):
        # TODO
        pass

    def test_stored_query_missing_bind_vars(self):
        # TODO
        pass

    def test_stored_query_raise_not_found(self):
        # TODO
        pass

    def test_save_docs_ok(self):
        # TODO
        pass

    def test_save_docs_invalid_args(self):
        # TODO
        pass

    def test_save_docs_unknown_coll(self):
        # TODO
        pass

    def test_save_docs_empty_docs(self):
        # TODO
        pass

    def test_save_docs_invalid_docs(self):
        # TODO
        pass

    # -- Test helpers

    def _save_test_vert(self):
        """Create a test vertex with a random & unique id."""
        _id = str(uuid4())
        docs = [{'_key': _id}]
        results = self.client.save_docs(coll=_VERT_COLL, docs=docs)
        if results['error']:
            raise RuntimeError(results)
        return _id
