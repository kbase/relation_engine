"""
Tests for the ncbi taxonomy stored queries.
"""
import json
import time
import unittest
import requests

from test.helpers import get_config
from test.stored_queries.helpers import create_test_docs

_CONF = get_config()
_NOW = int(time.time() * 1000)


class TestTaxonomy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Create test documents"""
        taxon_docs = [
            {'_key': '1', 'scientific_name': 'Bacteria', 'rank': 'Domain', 'strain': False},
            {'_key': '2', 'scientific_name': 'Firmicutes', 'rank': 'Phylum', 'strain': False},
            {'_key': '3', 'scientific_name': 'Bacilli', 'rank': 'Class', 'strain': False},
            {'_key': '4', 'scientific_name': 'Proteobacteria', 'rank': 'Phylum', 'strain': False},
            {'_key': '5', 'scientific_name': 'Alphaproteobacteria', 'rank': 'Class', 'strain': False},
            {'_key': '6', 'scientific_name': 'Gammaproteobacteria', 'rank': 'Class', 'strain': False},
            {'_key': '7', 'scientific_name': 'Deltaproteobacteria', 'rank': 'Class', 'strain': False},
            {'_key': '8', 'scientific_name': 'Bacillus subtilis 168', 'rank': 'no rank', 'strain': True},
        ]
        child_docs = [
            {'_from': 'ncbi_taxon/2', '_to': 'ncbi_taxon/1', 'from': '2', 'to': '1', 'id': '2'},
            {'_from': 'ncbi_taxon/4', '_to': 'ncbi_taxon/1', 'from': '4', 'to': '1', 'id': '4'},
            {'_from': 'ncbi_taxon/3', '_to': 'ncbi_taxon/2', 'from': '3', 'to': '2', 'id': '3'},
            {'_from': 'ncbi_taxon/5', '_to': 'ncbi_taxon/4', 'from': '5', 'to': '4', 'id': '5'},
            {'_from': 'ncbi_taxon/6', '_to': 'ncbi_taxon/4', 'from': '6', 'to': '4', 'id': '6'},
            {'_from': 'ncbi_taxon/7', '_to': 'ncbi_taxon/4', 'from': '7', 'to': '4', 'id': '7'},
            # a few levels missing here
            {'_from': 'ncbi_taxon/8', '_to': 'ncbi_taxon/3', 'from': '8', 'to': '3', 'id': '8'},
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
            {'_from': 'ws_object_version/1:1:1', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn1'},
            {'_from': 'ws_object_version/1:1:2', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn2'},
            {'_from': 'ws_object_version/2:1:1', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn2'},
        ]
        # Create workspace objects associated to taxa
        ws_docs = [
            _ws_defaults({'_key': '1', 'is_public': True}),
            _ws_defaults({'_key': '2', 'is_public': False}),
        ]
        ws_to_obj = [
            {'_from': 'ws_workspace/1', '_to': 'ws_object/1:1'},
            {'_from': 'ws_workspace/2', '_to': 'ws_object/2:1'},
        ]
        ws_type_version_docs = [
            {'_key': 'KBaseGenomes.Genome-99.77', 'module_name': 'KBaseGenomes',
             'type_name': 'Genome', 'maj_ver': 99, 'min_ver': 77}
        ]
        ws_obj_instance_of_type_docs = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_type_version/KBaseGenomes.Genome-99.77'},
            {'_from': 'ws_object_version/1:1:2', '_to': 'ws_type_version/KBaseGenomes.Genome-99.77'}
        ]
        _create_delta_test_docs('ncbi_taxon', taxon_docs)
        _create_delta_test_docs('ncbi_child_of_taxon', child_docs, edge=True)
        create_test_docs('ws_obj_version_has_taxon', obj_to_taxa_docs)
        create_test_docs('ws_object', obj_docs)
        create_test_docs('ws_workspace', ws_docs)
        create_test_docs('ws_workspace_contains_obj', ws_to_obj)
        create_test_docs('ws_object_version', obj_ver_docs)
        create_test_docs('ws_obj_instance_of_type', ws_obj_instance_of_type_docs)
        create_test_docs('ws_type_version', ws_type_version_docs)

    def test_get_lineage_valid(self):
        """Test a valid query of taxon lineage."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'taxonomy_get_lineage'},
            data=json.dumps({
                'ts': _NOW,
                'id': '7',
                'select': ['rank', 'scientific_name'],
                '@taxon_coll': 'ncbi_taxon',
                '@child_of_coll': 'ncbi_child_of_taxon'
            }),
        ).json()
        self.assertEqual(resp['count'], 2)
        ranks = [r['rank'] for r in resp['results']]
        names = [r['scientific_name'] for r in resp['results']]
        self.assertEqual(ranks, ['Domain', 'Phylum'])
        self.assertEqual(names, ['Bacteria', 'Proteobacteria'])


# -- Test helpers

def _run_search_sciname(self, ranks, include_strains, expected_count, expected_sci_names):
    """
    Helper to run the ncbi_taxon_search_sci_name query and make some standard
    assertions on the response.
    """
    data = {
        'ts': _NOW,
        'search_text': "prefix:bac"
    }
    if ranks is not None:
        data['ranks'] = ranks
    if include_strains is not None:
        data['include_strains'] = include_strains
    resp = requests.post(
        _CONF['re_api_url'] + '/api/v1/query_results',
        params={'stored_query': 'ncbi_taxon_search_sci_name'},
        data=json.dumps(data)
        ).json()
    result = resp['results'][0]
    self.assertEqual(result['total_count'], expected_count)
    names = {r['scientific_name'] for r in result['results']}
    self.assertEqual(names, expected_sci_names)


def _ws_defaults(data):
    """Set some defaults for the required workspace fields."""
    defaults = {
        'owner': 'owner',
        'max_obj_id': 1,
        'lock_status': 'n',
        'name': 'wsname',
        'mod_epoch': 1,
        'is_public': True,
        'is_deleted': False,
        'metadata': {'narrative_nice_name': 'narrname'},
    }
    # Merge the data with the above defaults
    return dict(defaults, **data)


def _construct_ws_obj_ver(wsid, objid, ver, is_public=False):
    """Test helper to create a ws_object_version vertex."""
    return {
        '_key': f"{wsid}:{objid}:{ver}",
        'workspace_id': wsid,
        'object_id': objid,
        'version': ver,
        'name': f'obj_name{objid}',
        'hash': 'xyz',
        'size': 100,
        'epoch': 0,
        'deleted': False,
        'is_public': is_public,
    }


def _construct_ws_obj(wsid, objid, is_public=False):
    """Test helper to create a ws_object vertex."""
    return {
        '_key': f"{wsid}:{objid}",
        'workspace_id': wsid,
        'object_id': objid,
        'deleted': False,
        'is_public': is_public,
    }


def _create_delta_test_docs(coll_name, docs, edge=False):
    """Add in delta required fields."""
    if edge:
        for doc in docs:
            # Replicate the time-travel system by just setting 'from' and 'to' to the keys
            doc['from'] = doc['_from'].split('/')[1]
            doc['to'] = doc['_to'].split('/')[1]
    else:
        for doc in docs:
            doc['id'] = doc['_key']
    for doc in docs:
        doc['expired'] = 9007199254740991
        doc['created'] = 0
    create_test_docs(coll_name, docs)
