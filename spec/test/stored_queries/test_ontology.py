"""
Tests for the ontology stored queries.

These tests run within the re_api docker image, and require access to the ArangoDB, auth, and workspace images.
"""
import json
import time
import unittest
import requests

from spec.test.helpers import (
    get_config,
    create_test_docs,
    check_spec_test_env,
)

_CONF = get_config()
_NOW = int(time.time() * 1000)


class TestOntology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create test documents"""

        check_spec_test_env()
        term_docs = [
            {
                "_key": "1",
                "id": "ENVO:00000446",
                "name": "terrestrial biome",
                "type": "CLASS",
                "namespace": "ENVO",
                "alt_ids": [],
                "def": {"val": ""},
                "comments": [],
                "subsets": [],
                "synonyms": [],
                "xrefs": [],
            },
            {
                "_key": "2",
                "id": "ENVO:00000428",
                "name": "biome",
                "type": "CLASS",
                "namespace": "ENVO",
                "alt_ids": [],
                "def": {"val": ""},
                "comments": [],
                "subsets": [],
                "synonyms": [],
                "xrefs": [],
            },
            {
                "_key": "3",
                "id": "ENVO:01001110",
                "name": "ecosystem",
                "type": "CLASS",
                "namespace": "ENVO",
                "alt_ids": [],
                "def": {"val": ""},
                "comments": [],
                "subsets": [],
                "synonyms": [],
                "xrefs": [],
            },
            {
                "_key": "4",
                "id": "ENVO:01000254",
                "name": "environmental system",
                "type": "CLASS",
                "namespace": "ENVO",
                "alt_ids": [],
                "def": {"val": ""},
                "comments": [],
                "subsets": [],
                "synonyms": [],
                "xrefs": [],
            },
            {
                "_key": "5",
                "id": "ENVO:00002030",
                "name": "aquatic biome",
                "type": "CLASS",
                "namespace": "ENVO",
                "alt_ids": [],
                "def": {"val": ""},
                "comments": [],
                "subsets": [],
                "synonyms": [],
                "xrefs": [],
            },
        ]
        edge_docs = [
            {
                "_from": "ENVO_terms/1",
                "_to": "ENVO_terms/2",
                "from": "1",
                "to": "2",
                "id": "1",
                "type": "is_a",
            },
            {
                "_from": "ENVO_terms/2",
                "_to": "ENVO_terms/3",
                "from": "2",
                "to": "3",
                "id": "2",
                "type": "is_a",
            },
            {
                "_from": "ENVO_terms/3",
                "_to": "ENVO_terms/4",
                "from": "3",
                "to": "4",
                "id": "3",
                "type": "is_a",
            },
            {
                "_from": "ENVO_terms/5",
                "_to": "ENVO_terms/2",
                "from": "5",
                "to": "2",
                "id": "4",
                "type": "is_a",
            },
        ]
        _create_delta_test_docs("ENVO_terms", term_docs)
        _create_delta_test_docs("ENVO_edges", edge_docs, edge=True)

    def test_get_term_by_name(self):
        """Test query of retrieving onotlogy term by searching name"""
        resp1 = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_term_by_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "name": "terrestrial biome",
                    "ancestor_term": "ENVO:01001110",
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp1["count"], 1)
        ids = [r["id"] for r in resp1["results"]]
        self.assertEqual(ids, ["ENVO:00000446"])

        resp2 = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_term_by_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "name": "terrestrial",
                    "ancestor_term": "ENVO:01001110",
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp2["count"], 0)

        resp3 = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_term_by_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "name": "terrestrial biome",
                    "ancestor_term": "ENVO:00002030",
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp3["count"], 0)

        resp4 = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_term_by_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "name": "terrestrial biome",
                    "ancestor_term": "",
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp4["count"], 1)
        ids = [r["id"] for r in resp4["results"]]
        self.assertEqual(ids, ["ENVO:00000446"])

    def test_get_children(self):
        """Test query of ontology children."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_children"},
            data=json.dumps(
                {
                    "id": "ENVO:00000428",
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 2)
        ids = [r["term"]["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:00000446", "ENVO:00002030"])

    def test_get_parents(self):
        """Test query of ontology parents."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_parents"},
            data=json.dumps(
                {
                    "id": "ENVO:00000428",
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 1)
        ids = [r["term"]["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:01001110"])

    def test_get_descendants(self):
        """Test query of ontology descendants."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_descendants"},
            data=json.dumps(
                {
                    "id": "ENVO:01001110",
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 3)
        ids = [r["term"]["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:00000446", "ENVO:00000428", "ENVO:00002030"])

    def test_get_ancestors(self):
        """Test query of ontology ancestors."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_ancestors"},
            data=json.dumps(
                {
                    "id": "ENVO:00000446",
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 3)
        ids = [r["term"]["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:00000428", "ENVO:01000254", "ENVO:01001110"])

    def test_get_siblings(self):
        """Test query of ontology siblings."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_siblings"},
            data=json.dumps(
                {
                    "id": "ENVO:00000446",
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                    "@onto_edges": "ENVO_edges",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 1)
        ids = [r["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:00002030"])

    def test_get_terms(self):
        """Test query of ontology terms."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ontology_get_terms"},
            data=json.dumps(
                {
                    "ids": ["ENVO:00000446", "ENVO:00002030", "abcd"],
                    "ts": _NOW,
                    "@onto_terms": "ENVO_terms",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 2)
        ids = [r["id"] for r in resp["results"]]
        self.assertEqual(ids, ["ENVO:00000446", "ENVO:00002030"])


# -- Test helpers


def _run_search_sciname(
    self, ranks, include_strains, expected_count, expected_sci_names
):
    """
    Helper to run the taxonomy_search_sci_name query and make some standard
    assertions on the response.
    """
    data = {
        "ts": _NOW,
        "search_text": "prefix:bac",
        "@taxon_coll": "ncbi_taxon",
        "sciname_field": "scientific_name",
    }
    if ranks is not None:
        data["ranks"] = ranks
    if include_strains is not None:
        data["include_strains"] = include_strains
    resp = requests.post(
        _CONF["re_api_url"] + "/api/v1/query_results",
        params={"stored_query": "taxonomy_search_sci_name"},
        data=json.dumps(data),
    ).json()
    result = resp["results"][0]
    self.assertEqual(result["total_count"], expected_count)
    names = {r["scientific_name"] for r in result["results"]}
    self.assertEqual(names, expected_sci_names)


def _ws_defaults(data):
    """Set some defaults for the required workspace fields."""
    defaults = {
        "owner": "owner",
        "max_obj_id": 1,
        "lock_status": "n",
        "name": "wsname",
        "mod_epoch": 1,
        "is_public": True,
        "is_deleted": False,
        "metadata": {"narrative_nice_name": "narrname"},
    }
    # Merge the data with the above defaults
    return dict(defaults, **data)


def _construct_ws_obj_ver(wsid, objid, ver, is_public=False):
    """Test helper to create a ws_object_version vertex."""
    return {
        "_key": f"{wsid}:{objid}:{ver}",
        "workspace_id": wsid,
        "object_id": objid,
        "version": ver,
        "name": f"obj_name{objid}",
        "hash": "xyz",
        "size": 100,
        "epoch": 0,
        "deleted": False,
        "is_public": is_public,
    }


def _construct_ws_obj(wsid, objid, is_public=False):
    """Test helper to create a ws_object vertex."""
    return {
        "_key": f"{wsid}:{objid}",
        "workspace_id": wsid,
        "object_id": objid,
        "deleted": False,
        "is_public": is_public,
    }


def _create_delta_test_docs(coll_name, docs, edge=False):
    """Add in delta required fields."""
    if edge:
        for doc in docs:
            # Replicate the time-travel system by just setting 'from' and 'to' to the keys
            doc["from"] = doc["_from"].split("/")[1]
            doc["to"] = doc["_to"].split("/")[1]
    for doc in docs:
        doc["expired"] = 9007199254740991
        doc["created"] = 0
    create_test_docs(coll_name, docs)
