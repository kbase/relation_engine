"""
Tests for stored queries involving a fulltext search:
* Generic fulltext_search (should be used with caution because it can be slow and timeout at 60s)
* Taxonomy taxonomy_search_species_strain
* Taxonomy taxonomy_search_species_strain_no_sort

The latter two are switched between depending on the length of the search text.
These stored query tests  are all bundled in one test file because their original purpose is to do a species/strain
name search on the ncbi_taxon collection

These tests run within the re_api docker image, and require access to the ArangoDB, auth, and workspace images.
"""
import json
import time
import unittest
import requests
import os

from spec.test.helpers import (
    get_config,
    check_spec_test_env,
    create_test_docs,
)

_CONF = get_config()
_NOW = int(time.time() * 1000)
LIMIT = 20  # default

TEST_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/")
)

ncbi_taxon_fp = os.path.join(TEST_DATA_DIR, "ncbi_taxon.json")
with open(ncbi_taxon_fp) as fh:
    ncbi_taxa = json.load(fh)

# scinames_test_all are all the test scinames
scinames_test_all = [
    # --- Token preceded by punctuation ---
    "Lactobacillus sp. 'thermophilus'",
    "Rabbit fibroma virus (strain Kasza)",
    "'Prunus dulcis' phytoplasma",
    # --- Tokens joined by punctuation ---
    "Lactococcus phage 936 group phage Phi13.16",
    "Pseudogobio cf. esocinus CBM:ZF:12684",
    "Klebsormidium sp. BIOTA 14615.5a",
    # --- Misc gnarly ---
    "Influenza C virus (C/PIG/Beijing/439/1982)",
    "Bovine herpesvirus type 1.1 (strain P8-2)",
    "Porcine transmissible gastroenteritis coronavirus strain FS772/70",
    "Salmonella enterica subsp. houtenae serovar 16:z4,z32:--",
    "Influenza A virus PX8-XIII(A/USSR/90/77(H1N1)xA/Pintail Duck/Primorie/695/76(H2N3))",
    "Influenza B virus (B/Ann Arbor/1/1966 [cold-adapted and wild- type])",
    # --- Prefix 1 ---
    "Vaccinia virus WR 65-16",
    "Dengue virus 2 Jamaica/1409/1983",
    "Dengue virus 2 Thailand/NGS-C/1944",
    # --- Dups (techinically only applicable to live data) ---
    "environmental samples",
    "Listeria sp. FSL_L7-0091",
    "Listeria sp. FSL_L7-1519",
    # --- Misc ---
    "Norovirus GII.9",
    "Corticiaceae sp.",
    "Escherichia coli",
]
# scinames_test_latest are the test scinames that are compatible with a current timestamp
scinames_test_latest = [
    "Lactobacillus sp. 'thermophilus'",
    "Rabbit fibroma virus (strain Kasza)",
    "'Prunus dulcis' phytoplasma",
    "Lactococcus phage 936 group phage Phi13.16",
    "Influenza C virus (C/PIG/Beijing/439/1982)",
    "Bovine herpesvirus type 1.1 (strain P8-2)",
    "Porcine transmissible gastroenteritis coronavirus strain FS772/70",
    "Salmonella enterica subsp. houtenae serovar 16:z4,z32:--",
    "Influenza A virus PX8-XIII(A/USSR/90/77(H1N1)xA/Pintail Duck/Primorie/695/76(H2N3))",
    "Influenza B virus (B/Ann Arbor/1/1966 [cold-adapted and wild- type])",
    "Vaccinia virus WR 65-16",
    "Dengue virus 2 Jamaica/1409/1983",
    "Dengue virus 2 Thailand/NGS-C/1944",
    "environmental samples",
    "Listeria sp. FSL_L7-0091",
    "Listeria sp. FSL_L7-1519",
    "Corticiaceae sp.",
    "Escherichia coli",
]


class TestTaxonomySearchSpeciesStrainStoredQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_spec_test_env()
        create_test_docs("ncbi_taxon", ncbi_taxa)

    def test_ncbi_taxon_scinames(self):
        """Happy path"""
        for sciname in scinames_test_all:
            _taxonomy_search_species_strain_queries(
                self,
                taxon_coll="ncbi_taxon",
                sciname_field="scientific_name",
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                offset=None,
                limit=LIMIT,
                select="scientific_name",
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_null_bind_params(self):
        """Leave off parameters"""
        for sciname in scinames_test_all:
            _taxonomy_search_species_strain_queries(
                self,
                taxon_coll="ncbi_taxon",
                sciname_field="scientific_name",
                search_text=sciname,
                ts=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_fully_specified_bind_params(self):
        """Specify all parameters"""
        for sciname in scinames_test_all:
            _taxonomy_search_species_strain_queries(
                self,
                taxon_coll="ncbi_taxon",
                sciname_field="scientific_name",
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                offset=0,
                limit=LIMIT,
                select=["id", "scientific_name"],
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_extra_params(self):
        """Extra params not in spec/aql"""
        _taxonomy_search_species_strain_queries(
            self,
            taxon_coll="ncbi_taxon",
            sciname_field="scientific_name",
            search_text="esch",
            ts=None,
            offset=0,
            limit=LIMIT,
            select=["id", "scientific_name"],
            extra_unused_param=42,
            # ---
            expect_error=("Additional properties are not allowed"),
        )

    def test_validation_fail(self):
        _taxonomy_search_species_strain_queries(
            self,
            taxon_coll=[],
            sciname_field=42,
            search_text={"hi": 1},
            ts=None,
            offset=None,
            limit=None,
            select=None,
            # ---
            expect_error="[] is not of type 'string'",
        )

    def test_aql_error(self):
        for sciname in scinames_test_all:
            _taxonomy_search_species_strain_queries(
                self,
                taxon_coll="ncbi_taxon",
                sciname_field="fake_attrkey",
                search_text=sciname,
                ts=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=True,
            )

    def test_no_hit(self):
        for sciname in scinames_test_all:
            _taxonomy_search_species_strain_queries(
                self,
                taxon_coll="ncbi_taxon",
                sciname_field="scientific_name",
                search_text=sciname[::-1],
                ts=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=False,
                expect_hit=False,
                expected_hits=[],
            )

    def test_prefix_hit(self):
        """Test search text len being lte 3"""
        _taxonomy_search_species_strain_queries(
            self,
            taxon_coll="ncbi_taxon",
            sciname_field="scientific_name",
            search_text="inf",
            ts=None,
            offset=None,
            limit=None,
            select=None,
            # ---
            expect_error=False,
            expect_hit=False,
            expected_hits=[
                "Influenza A virus PX8-XIII(A/USSR/90/77(H1N1)xA/Pintail Duck/Primorie/695/76(H2N3))",
                "Influenza C virus (C/PIG/Beijing/439/1982)",
                "Influenza B virus (B/Ann Arbor/1/1966 [cold-adapted and wild- type])",
                "Influenza B virus (B/Brisbane/FSS700/2017)",
            ],
        )


class TestFulltextSearchStoredQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_spec_test_env()
        create_test_docs("ncbi_taxon", ncbi_taxa)

    def test_ncbi_taxon_scinames(self):
        """Happy path"""
        for sciname in scinames_test_all:
            _fulltext_search_query(
                self,
                coll="ncbi_taxon",
                search_attrkey="scientific_name",
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                filter_attr_expr=[
                    {"rank": "species"},
                    {"rank": "strain"},
                    {"strain": True},
                ],
                offset=None,
                limit=LIMIT,
                select="scientific_name",
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_null_bind_params(self):
        """Leave off parameters"""
        for sciname in scinames_test_all:
            _fulltext_search_query(
                self,
                coll="ncbi_taxon",
                search_attrkey="scientific_name",
                search_text=sciname,
                ts=None,
                filter_attr_expr=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_fully_specified_bind_params(self):
        """Specify all parameters"""
        for sciname in scinames_test_all:
            _fulltext_search_query(
                self,
                coll="ncbi_taxon",
                search_attrkey="scientific_name",
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                filter_attr_expr=[
                    {"rank": "species"},
                    {"rank": "strain"},
                    {"strain": True},
                ],
                offset=0,
                limit=LIMIT,
                select=["id", "scientific_name"],
                # ---
                expect_error=False,
                expect_hit=True,
            )

    def test_extra_params(self):
        """Extra params not in spec/aql"""
        _fulltext_search_query(
            self,
            coll="ncbi_taxon",
            search_attrkey="scientific_name",
            search_text="esch",
            ts=None,
            filter_attr_expr=[
                {"rank": "species"},
                {"rank": "strain"},
                {"strain": True},
            ],
            offset=0,
            limit=LIMIT,
            select=["id", "scientific_name"],
            extra_unused_param=42,
            # ---
            expect_error=("Additional properties are not allowed"),
        )

    def test_validation_fail(self):
        _fulltext_search_query(
            self,
            coll=[],
            search_attrkey=42,
            search_text={"hi": 1},
            ts=None,
            filter_attr_expr=None,
            offset=None,
            limit=None,
            select=None,
            # ---
            expect_error="[] is not of type 'string'",
        )

    def test_aql_error(self):
        for sciname in scinames_test_all:
            _fulltext_search_query(
                self,
                coll="ncbi_taxon",
                search_attrkey="fake_attrkey",
                search_text=sciname,
                ts=None,
                filter_attr_expr=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=True,
            )

    def test_no_hit(self):
        for sciname in scinames_test_all:
            _fulltext_search_query(
                self,
                coll="ncbi_taxon",
                search_attrkey="scientific_name",
                search_text=sciname[::-1],
                ts=None,
                filter_attr_expr=None,
                offset=None,
                limit=None,
                select=None,
                # ---
                expect_error=False,
                expect_hit=False,
                expected_hits=[],
            )


# --- Test helpers ---


def _switch_taxonomy_search_species_strain_queries(search_text):
    return (
        "taxonomy_search_species_strain_no_sort"
        if len(search_text) <= 3
        else "taxonomy_search_species_strain"
    )


def _taxonomy_search_species_strain_queries(
    self,
    taxon_coll,
    sciname_field,
    search_text,
    ts,
    offset,
    limit,
    select,
    expect_error=False,
    expect_hit=True,
    expected_hits=None,
    **kw,  # for testing passing disallowed properties
):
    """
    Run query against ArangoDB server
    """
    data = {
        "@taxon_coll": taxon_coll,
        "sciname_field": sciname_field,
        "search_text": search_text,
        "ts": ts,
        "offset": offset,
        "limit": limit,
        "select": select,
        **kw,
    }
    stored_query = _switch_taxonomy_search_species_strain_queries(search_text)
    _check_query_results(
        self,
        data,
        stored_query,
        sciname_field,
        search_text,
        limit,
        expect_error,
        expect_hit,
        expected_hits,
    )


def _fulltext_search_query(
    self,
    coll,
    search_attrkey,
    search_text,
    ts,
    filter_attr_expr,
    offset,
    limit,
    select,
    expect_error=False,
    expect_hit=True,
    expected_hits=None,
    **kw,  # for testing passing disallowed properties
):
    """
    Run query against ArangoDB server
    """
    data = {
        "@coll": coll,
        "search_attrkey": search_attrkey,
        "search_text": search_text,
        "ts": ts,
        "filter_attr_expr": filter_attr_expr,
        "offset": offset,
        "limit": limit,
        "select": select,
        **kw,
    }
    stored_query = "fulltext_search"
    _check_query_results(
        self,
        data,
        stored_query,
        search_attrkey,
        search_text,
        limit,
        expect_error,
        expect_hit,
        expected_hits,
    )


def _check_query_results(
    self,
    data,
    stored_query,
    search_attrkey,
    search_text,
    limit,
    expect_error,
    expect_hit,
    expected_hits,
):
    resp = requests.post(
        _CONF["re_api_url"] + "/api/v1/query_results",
        params={"stored_query": stored_query},
        data=json.dumps(data),
    )

    if expect_error:
        self.assertIn("error", resp.json())
        if isinstance(expect_error, str):
            self.assertIn(expect_error, json.dumps(resp.json()))

    else:
        self.assertNotIn("error", resp.json(), json.dumps(resp.json(), indent=4))

        docs = resp.json()["results"]
        hits = [doc[search_attrkey] for doc in docs]
        if expect_hit:
            self.assertIn(search_text, hits, f"`{search_text}` not in `{hits}`")
            self.assertFalse(
                len(hits) == limit and len(set(hits) == 1)
            )  # check not just overflowing with dups
        else:
            self.assertNotIn(search_text, hits)

        if expected_hits is not None:
            self.assertCountEqual(expected_hits, hits)

    # Filter out null values
    # to see if their default null values would kick in properly
    data = {k: v for k, v in data.items() if v is not None}
    resp = requests.post(
        _CONF["re_api_url"] + "/api/v1/query_results",
        params={"stored_query": stored_query},
        data=json.dumps(data),
    )

    if expect_error:
        self.assertIn("error", resp.json())
        if isinstance(expect_error, str):
            self.assertIn(expect_error, json.dumps(resp.json()))

    else:
        self.assertNotIn("error", resp.json(), json.dumps(resp.json(), indent=4))

        docs = resp.json()["results"]
        hits = [doc[search_attrkey] for doc in docs]
        if expect_hit:
            self.assertIn(search_text, hits, f"`{search_text}` not in `{hits}`")
            self.assertFalse(
                len(hits) == limit and len(set(hits) == 1)
            )  # check not just overflowing with dups
        else:
            self.assertNotIn(search_text, hits)

        if expected_hits is not None:
            self.assertCountEqual(expected_hits, hits)
