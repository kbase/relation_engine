"""
Tests for the ncbi taxonomy stored queries.
"""
import json
import unittest
import requests
# import time

from test.helpers import get_config

_CONF = get_config()


def create_test_docs(ncbi_taxon, ncbi_child_of_taxon):
    """Create edges and vertices we need for tests."""
    body = '\n'.join([json.dumps(d) for d in ncbi_taxon])
    resp = requests.put(
        _CONF['re_api_url'] + '/api/v1/documents',
        params={'overwrite': True, 'collection': 'ncbi_taxon'},
        data=body,
        headers={'Authorization': 'admin_token'}
    )
    if not resp.ok:
        raise RuntimeError(resp.text)
    ncbi_taxon_results = resp.json()
    body = '\n'.join([json.dumps(d) for d in ncbi_child_of_taxon])
    resp = requests.put(
        _CONF['re_api_url'] + '/api/v1/documents',
        params={'overwrite': True, 'collection': 'ncbi_child_of_taxon'},
        data=body,
        headers={'Authorization': 'admin_token'}
    )
    if not resp.ok:
        raise RuntimeError(resp.text)
    ncbi_child_of_taxon_results = resp.json()
    return {
        'ncbi_taxon': ncbi_taxon_results,
        'ncbi_child_of_taxon': ncbi_child_of_taxon_results
    }


class TestNcbiTax(unittest.TestCase):

    def test_valid(self):
        """Test a valid query."""
        taxon_docs = [
            {'_key': '1', 'scientific_name': 'Bacteria', 'rank': 'Domain'},
            {'_key': '2', 'scientific_name': 'Firmicutes', 'rank': 'Phylum'}
        ]
        child_docs = [
                {'_from': 'ncbi_taxon/2', '_to': 'ncbi_taxon/1', 'child_type': 't'}
        ]
        create_test_docs(taxon_docs, child_docs)
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_ancestors'},
            data=json.dumps({'key': '2'}),
            headers={'Authorization': 'valid_token'}  # gives access to workspaces [1,2,3]
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['rank'], 'Domain')
