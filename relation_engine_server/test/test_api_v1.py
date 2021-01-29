"""
Simple integration tests on the API itself.

These tests run within the re_api docker image, and require access to the ArangoDB, auth, and workspace images.
"""
import unittest
import requests
import json
import os
from relation_engine_server.utils.config import get_config
from relation_engine_server.utils.wait_for import wait_for_api

_CONF = get_config()

# Use the mock auth tokens
NON_ADMIN_TOKEN = "non_admin_token"
ADMIN_TOKEN = "admin_token"
INVALID_TOKEN = "invalid_token"

# Use the docker-compose url of the running flask server
URL = os.environ.get("TEST_URL", "http://localhost:5000")
VERSION = "v1"
API_URL = "/".join([URL, "api", VERSION])

HEADERS_NON_ADMIN = {
    "Authorization": "Bearer " + NON_ADMIN_TOKEN,
    "Content-Type": "application/json",
}
HEADERS_ADMIN = {
    "Authorization": "Bearer " + ADMIN_TOKEN,
    "Content-Type": "application/json",
}


def create_test_docs(count):
    """Produce some test documents."""

    def doc(i):
        return '{"name": "name", "_key": "%s", "is_public": true}' % i

    return "\n".join(doc(i) for i in range(0, count))


def create_test_edges(count):
    """Produce some test edges."""

    def doc(i):
        return '{"_from": "test_vertex/%s", "_to": "test_vertex/%s"}' % (i, i)

    return "\n".join(doc(i) for i in range(0, count))


def save_test_docs(count, edges=False):
    if edges:
        docs = create_test_edges(count)
        collection = "test_edge"
    else:
        docs = create_test_docs(count)
        collection = "test_vertex"
    return requests.put(
        API_URL + "/documents",
        params={"overwrite": True, "collection": collection},
        data=docs,
        headers=HEADERS_ADMIN,
    ).json()


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wait_for_api()
        cls.maxDiff = None

    def test_request(
        self,
        url=None,
        params=None,
        data=None,
        headers=None,
        method="get",
        status_code=200,
        resp_json=None,
        resp_test=None,
    ):
        """test a request to the server

        arguments:
            url             url to be appended to API_URL (i.e. request will be made to API_URL + url)
            params          request parameters
            data            query data, encoded as JSON
            method          HTTP method; defaults to 'get'
            status_code     expected response status; defaults to 200
            resp_json       expected response content (JSON)
            resp_test       a function to perform on the response to test that it is as expected
        """

        # this method should only be run from another test method
        if url is None:
            self.assertTrue(True)
            return

        resp = requests.request(
            method,
            API_URL + url,
            params=params,
            data=data,
            headers=headers,
        )
        self.assertEqual(resp.status_code, status_code)
        if resp_json:
            self.assertEqual(resp_json, resp.json())

        if resp_test:
            resp_test(self, resp)

    def test_root(self):
        """Test root path for api."""
        resp_json = requests.get(URL + "/").json()
        self.assertEqual(resp_json["arangodb_status"], "connected_authorized")
        self.assertTrue(resp_json["commit_hash"])
        self.assertTrue(resp_json["repo_url"])

    def test_config(self):
        """Test config fetch."""
        resp_json = requests.get(API_URL + "/config").json()
        self.assertTrue(len(resp_json["auth_url"]))
        self.assertTrue(len(resp_json["workspace_url"]))
        self.assertTrue(len(resp_json["kbase_endpoint"]))
        self.assertTrue(len(resp_json["db_url"]))
        self.assertTrue(len(resp_json["db_name"]))

    def test_update_specs(self):
        """Test the endpoint that triggers an update on the specs."""
        resp = requests.put(
            API_URL + "/specs",
            headers=HEADERS_ADMIN,
            params={"reset": "1", "init_collections": "1"},
        )
        resp_json = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp_json["status"], "updated")
        self.assertEqual(
            resp_json["updated_from"],
            "/app/relation_engine_server/test/spec_release/spec.tar.gz",
        )

        # delete the SPEC_TEST_READY env var as it is no longer true
        os.environ.pop("SPEC_TEST_READY", None)

        # Test that the indexes get created and not duplicated
        url = _CONF["db_url"] + "/_api/index"
        auth = (_CONF["db_user"], _CONF["db_pass"])
        resp = requests.get(url, params={"collection": "ncbi_taxon"}, auth=auth)
        resp_json = resp.json()
        indexes = resp_json["indexes"]
        self.assertEqual(len(indexes), 4)
        fields = [i["fields"] for i in indexes]
        self.assertEqual(
            set(tuple(f) for f in fields),
            {
                ("_key",),
                ("scientific_name",),
                ("id", "expired", "created"),
                ("expired", "created", "last_version"),
            },
        )

    def check_list_contains(self, the_list, must_contain):
        """ensure the_list contains the items in must_contain"""
        for item in must_contain:
            self.assertIn(item, the_list)

    def test_list_collections(self):
        """Test the listing out of registered collection schemas for vertices and edges."""
        for variant in ["schemas", "collections"]:

            def check_resp_json_contains(self, resp):
                resp_json = resp.json()
                self.check_list_contains(
                    resp_json, ["test_edge", "test_vertex", "ncbi_taxon"]
                )

            self.test_request("/specs/" + variant, resp_test=check_resp_json_contains)

    def test_list_data_sources(self):
        """test the data source listing endpoints"""

        # there are two different data_sources endpoints that return very similar results
        # /data_sources is used by the UI and requires slightly different response formatting
        # /specs/data_sources is in the standard /specs format used by collections and stored_queries

        data_sources = ["ncbi_taxonomy"]

        # /spec/data_sources endpoint
        def check_resp_json_spec_endpoint(self, resp):
            resp_json = resp.json()
            self.check_list_contains(
                resp_json,
                data_sources,
            )

        self.test_request(
            "/specs/data_sources", resp_test=check_resp_json_spec_endpoint
        )

    def test_list_stored_queries(self):
        """Test the listing out of saved AQL stored queries."""

        def check_resp_json_contains(self, resp):
            resp_json = resp.json()
            self.check_list_contains(
                resp_json,
                ["fetch_test_vertex", "list_test_vertices", "ncbi_fetch_taxon"],
            )

        self.test_request(
            "/specs/stored_queries",
            resp_test=check_resp_json_contains,
        )

    def test_fetch_collection_and_fetch_schema_for_doc(self):
        """Given a collection name or a document ID, fetch its schema."""

        name = "test_vertex"
        collection_params = {"name": name}  # valid collection
        document_params = {"doc_id": name + "/123"}  # valid document

        def check_resp_json(self, resp):
            resp_json = resp.json()
            self.assertEqual(resp_json["name"], name)
            self.assertEqual(resp_json["type"], "vertex")
            self.assertTrue(resp_json["schema"])

        for variant in ["schemas", "collections"]:
            for params in [document_params, collection_params]:
                self.test_request(
                    "/specs/" + variant,
                    params=params,
                    resp_test=check_resp_json,
                )

    def test_fetch_data_source(self):
        """fetch a data source by name"""

        name = "ncbi_taxonomy"

        def check_resp_json(self, resp):
            resp_json = resp.json()
            self.assertEqual(type(resp_json), dict)
            self.assertEqual(
                set(resp_json.keys()),
                {"name", "category", "title", "home_url", "data_url", "logo_url"},
            )
            self.assertTrue(
                "/ui-assets/images/third-party-data-sources/ncbi"
                in resp_json["logo_url"]
            )

        self.test_request(
            "/specs/data_sources", {"name": name}, resp_test=check_resp_json
        )

    def test_fetch_stored_query(self):
        """fetch a stored query by name"""

        name = "fetch_test_vertex"

        # note that the stored_queries endpoint returns the query data in a dict
        # under the key 'stored_query'
        def check_resp_json(self, resp):
            resp_json = resp.json()
            self.assertEqual(type(resp_json["stored_query"]), dict)
            self.assertEqual(resp_json["stored_query"]["name"], name)
            self.assertEqual(
                set(resp_json["stored_query"].keys()), {"name", "query", "params"}
            )

        self.test_request(
            "/specs/stored_queries", {"name": name}, resp_test=check_resp_json
        )

    def test_fetch_invalid_data_source(self):
        """Unknown data source name should yield 404 status."""

        name = "invalid_data_source"
        self.test_request(
            "/specs/data_sources",
            {"name": name},
            status_code=404,
            resp_json={
                "error": {
                    "message": "Not found",
                    "details": f"Data source '{name}' does not exist.",
                    "name": name,
                }
            },
        )

    def test_fetch_invalid_collections_and_documents(self):
        """Test the case where the collection or document does not exist."""

        name = "fake_collection"
        collection_params = {"name": name}  # fetch an invalid collection
        document_params = {"doc_id": name + "/123"}  # fetch an invalid document
        for variant in ["schemas", "collections"]:
            for params in [document_params, collection_params]:

                self.test_request(
                    "/specs/" + variant,
                    params=params,
                    status_code=404,
                    resp_json={
                        "error": {
                            "message": "Not found",
                            "details": f"Collection '{name}' does not exist.",
                            "name": name,
                        }
                    },
                )

    def test_fetch_invalid_stored_queries(self):
        """Test the case where the stored query does not exist."""

        name = "made_up_stored_query"
        self.test_request(
            "/specs/stored_queries",
            params={"name": name},
            status_code=404,
            resp_json={
                "error": {
                    "message": "Not found",
                    "details": f"Stored query '{name}' does not exist.",
                    "name": name,
                }
            },
        )

    def test_show_data_sources(self):
        resp = requests.get(API_URL + "/data_sources")
        self.assertTrue(resp.ok)
        resp_json = resp.json()
        self.assertTrue(len(resp_json["data_sources"]) > 0)
        self.assertEqual(set(type(x) for x in resp_json["data_sources"]), {str})

    def test_show_data_source(self):

        name = "ncbi_taxonomy"

        def check_resp_json(self, resp):
            resp_json = resp.json()
            self.assertEqual(type(resp_json["data_source"]), dict)
            self.assertEqual(
                set(resp_json["data_source"].keys()),
                {"name", "category", "title", "home_url", "data_url", "logo_url"},
            )
            self.assertTrue(
                "/ui-assets/images/third-party-data-sources/ncbi"
                in resp_json["data_source"]["logo_url"]
            )

        self.test_request("/data_sources/" + name, resp_test=check_resp_json)

        resp = requests.get(API_URL + "/data_sources/ncbi_taxonomy")
        self.assertTrue(resp.ok)
        resp_json = resp.json()
        self.assertEqual(type(resp_json["data_source"]), dict)
        self.assertEqual(
            set(resp_json["data_source"].keys()),
            {"name", "category", "title", "home_url", "data_url", "logo_url"},
        )
        self.assertTrue(
            "/ui-assets/images/third-party-data-sources/ncbi"
            in resp_json["data_source"]["logo_url"]
        )

    def test_show_data_source_unknown(self):
        """Unknown data source name should yield 404 status."""
        name = "xyzyxz"

        self.test_request(
            f"/data_sources/{name}",
            status_code=404,
            resp_json={
                "error": {
                    "message": "Not found",
                    "details": f"Data source '{name}' does not exist.",
                    "name": name,
                }
            },
        )

    def test_save_documents_missing_auth(self):
        """Test an invalid attempt to save a doc with a missing auth token."""
        self.test_request(
            "/documents?on_duplicate=error&overwrite=true&collection",
            method="put",
            status_code=400,
            resp_json={"error": {"message": "Missing header: Authorization"}},
        )

    def test_save_documents_invalid_auth(self):
        """Test an invalid attempt to save a doc with a bad auth token."""

        # see ./mock_auth/auth_invalid.json for the response
        auth_response = {
            "error": {
                "httpcode": 401,
                "httpstatus": "Unauthorized",
                "appcode": 10020,
                "apperror": "Invalid token",
                "message": "10020 Invalid token",
                "callid": "1757210147564211",
                "time": 1542737889450,
            }
        }

        self.test_request(
            "/documents?on_duplicate=error&overwrite=true&collection",
            headers={"Authorization": "Bearer " + INVALID_TOKEN},
            method="put",
            status_code=403,
            resp_json={
                "error": {
                    "message": "Unauthorized",
                    "auth_url": "http://auth:5000",
                    "auth_response": json.dumps(auth_response),
                }
            },
        )

    def test_save_documents_non_admin(self):
        """Test an invalid attempt to save a doc as a non-admin."""
        self.test_request(
            "/documents?on_duplicate=error&overwrite=true&collection",
            headers=HEADERS_NON_ADMIN,
            method="put",
            status_code=403,
            resp_json={
                "error": {
                    "auth_response": "Missing role",
                    "auth_url": "http://auth:5000",
                    "message": "Unauthorized",
                }
            },
        )

    def test_save_documents_invalid_schema(self):
        """Test the case where some documents fail against their schema."""

        self.test_request(
            "/documents",
            params={"on_duplicate": "ignore", "collection": "test_vertex"},
            data='{"name": "x"}\n{"name": "y"}',
            headers=HEADERS_ADMIN,
            method="put",
            status_code=400,
            resp_json={
                "error": {
                    "message": "'_key' is a required property",
                    "value": {"name": "x"},
                    "path": [],
                    "failed_validator": "required",
                }
            },
        )

    def test_save_documents_missing_schema(self):
        """Test the case where the collection/schema does not exist."""

        name = "fake_collection"
        self.test_request(
            "/documents",
            method="put",
            params={"collection": name},
            data="",
            headers=HEADERS_ADMIN,
            status_code=404,
            resp_json={
                "error": {
                    "message": "Not found",
                    "details": f"Collection '{name}' does not exist.",
                    "name": name,
                }
            },
        )

    def test_save_documents_invalid_json(self):
        """Test an attempt to save documents with an invalid JSON body."""
        resp_json = requests.put(
            API_URL + "/documents",
            params={"collection": "test_vertex"},
            data="\n",
            headers=HEADERS_ADMIN,
        ).json()
        self.assertTrue("Unable to parse" in resp_json["error"]["message"])
        self.assertEqual(resp_json["error"]["pos"], 1)
        self.assertEqual(resp_json["error"]["source_json"], "\n")

    def test_create_documents(self):
        """Test all valid cases for saving documents."""
        resp = save_test_docs(3)
        expected = {
            "created": 3,
            "errors": 0,
            "empty": 0,
            "updated": 0,
            "ignored": 0,
            "error": False,
        }
        self.assertEqual(resp, expected)

    def test_create_edges(self):
        """Test all valid cases for saving edges."""
        resp = save_test_docs(3, edges=True)
        expected = {
            "created": 3,
            "errors": 0,
            "empty": 0,
            "updated": 0,
            "ignored": 0,
            "error": False,
        }
        self.assertEqual(resp, expected)

    def test_update_documents(self):
        """Test updating existing documents."""
        resp_json = requests.put(
            API_URL + "/documents",
            params={"on_duplicate": "update", "collection": "test_vertex"},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN,
        ).json()
        expected = {
            "created": 0,
            "errors": 0,
            "empty": 0,
            "updated": 3,
            "ignored": 0,
            "error": False,
        }
        self.assertEqual(resp_json, expected)

    def test_update_edge(self):
        """Test updating existing edge."""
        edges = create_test_edges(3)
        resp = requests.put(
            API_URL + "/documents",
            params={"on_duplicate": "update", "collection": "test_edge"},
            data=create_test_edges(3),
            headers=HEADERS_ADMIN,
        )
        self.assertTrue(resp.ok)
        resp_json = requests.put(
            API_URL + "/documents",
            params={"on_duplicate": "update", "collection": "test_edge"},
            data=edges,
            headers=HEADERS_ADMIN,
        ).json()
        expected = {
            "created": 0,
            "errors": 0,
            "empty": 0,
            "updated": 3,
            "ignored": 0,
            "error": False,
        }
        self.assertEqual(resp_json, expected)

    def test_replace_documents(self):
        """Test replacing of existing documents."""
        resp_json = requests.put(
            API_URL + "/documents",
            params={"on_duplicate": "replace", "collection": "test_vertex"},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN,
        ).json()
        expected = {
            "created": 0,
            "errors": 0,
            "empty": 0,
            "updated": 3,
            "ignored": 0,
            "error": False,
        }
        self.assertEqual(resp_json, expected)

    def test_save_documents_dupe_errors(self):
        """Test where we want to raise errors on duplicate documents."""
        save_test_docs(3)
        resp_json = requests.put(
            API_URL + "/documents",
            params={
                "on_duplicate": "error",
                "collection": "test_vertex",
                "display_errors": "1",
            },
            data=create_test_docs(3),
            headers=HEADERS_ADMIN,
        ).json()
        self.assertEqual(resp_json["created"], 0)
        self.assertEqual(resp_json["errors"], 3)
        self.assertTrue(resp_json["details"])

    def test_save_documents_ignore_dupes(self):
        """Test ignoring duplicate, existing documents when saving."""
        resp_json = requests.put(
            API_URL + "/documents",
            params={"on_duplicate": "ignore", "collection": "test_vertex"},
            data=create_test_docs(3),
            headers=HEADERS_ADMIN,
        ).json()
        expected = {
            "created": 0,
            "errors": 0,
            "empty": 0,
            "updated": 0,
            "ignored": 3,
            "error": False,
        }
        self.assertEqual(resp_json, expected)

    def test_admin_query(self):
        """Test an ad-hoc query made by an admin."""
        save_test_docs(1)
        query = "for v in test_vertex sort rand() limit @count return v._id"
        resp_json = requests.post(
            API_URL + "/query_results",
            params={},
            headers=HEADERS_ADMIN,
            data=json.dumps({"query": query, "count": 1}),
        ).json()
        self.assertEqual(resp_json["count"], 1)
        self.assertEqual(len(resp_json["results"]), 1)

    def test_admin_query_non_admin(self):
        """Test an ad-hoc query error as a non-admin."""
        query = "for v in test_vertex sort rand() limit @count return v._id"
        self.test_request(
            "/query_results",
            method="post",
            params={},
            headers=HEADERS_NON_ADMIN,
            data=json.dumps({"query": query, "count": 1}),
            status_code=403,
            resp_json={
                "error": {
                    "message": "Unauthorized",
                    "auth_url": "http://auth:5000",
                    "auth_response": "Missing role",
                }
            },
        )

    def test_admin_query_invalid_auth(self):
        """Test the error response for an ad-hoc admin query without auth."""

        # see ./mock_auth/auth_invalid.json for response
        query = "for v in test_vertex sort rand() limit @count return v._id"
        self.test_request(
            "/query_results",
            method="post",
            params={},
            headers={"Authorization": INVALID_TOKEN},
            data=json.dumps({"query": query, "count": 1}),
            status_code=403,
            resp_json={
                "error": {
                    "message": "Unauthorized",
                    "auth_url": "http://auth:5000",
                    "auth_response": json.dumps(
                        {
                            "error": {
                                "httpcode": 401,
                                "httpstatus": "Unauthorized",
                                "appcode": 10020,
                                "apperror": "Invalid token",
                                "message": "10020 Invalid token",
                                "callid": "1757210147564211",
                                "time": 1542737889450,
                            }
                        }
                    ),
                }
            },
        )

    def test_query_with_cursor(self):
        """Test getting more data via a query cursor and setting batch size."""
        save_test_docs(count=20)
        resp_json = requests.post(
            API_URL + "/query_results",
            params={
                "stored_query": "list_test_vertices",
                "batch_size": 10,
                "full_count": True,
            },
        ).json()
        self.assertTrue(resp_json["cursor_id"])
        self.assertEqual(resp_json["has_more"], True)
        self.assertEqual(resp_json["count"], 20)
        self.assertEqual(resp_json["stats"]["fullCount"], 20)
        self.assertTrue(len(resp_json["results"]), 10)

        cursor_id = resp_json["cursor_id"]
        resp_json = requests.post(
            API_URL + "/query_results", params={"cursor_id": cursor_id}
        ).json()
        self.assertEqual(resp_json["count"], 20)
        self.assertEqual(resp_json["stats"]["fullCount"], 20)
        self.assertEqual(resp_json["has_more"], False)
        self.assertEqual(resp_json["cursor_id"], None)
        self.assertTrue(len(resp_json["results"]), 10)

        # Try to get the same cursor again
        self.test_request(
            "/query_results",
            method="post",
            params={"cursor_id": cursor_id},
            status_code=400,
            resp_json={
                "error": {
                    "message": "ArangoDB server error.",
                    "arango_message": "cursor not found",
                }
            },
        )

    def test_query_no_name(self):
        """Test a query error with a stored query name that does not exist."""

        name = "nonexistent"
        self.test_request(
            "/query_results",
            method="post",
            params={"stored_query": name},
            status_code=404,
            resp_json={
                "error": {
                    "message": "Not found",
                    "details": f"Stored query '{name}' does not exist.",
                    "name": name,
                }
            },
        )

    def test_query_missing_bind_var(self):
        """Test a query error with a missing bind variable."""

        arango_msg = (
            "AQL: bind parameter 'xyz' was not declared in the query (while parsing)"
        )
        self.test_request(
            "/query_results",
            method="post",
            params={"stored_query": "list_test_vertices"},
            data=json.dumps({"xyz": "test_vertex"}),
            status_code=400,
            resp_json={
                "error": {
                    "message": "ArangoDB server error.",
                    "arango_message": arango_msg,
                }
            },
        )

    def test_auth_query_with_access(self):
        """Test the case where we query a collection with specific workspace access."""
        ws_id = 3
        # Remove all test vertices and create one with a ws_id
        requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_vertex"},
            data=json.dumps({"name": "requires_auth", "_key": "123", "ws_id": ws_id}),
            headers=HEADERS_ADMIN,
        )
        resp_json = requests.post(
            API_URL + "/query_results",
            params={"stored_query": "list_test_vertices"},
            headers={
                "Authorization": "valid_token"
            },  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp_json["count"], 1)
        self.assertEqual(resp_json["results"][0]["ws_id"], ws_id)

    def test_auth_query_no_access(self):
        """Test the case where we try to query a collection without the right workspace access."""
        # Remove all test vertices and create one with a ws_id
        requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_vertex"},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 9999}',
            headers=HEADERS_ADMIN,
        )
        resp_json = requests.post(
            API_URL + "/query_results",
            params={"stored_query": "list_test_vertices"},
            headers={
                "Authorization": "valid_token"
            },  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp_json["count"], 0)

    def test_query_cannot_pass_ws_ids(self):
        """Test that users cannot set the ws_ids param."""
        ws_id = 99
        requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_vertex"},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 99}',
            headers=HEADERS_ADMIN,
        )
        resp_json = requests.post(
            API_URL + "/query_results",
            params={"view": "list_test_vertices"},
            data=json.dumps({"ws_ids": [ws_id]}),
            headers={"Authorization": "valid_token"},
        ).json()
        self.assertEqual(resp_json["count"], 0)

    def test_auth_query_invalid_token(self):
        """Test the case where we try to authorize a query using an invalid auth token."""
        requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_vertex"},
            data='{"name": "requires_auth", "_key": "1", "ws_id": 99}',
            headers=HEADERS_ADMIN,
        )

        # see ./mock_workspace/list_workspace_ids_invalid.json for response
        self.test_request(
            "/query_results",
            params={"view": "list_test_vertices"},
            data=json.dumps({"ws_ids": [1]}),
            headers={"Authorization": INVALID_TOKEN},
            method="post",
            status_code=403,
            resp_json={
                "error": {
                    "message": "Unauthorized",
                    "auth_url": "http://workspace:5000",
                    "auth_response": json.dumps(
                        {
                            "version": "1.1",
                            "error": {
                                "name": "JSONRPCError",
                                "code": -32400,
                                "message": "Token validation failed!",
                                "error": "...",
                            },
                        }
                    ),
                }
            },
        )

    def test_auth_adhoc_query(self):
        """Test that the 'ws_ids' bind-var is set for RE_ADMINs."""
        ws_id = 99
        requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_vertex"},
            data=json.dumps({"name": "requires_auth", "key": "1", "ws_id": ws_id}),
            headers={"Authorization": "valid_token"},
        )
        # This is the same query as list_test_vertices.aql in the spec
        query = "for o in test_vertex filter o.is_public || o.ws_id IN ws_ids return o"
        resp_json = requests.post(
            API_URL + "/query_results",
            data=json.dumps({"query": query}),
            headers={
                "Authorization": ADMIN_TOKEN
            },  # see ./mock_workspace/endpoints.json
        ).json()
        self.assertEqual(resp_json["count"], 1)

    def test_save_docs_invalid(self):
        """Test that an invalid bulk save returns a 400 response"""
        doc = {"_from": "|||", "_to": "|||"}
        resp = requests.put(
            API_URL + "/documents",
            params={"overwrite": True, "collection": "test_edge", "display_errors": 1},
            data=json.dumps(doc),
            headers=HEADERS_ADMIN,
        )
        self.assertEqual(resp.status_code, 400)
        resp_json = resp.json()
        self.assertEqual(resp_json["errors"], 1)
