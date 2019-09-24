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


def _construct_ws_obj(wsid, objid, ver, is_public=False):
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


class TestNcbiTax(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Create test documents"""
        taxon_docs = [
            {'_key': '1', 'scientific_name': 'Bacteria', 'rank': 'Domain'},
            {'_key': '2', 'scientific_name': 'Firmicutes', 'rank': 'Phylum'},
            {'_key': '3', 'scientific_name': 'Bacilli', 'rank': 'Class'},
            {'_key': '4', 'scientific_name': 'Proteobacteria', 'rank': 'Phylum'},
            {'_key': '5', 'scientific_name': 'Alphaproteobacteria', 'rank': 'Class'},
            {'_key': '6', 'scientific_name': 'Gammaproteobacteria', 'rank': 'Class'},
            {'_key': '7', 'scientific_name': 'Deltaproteobacteria', 'rank': 'Class'},
        ]
        child_docs = [
            {'_from': 'ncbi_taxon/2', '_to': 'ncbi_taxon/1', 'child_type': 't'},
            {'_from': 'ncbi_taxon/4', '_to': 'ncbi_taxon/1', 'child_type': 't'},
            {'_from': 'ncbi_taxon/3', '_to': 'ncbi_taxon/2', 'child_type': 't'},
            {'_from': 'ncbi_taxon/5', '_to': 'ncbi_taxon/4', 'child_type': 't'},
            {'_from': 'ncbi_taxon/6', '_to': 'ncbi_taxon/4', 'child_type': 't'},
            {'_from': 'ncbi_taxon/7', '_to': 'ncbi_taxon/4', 'child_type': 't'},
        ]
        obj_docs = [
            _construct_ws_obj(1, 1, 1, is_public=True),
            _construct_ws_obj(1, 1, 2, is_public=True),
            _construct_ws_obj(2, 1, 1, is_public=False),
        ]
        obj_to_taxa_docs = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn1'},
            {'_from': 'ws_object_version/1:1:2', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn2'},
            {'_from': 'ws_object_version/2:1:1', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn2'},
        ]
        # Create workspace objects associated to taxa
        ws_docs = [{'_key': '1', 'is_public': True}, {'_key': '2', 'is_public': False}]
        ws_to_obj = [
            {'_from': 'ws_workspace/1', '_to': 'ws_object_version/1:1:1'},
            {'_from': 'ws_workspace/1', '_to': 'ws_object_version/1:1:2'},
            {'_from': 'ws_workspace/2', '_to': 'ws_object_version/2:1:1'},
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
        _create_delta_test_docs('ws_object_version', obj_docs)
        _create_delta_test_docs('ws_obj_version_has_taxon', obj_to_taxa_docs, edge=True)
        _create_delta_test_docs('ws_workspace', ws_docs)
        _create_delta_test_docs('ws_workspace_contains_obj', ws_to_obj, edge=True)
        create_test_docs('ws_obj_instance_of_type', ws_obj_instance_of_type_docs)
        create_test_docs('ws_type_version', ws_type_version_docs)

    def test_get_lineage_valid(self):
        """Test a valid query of taxon lineage."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_lineage'},
            data=json.dumps({'ts': _NOW, 'id': '7', 'select': ['rank', 'scientific_name']}),
        ).json()
        self.assertEqual(resp['count'], 2)
        ranks = [r['rank'] for r in resp['results']]
        names = [r['scientific_name'] for r in resp['results']]
        self.assertEqual(ranks, ['Domain', 'Phylum'])
        self.assertEqual(names, ['Bacteria', 'Proteobacteria'])

    def test_get_children(self):
        """Test a valid query of taxon descendants."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_children'},
            data=json.dumps({
                'id': '1',
                'ts': _NOW,
                'search_text': 'firmicutes,|proteobacteria',
                'select': ['rank', 'scientific_name']
            }),
        ).json()
        result = resp['results'][0]
        self.assertEqual(result['total_count'], 2)
        ranks = {r['rank'] for r in result['results']}
        names = [r['scientific_name'] for r in result['results']]
        self.assertEqual(ranks, {'Phylum'})
        self.assertEqual(names, ['Firmicutes', 'Proteobacteria'])

    def test_get_children_cursor(self):
        """Test a valid query to get children with a cursor."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_children_cursor'},
            data=json.dumps({'ts': _NOW, 'id': '1'})
        ).json()
        self.assertEqual(len(resp['results']), 2)

    def test_siblings_valid(self):
        """Test a valid query for siblings."""
        # Querying from "Alphaproteobacteria"
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({
                'ts': _NOW,
                'id': '5',
                'select': ['rank', 'scientific_name']
            })
        ).json()
        result = resp['results'][0]
        self.assertEqual(result['total_count'], 2)
        ranks = {r['rank'] for r in result['results']}
        names = [r['scientific_name'] for r in result['results']]
        self.assertEqual(ranks, {'Class'})
        self.assertEqual(names, ['Deltaproteobacteria', 'Gammaproteobacteria'])

    def test_siblings_root(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({'ts': _NOW, 'id': '1'}),  # Querying from "Bacteria"
        ).json()
        self.assertEqual(resp['results'][0]['total_count'], 0)

    def test_siblings_nonexistent_node(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({'ts': _NOW, 'id': 'xyz'}),  # Nonexistent node
        ).json()
        self.assertEqual(resp['results'][0]['total_count'], 0)

    def test_search_sciname_prefix(self):
        """Test a query to search sciname."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW, 'search_text': 'prefix:bact', 'select': ['scientific_name']}),
        ).json()
        result = resp['results'][0]
        self.assertEqual(result['total_count'], 1)
        self.assertEqual(result['results'][0]['scientific_name'], 'Bacteria')

    def test_search_sciname_nonexistent(self):
        """Test a query to search sciname for empty results."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW, 'search_text': 'xyzabc'}),
        ).json()
        self.assertEqual(resp['results'][0]['total_count'], 0)

    def test_search_sciname_wrong_type(self):
        """Test a query to search sciname with the wrong type for the search_text param."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW, 'search_text': 123})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "123 is not of type 'string'")

    def test_search_sciname_missing_search(self):
        """Test a query to search sciname with the search_text param missing."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "'search_text' is a required property")

    def test_search_sciname_more_complicated(self):
        """Test a query to search sciname with some more keyword options."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({
                'ts': _NOW,
                'search_text': "prefix:gamma,|prefix:alpha,|prefix:delta"
            })
        ).json()
        result = resp['results'][0]
        self.assertEqual(result['total_count'], 3)
        names = {r['scientific_name'] for r in result['results']}
        self.assertEqual(names, {'Gammaproteobacteria', 'Alphaproteobacteria', 'Deltaproteobacteria'})

    def test_search_sciname_offset_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW, 'search_text': "prefix:bact", "offset": 100001})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "100001 is greater than the maximum of 100000")

    def test_search_sciname_limit_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'ts': _NOW, 'search_text': "prefix:bact", "limit": 1001})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "1001 is greater than the maximum of 1000")

    def test_select_fields(self):
        """Test that the 'select' works properly for one query."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_lineage'},
            data=json.dumps({'ts': _NOW, 'id': '7', 'select': ['rank']})
        ).json()
        self.assertEqual(resp['count'], 2)
        self.assertEqual(resp['results'], [
            {'rank': 'Domain'},
            {'rank': 'Phylum'}
        ])

    def test_fetch_taxon(self):
        """Test a valid query to fetch a taxon."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_fetch_taxon'},
            data=json.dumps({'ts': _NOW, 'id': '1'})
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['id'], '1')

    def test_get_associated_objs(self):
        """
        Test a valid query to get associated objects for a taxon.
        Two objects are public and one is private, so total_count will be 3 while only the public objects are returned.
        """
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_associated_ws_objects'},
            data=json.dumps({'ts': _NOW, 'taxon_id': '1', 'select_obj': ['_id', 'type'],
                             'select_edge': ['assigned_by']}),
        ).json()
        self.assertEqual(resp['count'], 1)
        results = resp['results'][0]
        self.assertEqual(results['total_count'], 3)
        self.assertEqual(len(results['results']), 2)
        assignments = {ret['edge']['assigned_by'] for ret in results['results']}
        ids = {ret['ws_obj']['_id'] for ret in results['results']}
        self.assertEqual(assignments, {'assn1', 'assn2'})
        self.assertEqual(ids, {'ws_object_version/1:1:1', 'ws_object_version/1:1:2'})
        self.assertEqual(results['results'][0]['ws_obj']['type'], {
            'type_name': 'Genome',
            'module_name': 'KBaseGenomes',
            'maj_ver': 99,
            'min_ver': 77,
            '_key': 'KBaseGenomes.Genome-99.77'
        })
