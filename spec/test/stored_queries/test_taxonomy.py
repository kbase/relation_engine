"""
Tests for the ncbi taxonomy stored queries.

These tests run within the re_api docker image, and require access to the ArangoDB, auth, and workspace images.
"""
import json
import time
import unittest
import requests

from spec.test.helpers import (
    get_config,
    assert_subset,
    create_test_docs,
    check_spec_test_env,
)

_CONF = get_config()
_NOW = int(time.time() * 1000)


class TestTaxonomy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create test documents"""

        check_spec_test_env()
        taxon_docs = [
            {
                "_key": "1",
                "scientific_name": "Bacteria",
                "rank": "Domain",
                "strain": False,
            },
            {
                "_key": "2",
                "scientific_name": "Firmicutes",
                "rank": "Phylum",
                "strain": False,
            },
            {
                "_key": "3",
                "scientific_name": "Bacilli",
                "rank": "Class",
                "strain": False,
            },
            {
                "_key": "4",
                "scientific_name": "Proteobacteria",
                "rank": "Phylum",
                "strain": False,
            },
            {
                "_key": "5",
                "scientific_name": "Alphaproteobacteria",
                "rank": "Class",
                "strain": False,
            },
            {
                "_key": "6",
                "scientific_name": "Gammaproteobacteria",
                "rank": "Class",
                "strain": False,
            },
            {
                "_key": "7",
                "scientific_name": "Deltaproteobacteria",
                "rank": "Class",
                "strain": False,
            },
            {
                "_key": "8",
                "scientific_name": "Bacillus subtilis 168",
                "rank": "no rank",
                "strain": True,
            },
        ]
        gtdb_taxon_docs = [
            {"_key": "1", "scientific_name": "Bacteria", "rank": "Domain"},
        ]
        child_docs = [
            {
                "_from": "ncbi_taxon/2",
                "_to": "ncbi_taxon/1",
                "from": "2",
                "to": "1",
                "id": "2",
            },
            {
                "_from": "ncbi_taxon/4",
                "_to": "ncbi_taxon/1",
                "from": "4",
                "to": "1",
                "id": "4",
            },
            {
                "_from": "ncbi_taxon/3",
                "_to": "ncbi_taxon/2",
                "from": "3",
                "to": "2",
                "id": "3",
            },
            {
                "_from": "ncbi_taxon/5",
                "_to": "ncbi_taxon/4",
                "from": "5",
                "to": "4",
                "id": "5",
            },
            {
                "_from": "ncbi_taxon/6",
                "_to": "ncbi_taxon/4",
                "from": "6",
                "to": "4",
                "id": "6",
            },
            {
                "_from": "ncbi_taxon/7",
                "_to": "ncbi_taxon/4",
                "from": "7",
                "to": "4",
                "id": "7",
            },
            # a few levels missing here
            {
                "_from": "ncbi_taxon/8",
                "_to": "ncbi_taxon/3",
                "from": "8",
                "to": "3",
                "id": "8",
            },
        ]
        obj_ver_docs = [
            _construct_ws_obj_ver(1, 1, 1, is_public=True),
            _construct_ws_obj_ver(1, 1, 2, is_public=True),
            _construct_ws_obj_ver(2, 1, 1, is_public=False),
        ]
        obj_docs = [
            _construct_ws_obj(1, 1, is_public=True),
            _construct_ws_obj(2, 1, is_public=False),
        ]
        obj_to_taxa_docs = [
            {
                "_from": "ws_object_version/1:1:1",
                "_to": "ncbi_taxon/1",
                "assigned_by": "assn1",
            },
            {
                "_from": "ws_object_version/1:1:2",
                "_to": "ncbi_taxon/1",
                "assigned_by": "assn2",
            },
            {
                "_from": "ws_object_version/2:1:1",
                "_to": "ncbi_taxon/1",
                "assigned_by": "assn2",
            },
        ]
        # Create workspace objects associated to taxa
        ws_docs = [
            _ws_defaults({"_key": "1", "is_public": True}),
            _ws_defaults({"_key": "2", "is_public": False}),
        ]
        ws_to_obj = [
            {"_from": "ws_workspace/1", "_to": "ws_object/1:1"},
            {"_from": "ws_workspace/2", "_to": "ws_object/2:1"},
        ]
        ws_type_version_docs = [
            {
                "_key": "KBaseGenomes.Genome-99.77",
                "module_name": "KBaseGenomes",
                "type_name": "Genome",
                "maj_ver": 99,
                "min_ver": 77,
            }
        ]
        ws_obj_instance_of_type_docs = [
            {
                "_from": "ws_object_version/1:1:1",
                "_to": "ws_type_version/KBaseGenomes.Genome-99.77",
            },
            {
                "_from": "ws_object_version/1:1:2",
                "_to": "ws_type_version/KBaseGenomes.Genome-99.77",
            },
        ]
        _create_delta_test_docs("ncbi_taxon", taxon_docs)
        _create_delta_test_docs("gtdb_taxon", gtdb_taxon_docs)
        _create_delta_test_docs("ncbi_child_of_taxon", child_docs, edge=True)
        create_test_docs("ws_obj_version_has_taxon", obj_to_taxa_docs)
        create_test_docs("ws_object", obj_docs)
        create_test_docs("ws_workspace", ws_docs)
        create_test_docs("ws_workspace_contains_obj", ws_to_obj)
        create_test_docs("ws_object_version", obj_ver_docs)
        create_test_docs("ws_obj_instance_of_type", ws_obj_instance_of_type_docs)
        create_test_docs("ws_type_version", ws_type_version_docs)

    def test_get_lineage_valid(self):
        """Test a valid query of taxon lineage."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_lineage"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "7",
                    "select": ["rank", "scientific_name"],
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 2)
        ranks = [r["rank"] for r in resp["results"]]
        names = [r["scientific_name"] for r in resp["results"]]
        self.assertEqual(ranks, ["Domain", "Phylum"])
        self.assertEqual(names, ["Bacteria", "Proteobacteria"])

    def test_get_children(self):
        """Test a valid query of taxon descendants."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_children"},
            data=json.dumps(
                {
                    "id": "1",
                    "ts": _NOW,
                    "search_text": "firmicutes,|proteobacteria",
                    "select": ["rank", "scientific_name"],
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertEqual(result["total_count"], 2)
        ranks = {r["rank"] for r in result["results"]}
        names = [r["scientific_name"] for r in result["results"]]
        self.assertEqual(ranks, {"Phylum"})
        self.assertEqual(names, ["Firmicutes", "Proteobacteria"])

    def test_get_children_cursor(self):
        """Test a valid query to get children with a cursor."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_children_cursor"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "1",
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        self.assertEqual(len(resp["results"]), 2)

    def test_siblings_valid(self):
        """Test a valid query for siblings."""
        # Querying from "Alphaproteobacteria"
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_siblings"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "5",
                    "select": ["rank", "scientific_name"],
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertEqual(result["total_count"], 2)
        ranks = {r["rank"] for r in result["results"]}
        names = [r["scientific_name"] for r in result["results"]]
        self.assertEqual(ranks, {"Class"})
        self.assertEqual(names, ["Deltaproteobacteria", "Gammaproteobacteria"])

    def test_siblings_root(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_siblings"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "1",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),  # Querying from "Bacteria"
        ).json()
        self.assertEqual(resp["results"][0]["total_count"], 0)

    def test_siblings_nonexistent_node(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_siblings"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "xyz",  # Nonexistent node
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["results"][0]["total_count"], 0)

    def test_search_sci_name_no_count(self):
        """Test a valid query to search sciname without a count."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "no_count": True,
                    "search_text": "prefix:bact",
                    "select": ["scientific_name"],
                    "sciname_field": "scientific_name",
                    "ranks": ["Domain"],
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertTrue("total_count" not in result)
        self.assertEqual(result["results"][0]["scientific_name"], "Bacteria")

    def test_search_sciname_prefix(self):
        """Test a query to search sciname."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "prefix:bact",
                    "select": ["scientific_name"],
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["results"][0]["scientific_name"], "Bacteria")

    def test_search_sciname_gtdb(self):
        """Test a search on scientific name against the gtdb taxonomy."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "prefix:bact",
                    "select": ["scientific_name"],
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "gtdb_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["results"][0]["scientific_name"], "Bacteria")

    def test_search_sciname_nonexistent(self):
        """Test a query to search sciname for empty results."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "xyzabc",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["results"][0]["total_count"], 0)

    def test_search_sciname_wrong_type(self):
        """Test a query to search sciname with the wrong type for the search_text param."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": 123,
                    "@taxon_coll": "ncbi_taxon",
                    "sciname_field": "scientific_name",
                }
            ),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["message"], "123 is not of type 'string'")

    def test_search_sciname_missing_search(self):
        """Test a query to search sciname with the search_text param missing."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps({"ts": _NOW, "@taxon_coll": "ncbi_taxon"}),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["message"], "'search_text' is a required property"
        )

    def test_search_sciname_more_complicated(self):
        """Test a query to search sciname with some more keyword options."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "prefix:gamma,|prefix:alpha,|prefix:delta",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        result = resp["results"][0]
        self.assertEqual(result["total_count"], 3)
        names = {r["scientific_name"] for r in result["results"]}
        self.assertEqual(
            names, {"Gammaproteobacteria", "Alphaproteobacteria", "Deltaproteobacteria"}
        )

    def test_search_sciname_offset_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "prefix:bact",
                    "offset": 100001,
                    "@taxon_coll": "ncbi_taxon",
                    "sciname_field": "scientific_name",
                }
            ),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["message"],
            "100001 is greater than the maximum of 100000",
        )

    def test_search_sciname_limit_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_search_sci_name"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "search_text": "prefix:bact",
                    "limit": 1001,
                    "@taxon_coll": "ncbi_taxon",
                    "sciname_field": "scientific_name",
                }
            ),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["message"], "1001 is greater than the maximum of 1000"
        )

    def test_search_sciname_limit_ranks_implicit_defaults(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=None,
            include_strains=None,
            expected_count=3,
            expected_sci_names={"Bacteria", "Bacilli", "Bacillus subtilis 168"},
        )

    def test_search_sciname_limit_ranks_explicit_defaults(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=[],
            include_strains=False,
            expected_count=3,
            expected_sci_names={"Bacteria", "Bacilli", "Bacillus subtilis 168"},
        )

    def test_search_sciname_limit_ranks_2(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=["Domain", "Class"],
            include_strains=None,
            expected_count=2,
            expected_sci_names={"Bacteria", "Bacilli"},
        )

    def test_search_sciname_limit_ranks_1(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=["Class"],
            include_strains=None,
            expected_count=1,
            expected_sci_names={"Bacilli"},
        )

    def test_search_sciname_limit_ranks_1_with_strain(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=["Class"],
            include_strains=True,
            expected_count=2,
            expected_sci_names={"Bacilli", "Bacillus subtilis 168"},
        )

    def test_search_sciname_limit_ranks_1_with_false_strain(self):
        """Test queries where the results are limited by the rank or strain flag."""
        _run_search_sciname(
            self,
            ranks=["Class"],
            include_strains=False,
            expected_count=1,
            expected_sci_names={"Bacilli"},
        )

    def test_select_fields(self):
        """Test that the 'select' works properly for one query."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_lineage"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "id": "7",
                    "select": ["rank"],
                    "@taxon_coll": "ncbi_taxon",
                    "@taxon_child_of": "ncbi_child_of_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 2)
        self.assertEqual(resp["results"], [{"rank": "Domain"}, {"rank": "Phylum"}])

    def test_fetch_taxon(self):
        """Test a valid query to fetch a taxon."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_fetch_taxon"},
            data=json.dumps({"ts": _NOW, "id": "1", "@taxon_coll": "ncbi_taxon"}),
        ).json()
        self.assertEqual(resp["count"], 1)
        self.assertEqual(resp["results"][0]["id"], "1")

    def test_get_associated_objs(self):
        """
        Test a valid query to get associated objects for a taxon.
        Two objects are public and one is private, so total_count will be 3 while only the public objects are returned.
        """
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_associated_ws_objects"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "taxon_id": "1",
                    "select_obj": ["_id", "type", "ws_info"],
                    "select_edge": ["assigned_by"],
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 1)
        results = resp["results"][0]
        self.assertEqual(results["total_count"], 3)
        self.assertEqual(len(results["results"]), 2)
        assignments = {ret["edge"]["assigned_by"] for ret in results["results"]}
        ids = {ret["ws_obj"]["_id"] for ret in results["results"]}
        self.assertEqual(assignments, {"assn1", "assn2"})
        self.assertEqual(ids, {"ws_object_version/1:1:1", "ws_object_version/1:1:2"})
        self.assertEqual(
            results["results"][0]["ws_obj"]["type"],
            {
                "type_name": "Genome",
                "module_name": "KBaseGenomes",
                "maj_ver": 99,
                "min_ver": 77,
                "_key": "KBaseGenomes.Genome-99.77",
            },
        )
        self.assertEqual(
            results["results"][0]["ws_obj"]["ws_info"],
            {
                "owner": "owner",
                "metadata": {"narrative_nice_name": "narrname"},
                "is_public": True,
                "mod_epoch": 1,
            },
        )

    def test_get_taxon_from_ws_obj(self):
        """Fetch the taxon vertex from a workspace versioned id."""
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_get_taxon_from_ws_obj"},
            data=json.dumps(
                {"ts": _NOW, "obj_ref": "1:1:1", "@taxon_coll": "ncbi_taxon"}
            ),
        ).json()
        self.assertEqual(resp["count"], 1)
        assert_subset(
            self,
            {"id": "1", "scientific_name": "Bacteria", "rank": "Domain"},
            resp["results"][0],
        )

    def test_fetch_taxon_by_sciname(self):
        """Test the ncbi_fetch_taxon_by_sciname query."""
        sciname = "Deltaproteobacteria"
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_fetch_taxon_by_sciname"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "sciname": "Deltaproteobacteria",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 1)
        assert_subset(
            self,
            {
                "id": "7",
                "scientific_name": sciname,
                "rank": "Class",
            },
            resp["results"][0],
        )

    def test_fetch_taxon_by_sciname_failures(self):
        """Test invalid cases for ncbi_fetch_taxon_by_sciname."""
        # No sciname
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_fetch_taxon_by_sciname"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["error"]["message"], "'sciname' is a required property")
        # No ts
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "ncbi_fetch_taxon_by_sciname"},
            data=json.dumps(
                {
                    "sciname": "Deltaproteobacteria",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["error"]["message"], "'ts' is a required property")
        # sciname not found
        resp = requests.post(
            _CONF["re_api_url"] + "/api/v1/query_results",
            params={"stored_query": "taxonomy_fetch_taxon_by_sciname"},
            data=json.dumps(
                {
                    "ts": _NOW,
                    "sciname": "xyzabc",
                    "sciname_field": "scientific_name",
                    "@taxon_coll": "ncbi_taxon",
                }
            ),
        ).json()
        self.assertEqual(resp["count"], 0)
        self.assertEqual(len(resp["results"]), 0)


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
    else:
        for doc in docs:
            doc["id"] = doc["_key"]
    for doc in docs:
        doc["expired"] = 9007199254740991
        doc["created"] = 0
    create_test_docs(coll_name, docs)
