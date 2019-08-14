"""
Tests queries related to wsfull objects
"""
import json
import unittest
import requests

from test.stored_queries.helpers import create_test_docs
from test.helpers import get_config

_CONF = get_config()


class TestWsfull(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Create test documents"""
        wsfull_object_versions = [
            {
                '_key': '1:1:2',
                'workspace_id': 1,
                'object_id': 1,
                'version': 2,
                'name': 'obj_name',
                'hash': 'xyz',
                'size': 100,
                'epoch': 0,
                'deleted': False
            }
        ]
        taxa = [
            {'_key': '1', 'scientific_name': 'sciname1', 'rank': 'rank1'},
            {'_key': '2', 'scientific_name': 'sciname2', 'rank': 'rank2'},
        ]
        edges = [
            {'_from': 'wsfull_object_version/1:1:2', '_to': 'ncbi_taxon/1', 'assigned_by': 'assn1'},
            {'_from': 'wsfull_object_version/1:1:2', '_to': 'ncbi_taxon/2', 'assigned_by': 'assn2'},
        ]
        create_test_docs('wsfull_object_version', wsfull_object_versions)
        create_test_docs('ncbi_taxon', taxa)
        create_test_docs('wsfull_obj_version_has_taxon', edges)

    def test_valid_query(self):
        """Test a valid query to get associated taxa."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'wsfull_get_associated_taxa'},
            data=json.dumps({'id': 'wsfull_object_version/1:1:2'}),
        ).json()
        self.assertEqual(resp['count'], 2)
        assignments = [ret['edge']['assigned_by'] for ret in resp['results']]
        scinames = [ret['taxon']['scientific_name'] for ret in resp['results']]
        self.assertEqual(assignments, ['assn1', 'assn2'])
        self.assertEqual(scinames, ['sciname1', 'sciname2'])
