"""
Tests the boolean flags on NCBI Taxon nodes when used in conjunction with full text search, e.g.
in the queries:
- taxonomy_search_species_strain
- taxonomy_search_species_strain_no_sort

Note these tests omit several fields from the records that are not relevant to the queries.
"""

import os
import yaml
from arango import ArangoClient
from frozendict import frozendict  # type: ignore[attr-defined]
from pathlib import Path
from pytest import fixture
from relation_engine_server.utils.config import get_config
from relation_engine_client import REClient

_QUERY_SORT = "taxonomy_search_species_strain"
_QUERY_NO_SORT = "taxonomy_search_species_strain_no_sort"


@fixture(scope="module")
def conf():
    config = get_config()
    config["re_api_url"] = os.environ.get("RE_API_URL", "http://localhost:5000")

    yield config


@fixture(scope="module")
def spec(conf):
    # There should probably be some sort of abstraction here so this isn't hard coded, but AFAICT
    # it doesn't exist in the code base at this point. Add later maybe. At least the tests
    # should fail if the file is renamed / altered
    schemapath = Path(conf["spec_paths"]["collections"]) / "ncbi" / "ncbi_taxon.yaml"
    with open(schemapath) as fd:
        spec = yaml.safe_load(fd)
    yield spec


@fixture(scope="module")
def db(conf, spec):
    # This is set to the "_system" db by the get_config() method defaults, which are used to start
    # up the RE API in the docker tests...
    arango = ArangoClient(conf["db_url"])
    db = arango.db(conf["db_name"])

    yield db

    # clean up for tests in other modules that might be using the same db / collection
    _clear_collection(db, spec["name"])


@fixture(scope="module")
def re_client(conf):
    re_c = REClient(conf["re_api_url"], "non_admin_token")
    yield re_c


@fixture()
def coll(db, spec):
    yield _clear_collection(db, spec["name"])


def _clear_collection(db, coll_name):
    collection = db.collection(coll_name)
    collection.truncate()

    return collection


COVID_NO_RANK_STRAIN = {
    "_key": "89_2022-01-01",
    "id": "89",
    "scientific_name": "Covid in yer earhole",
    "rank": "no rank",
    "strain": True,
    "ncbi_taxon_id": 89,
    "created": 1,
    "expired": 100000000000,
}
COVID_GENUS = {
    "_key": "42_2022-01-01",
    "id": "42",
    "scientific_name": "Covid genus",
    "rank": "genus",
    "strain": False,
    "ncbi_taxon_id": 42,
    "created": 1,
    "expired": 100000000000,
}
COVID_SPECIES = {
    "_key": "44_2022-01-01",
    "id": "44",
    "scientific_name": "Covid species",
    "rank": "species",
    "strain": False,
    "ncbi_taxon_id": 44,
    "created": 1,
    "expired": 100000000000,
}
COVID_STRAIN = {
    "_key": "46_2022-01-01",
    "id": "46",
    "scientific_name": "Covid strain",
    "rank": "clade",
    "strain": True,
    "ncbi_taxon_id": 46,
    "created": 1,
    "expired": 100000000000,
}
COV_SPECIES = {
    "_key": "48_2022-01-01",
    "id": "48",
    "scientific_name": "Cov",
    "rank": "species",
    "strain": False,
    "ncbi_taxon_id": 48,
    "created": 1,
    "expired": 100000000000,
}
COVID_NO_RANK_SOB_TRUE = {
    "_key": "6_2022-01-01",
    "id": "6",
    "scientific_name": "I've got Covid",
    "rank": "no rank",
    "strain": False,
    "species_or_below": True,
    "ncbi_taxon_id": 6,
    "created": 1,
    "expired": 100000000000,
}
COVID_CLADE_SOB_TRUE = {
    "_key": "7_2022-01-01",
    "id": "7",
    "scientific_name": "Covidiot",
    "rank": "clade",
    "strain": False,
    "species_or_below": True,
    "ncbi_taxon_id": 7,
    "created": 1,
    "expired": 100000000000,
}
COVID_SPECIES_SOB_TRUE = {
    "_key": "8_2022-01-01",
    "id": "8",
    "scientific_name": "I, too, have Covid on my bottom",
    "rank": "species",
    "strain": False,
    "species_or_below": True,
    "ncbi_taxon_id": 8,
    "created": 1,
    "expired": 100000000000,
}
COVID_GENUS_SOB_FALSE = {
    "_key": "9_2022-01-01",
    "id": "9",
    "scientific_name": "Covidiously smarmy",
    "rank": "genus",
    "strain": False,
    "species_or_below": False,
    "ncbi_taxon_id": 9,
    "created": 1,
    "expired": 100000000000,
}


def test_missing_species_or_below_flag_covid(coll, re_client):
    """
    Test queries against documents that don't have the species_or_below flag at all.
    """
    coll.import_bulk(
        [COVID_NO_RANK_STRAIN, COVID_GENUS, COVID_SPECIES, COVID_STRAIN, COV_SPECIES]
    )

    expected = _add_id(coll.name, [COVID_NO_RANK_STRAIN, COVID_SPECIES, COVID_STRAIN])

    _check_queries(re_client, coll.name, expected, "Covid")


def test_missing_species_or_below_flag_cov(coll, re_client):
    """
    Test queries against documents that don't have the species_or_below flag at all.
    """
    coll.import_bulk(
        [COVID_NO_RANK_STRAIN, COVID_GENUS, COVID_SPECIES, COVID_STRAIN, COV_SPECIES]
    )

    expected = _add_id(
        coll.name, [COV_SPECIES, COVID_NO_RANK_STRAIN, COVID_SPECIES, COVID_STRAIN]
    )

    _check_queries(re_client, coll.name, expected, "Cov")


def test_with_species_or_below_flag_covid(coll, re_client):
    """
    Test queries against documents that have the new species_or_below flag.
    """
    coll.import_bulk(
        [
            COVID_NO_RANK_SOB_TRUE,
            COV_SPECIES,
            COVID_NO_RANK_STRAIN,
            COVID_GENUS,
            COVID_CLADE_SOB_TRUE,
            COVID_SPECIES,
            COVID_SPECIES_SOB_TRUE,
            COVID_STRAIN,
            COVID_GENUS_SOB_FALSE,
        ]
    )
    expected = _add_id(
        coll.name,
        [
            COVID_NO_RANK_STRAIN,
            COVID_SPECIES,
            COVID_STRAIN,
            COVID_CLADE_SOB_TRUE,
            COVID_SPECIES_SOB_TRUE,
            COVID_NO_RANK_SOB_TRUE,
        ],
    )
    _check_queries(re_client, coll.name, expected, "Covid")


def test_with_species_or_below_flag_cov(coll, re_client):
    """
    Test queries against documents that have the new species_or_below.
    """
    coll.import_bulk(
        [
            COVID_NO_RANK_SOB_TRUE,
            COV_SPECIES,
            COVID_NO_RANK_STRAIN,
            COVID_GENUS,
            COVID_CLADE_SOB_TRUE,
            COVID_SPECIES,
            COVID_SPECIES_SOB_TRUE,
            COVID_STRAIN,
            COVID_GENUS_SOB_FALSE,
        ]
    )
    expected = _add_id(
        coll.name,
        [
            COV_SPECIES,
            COVID_NO_RANK_STRAIN,
            COVID_SPECIES,
            COVID_STRAIN,
            COVID_CLADE_SOB_TRUE,
            COVID_SPECIES_SOB_TRUE,
            COVID_NO_RANK_SOB_TRUE,
        ],
    )
    _check_queries(re_client, coll.name, expected, "Cov")


def _add_id(coll_name, list_o_dicts):
    return [d | {"_id": f"{coll_name}/{d['_key']}"} for d in list_o_dicts]


def _check_queries(re_client, coll_name, expected_sorted, search_text):
    res = _run_query(re_client, coll_name, _QUERY_NO_SORT, search_text)
    assert set(_freeze(res)) == set(_freeze(expected_sorted))

    res = _run_query(re_client, coll_name, _QUERY_SORT, search_text)
    assert res == expected_sorted


def _freeze(list_o_dicts):
    return [frozendict(d) for d in list_o_dicts]


def _run_query(re_client, coll_name, query, search_text):
    res = re_client.stored_query(
        query,
        {
            "@taxon_coll": coll_name,
            "search_text": search_text,
            "sciname_field": "scientific_name",
        },
    )["results"]
    for r in res:
        del r["_rev"]
    return res
