"""g
Tests for the generic fulltext search

These tests run within the re_api docker image, and require access to the ArangoDB, auth, and workspace images.
"""
import json
import time
import unittest
import requests
import os
import pytest

from relation_engine_server.utils.arango_client import ArangoServerError
from spec.test.helpers import (
    get_config,
    check_spec_test_env,
    create_test_docs,
)

_CONF = get_config()
_NOW = int(time.time() * 1000)
LIMIT = 20  # default

TEST_DATA_DIR = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '../data/'
    )
)

ncbi_taxon_fp = os.path.join(TEST_DATA_DIR, 'ncbi_taxon.json')
with open(ncbi_taxon_fp) as fh:
    ncbi_taxa = json.load(fh)

# scinames_test_all are all the test scinames
scinames_test_all = [
    # --- Token preceded by punctuation ---
    "Lactobacillus sp. 'thermophilus'",
    "Rabbit fibroma virus (strain Kasza)",
    "'Prunus dulcis' phytoplasma",
    # --- Tokens joined by punctuation
    'Lactococcus phage 936 group phage Phi13.16',
    'Pseudogobio cf. esocinus CBM:ZF:12684',
    'Klebsormidium sp. BIOTA 14615.5a',
    # --- Misc gnarly ---
    'Influenza C virus (C/PIG/Beijing/439/1982)',
    'Bovine herpesvirus type 1.1 (strain P8-2)',
    'Porcine transmissible gastroenteritis coronavirus strain FS772/70',
    'Salmonella enterica subsp. houtenae serovar 16:z4,z32:--',
    'Influenza A virus PX8-XIII(A/USSR/90/77(H1N1)xA/Pintail Duck/Primorie/695/76(H2N3))',
    'Influenza B virus (B/Ann Arbor/1/1966 [cold-adapted and wild- type])',
    # --- Prefix 1 ---
    'Vaccinia virus WR 65-16',
    'Dengue virus 2 Jamaica/1409/1983',
    'Dengue virus 2 Thailand/NGS-C/1944',
    # --- Dups ---
    'environmental samples',
    'Listeria sp. FSL_L7-0091',
    'Listeria sp. FSL_L7-1519',
    # --- Misc ---
    'Norovirus GII.9',
    'Corticiaceae sp.',
    'Escherichia coli',
]
# scinames_test_latest are the test scinames that are compatible with a current timestamp
scinames_test_latest = [
    "Lactobacillus sp. 'thermophilus'",
    'Rabbit fibroma virus (strain Kasza)',
    "'Prunus dulcis' phytoplasma",
    'Lactococcus phage 936 group phage Phi13.16',
    'Influenza C virus (C/PIG/Beijing/439/1982)',
    'Bovine herpesvirus type 1.1 (strain P8-2)',
    'Porcine transmissible gastroenteritis coronavirus strain FS772/70',
    'Salmonella enterica subsp. houtenae serovar 16:z4,z32:--',
    'Influenza A virus PX8-XIII(A/USSR/90/77(H1N1)xA/Pintail Duck/Primorie/695/76(H2N3))',
    'Influenza B virus (B/Ann Arbor/1/1966 [cold-adapted and wild- type])',
    'Vaccinia virus WR 65-16',
    'Dengue virus 2 Jamaica/1409/1983',
    'Dengue virus 2 Thailand/NGS-C/1944',
    'environmental samples',
    'Listeria sp. FSL_L7-0091',
    'Listeria sp. FSL_L7-1519',
    'Corticiaceae sp.',
    'Escherichia coli'
]


class Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_spec_test_env(do_download_specs=True)
        create_test_docs('ncbi_taxon', ncbi_taxa)

    def test_ncbi_taxon_scinames(self):
        """Happy path"""
        for sciname in scinames_test_all:
            _fulltext_query__expect_hit(
                self,
                coll='ncbi_taxon',
                search_attrkey='scientific_name',
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                filter_attr_expr=[{'rank': 'species'}, {'rank': 'strain'}, {'strain': True}],
                offset=None,
                limit=LIMIT,
                select='scientific_name'
            )

    def test_null_bind_params(self):
        """Leave off parameters"""
        for sciname in scinames_test_all:
            _fulltext_query__expect_hit(
                self,
                coll='ncbi_taxon',
                search_attrkey='scientific_name',
                search_text=sciname,
                ts=None,
                filter_attr_expr=None,
                offset=None,
                limit=None,
                select=None,
            )

    def test_fully_specified_bind_params(self):
        """Specify all parameters"""
        for sciname in scinames_test_all:
            _fulltext_query__expect_hit(
                self,
                coll='ncbi_taxon',
                search_attrkey='scientific_name',
                search_text=sciname,
                ts=_NOW if sciname in scinames_test_latest else None,
                filter_attr_expr=[{'rank': 'species'}, {'rank': 'strain'}, {'strain': True}],
                offset=0,
                limit=LIMIT,
                select=['id', 'scientific_name']
            )

    def test_stored_query_validation_fail(self):
        for sciname in scinames_test_all:
            with self.assertRaises(Exception) as e:
                print('\n#e', e)
                _fulltext_query__expect_hit(
                    self,
                    coll=None,
                    search_attrkey=None,
                    search_text=None,
                    ts=None,
                    filter_attr_expr=None,
                    offset=None,
                    limit=None,
                    select=None,
                )

    def test_arango_error(self):
        for sciname in scinames_test_all:
            with self.assertRaises(ArangoServerError):
                _fulltext_query__expect_hit(
                    self,
                    coll='ncbi_taxon',
                    search_attrkey='fake_attrkey',
                    search_text=sciname,
                    ts=None,
                    filter_attr_expr=None,
                    offset=None,
                    limit=None,
                    select=None,
                )

    def test_no_hit(self):
        for sciname in scinames_test_all:
            with self.assertRaises(AssertionError):
                _fulltext_query__expect_hit(
                    self,
                    coll='ncbi_taxon',
                    search_attrkey='scientific_name',
                    search_text=sciname[::-1],
                    ts=None,
                    filter_attr_expr=None,
                    offset=None,
                    limit=None,
                    select=None,
                )


# --- Test helpers ---


def _fulltext_query__expect_hit(
    self,
    coll,
    search_attrkey,
    search_text,
    ts,
    filter_attr_expr,
    offset,
    limit,
    select,
):
    """
    Helper to run the taxonomy_search_sci_name query and make some standard
    assertions on the response.
    """
    data = {
        '@coll': coll,
        'search_attrkey': search_attrkey,
        'search_text': search_text,
        'ts': ts,
        'filter_attr_expr': filter_attr_expr,
        'offset': offset,
        'limit': limit,
        'select': select,
    }
    resp = requests.post(
        _CONF["re_api_url"] + "/api/v1/query_results",
        params={"stored_query": "fulltext_search"},
        data=json.dumps(data),
    )

    if "error" in resp.json():
        raise ArangoServerError(resp.text)

    docs = resp.json()['results']
    hits = [doc[search_attrkey] for doc in docs]
    self.assertIn(search_text, hits)
    self.assertFalse(len(hits) == limit and len(set(hits) == 1))  # check not just overflowing with dups
