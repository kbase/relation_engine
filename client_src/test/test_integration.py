import unittest
import os
from uuid import uuid4

from relation_engine_client import REClient
from relation_engine_client.exceptions import RERequestError, RENotFound

_API_URL = os.environ.get("RE_API_URL", "http://localhost:5000")
# See the test schemas here:
# https://github.com/kbase/relation_engine/tree/develop/spec/collections/test
_VERT_COLL = "test_vertex"
_EDGE_COLL = "test_edge"
# See the docker-compose.yaml file in the root of this repo
# See the mock auth endpoints in relation_engine_server/test/mock_auth/*.json
_TOK_ADMIN = "admin_token"
_TOK_USER = "non_admin_token"
_TOK_INVALID = "invalid_token"


class TestREClientIntegration(unittest.TestCase):
    """Integration tests for the REClient package."""

    @classmethod
    def setUpClass(cls):
        cls.client = REClient(_API_URL, _TOK_ADMIN)

    def test_admin_query_ok(self):
        _id = self._save_test_vert()
        bind_vars = {"id": _id}
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        result = self.client.admin_query(query, bind_vars)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["_key"], _id)

    def test_admin_query_empty_auth(self):
        client2 = REClient(_API_URL)
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        with self.assertRaises(RERequestError) as ctx:
            client2.admin_query(query, {"id": "xyz"})
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Missing header: Authorization" in str(ctx.exception))

    def test_admin_query_invalid_auth(self):
        client2 = REClient(_API_URL, "xyz")
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        with self.assertRaises(RERequestError) as ctx:
            client2.admin_query(query, {"id": "xyz"})
        self.assertEqual(ctx.exception.resp.status_code, 403)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Unauthorized" in str(ctx.exception))

    def test_admin_empty_query(self):
        bind_vars = {"id": "xyz"}
        with self.assertRaises(RERequestError) as ctx:
            self.client.admin_query("", bind_vars)
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    def test_admin_missing_param(self):
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        with self.assertRaises(RERequestError) as ctx:
            self.client.admin_query(query, bind_vars={})
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    def test_admin_raise_not_found(self):
        query = f"FOR vert IN {_VERT_COLL} FILTER vert._key == @id RETURN vert"
        _id = str(uuid4())
        bind_vars = {"id": _id}
        with self.assertRaises(RENotFound) as ctx:
            self.client.admin_query(query, bind_vars, raise_not_found=True)
        self.assertTrue(_id in ctx.exception.req_body)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Request body:" in str(ctx.exception))

    def test_admin_invalid_args(self):
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
        bind_vars = {"key": _id}
        qname = "fetch_test_vertex"
        result = self.client.stored_query(qname, bind_vars)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["_key"], _id)

    def test_stored_query_invalid_args(self):
        with self.assertRaises(TypeError):
            self.client.stored_query()
        with self.assertRaises(TypeError):
            self.client.stored_query(123, 123)
        with self.assertRaises(TypeError):
            self.client.stored_query("")

    def test_stored_query_unknown_query(self):
        qname = "xyz123"
        with self.assertRaises(RERequestError) as ctx:
            self.client.admin_query(qname, bind_vars={"key": 0})
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    def test_stored_query_missing_bind_vars(self):
        qname = "fetch_test_vertex"
        with self.assertRaises(RERequestError) as ctx:
            self.client.admin_query(qname, bind_vars={"x": "y"})
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    def test_stored_query_raise_not_found(self):
        _id = str(uuid4())
        bind_vars = {"key": _id}
        qname = "fetch_test_vertex"
        with self.assertRaises(RENotFound) as ctx:
            self.client.stored_query(qname, bind_vars, raise_not_found=True)
        self.assertTrue(_id in ctx.exception.req_body)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Request body:" in str(ctx.exception))

    def test_save_docs_ok(self):
        _id = str(uuid4())
        docs = [{"_key": _id}]
        results = self.client.save_docs(coll=_VERT_COLL, docs=docs)
        self.assertEqual(results["created"], 1)
        self.assertFalse(results["error"])
        self.assertEqual(results["errors"], 0)
        self.assertEqual(results["ignored"], 0)
        self.assertEqual(results["updated"], 0)

    def test_save_docs_empty_auth(self):
        client2 = REClient(_API_URL)
        docs = [{"_key": "xyz"}]
        with self.assertRaises(RERequestError) as ctx:
            client2.save_docs(coll=_VERT_COLL, docs=docs)
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Missing header: Authorization" in str(ctx.exception))

    def test_save_docs_invalid_auth(self):
        client2 = REClient(_API_URL, "xyz")
        docs = [{"_key": "xyz"}]
        with self.assertRaises(RERequestError) as ctx:
            client2.save_docs(coll=_VERT_COLL, docs=docs)
        self.assertEqual(ctx.exception.resp.status_code, 403)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Unauthorized" in str(ctx.exception))

    def test_save_docs_invalid_args(self):
        with self.assertRaises(TypeError):
            self.client.save_docs()
        with self.assertRaises(TypeError):
            self.client.save_docs(123, 456)
        # Empty docs list
        with self.assertRaises(TypeError):
            self.client.save_docs(_VERT_COLL, [])

    def test_save_docs_unknown_coll(self):
        with self.assertRaises(RERequestError) as ctx:
            self.client.save_docs("xyz123", [{"_key": 0}])
        self.assertEqual(ctx.exception.resp.status_code, 404)
        self.assertEqual(
            ctx.exception.resp.json(),
            {
                "error": {
                    "message": "Not found",
                    "details": "Collection 'xyz123' does not exist.",
                    "name": "xyz123",
                }
            },
        )
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    def test_save_docs_invalid_docs(self):
        with self.assertRaises(RERequestError) as ctx:
            self.client.save_docs(_VERT_COLL, [{"hi": 0}])
        self.assertEqual(ctx.exception.resp.status_code, 400)
        # Mostly make sure that the __str__ method does not throw any errs
        self.assertTrue("Response:" in str(ctx.exception))

    # -- Test helpers

    def _save_test_vert(self):
        """Create a test vertex with a random & unique id."""
        _id = str(uuid4())
        docs = [{"_key": _id}]
        results = self.client.save_docs(coll=_VERT_COLL, docs=docs)
        if results["error"]:
            raise RuntimeError(results)
        return _id
