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
        create_test_docs(taxon_docs, child_docs)

    def test_ancestors_valid(self):
        """Test a valid query of taxon ancestors."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_ancestors'},
            data=json.dumps({'key': '2'}),
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['rank'], 'Domain')

    def test_descendants_valid(self):
        """Test a valid query of taxon descendants."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_descendants'},
            data=json.dumps({'key': '1'}),
        ).json()
        self.assertEqual(resp['count'], 2)
        ranks = {r['rank'] for r in resp['results']}
        names = {r['scientific_name'] for r in resp['results']}
        self.assertEqual(ranks, {'Phylum'})
        self.assertEqual(names, {'Firmicutes', 'Proteobacteria'})

    def test_descendants_2levels_valid(self):
        """Test a valid query for descendants with 2 levels."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_descendants'},
            data=json.dumps({'key': '1', 'levels': 2}),
        ).json()
        self.assertEqual(resp['count'], 6)
        ranks = {r['rank'] for r in resp['results']}
        names = {r['scientific_name'] for r in resp['results']}
        self.assertEqual(ranks, {'Phylum', 'Class'})
        self.assertEqual(names, {
            'Firmicutes',
            'Proteobacteria',
            'Bacilli',
            'Alphaproteobacteria',
            'Gammaproteobacteria',
            'Deltaproteobacteria',
        })

    def test_siblings_valid(self):
        """Test a valid query for siblings."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({'key': '5'}),  # Querying from "Alphaproteobacteria"
        ).json()
        self.assertEqual(resp['count'], 2)
        ranks = {r['rank'] for r in resp['results']}
        names = {r['scientific_name'] for r in resp['results']}
        self.assertEqual(ranks, {'Class'})
        self.assertEqual(names, {'Gammaproteobacteria', 'Deltaproteobacteria'})

    def test_siblings_root(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({'key': '1'}),  # Querying from "Bacteria"
        ).json()
        self.assertEqual(resp['count'], 0)

    def test_siblings_nonexistent_node(self):
        """Test a query for siblings on the root node with no parent."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_get_siblings'},
            data=json.dumps({'key': 'xyz'}),  # Nonexistent node
        ).json()
        self.assertEqual(resp['count'], 0)

    def test_search_sciname_prefix(self):
        """Test a query to search sciname."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': 'prefix:bact'}),
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['scientific_name'], 'Bacteria')

    def test_search_sciname_nonexistent(self):
        """Test a query to search sciname for empty results."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': 'xyzabc'}),
        ).json()
        self.assertEqual(resp['count'], 0)

    def test_search_sciname_wrong_type(self):
        """Test a query to search sciname with the wrong type for the search_text param."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': 123})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "123 is not of type 'string'")

    def test_search_sciname_missing_search(self):
        """Test a query to search sciname with the search_text param missing."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "'search_text' is a required property")

    def test_search_sciname_more_complicated(self):
        """Test a query to search sciname with some more keyword options."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': "prefix:gamma,|prefix:alpha,|prefix:delta"})
        ).json()
        self.assertEqual(resp['count'], 3)
        names = {r['scientific_name'] for r in resp['results']}
        self.assertEqual(names, {'Gammaproteobacteria', 'Alphaproteobacteria', 'Deltaproteobacteria'})

    def test_search_sciname_offset_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': "prefix:bact", "offset": 10001})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "10001 is greater than the maximum of 10000")

    def test_search_sciname_limit_max(self):
        """Test a query to search sciname with an invalid offset (greater than max)."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_taxon_search_sci_name'},
            data=json.dumps({'search_text': "prefix:bact", "limit": 101})
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], "101 is greater than the maximum of 100")

    def test_fetch_taxon(self):
        """Test a valid query to fetch a taxon."""
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ncbi_fetch_taxon'},
            data=json.dumps({'key': '1'})
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['results'][0]['_id'], 'ncbi_taxon/1')
