"""
Tests for the Dan Jacobson ORNL Arabidopsis stored queries.
"""
import json
import unittest
import os

from spec.test.helpers import get_config, modified_environ, create_test_docs, run_query, check_spec_test_env
from importers.djornl.parser import DJORNL_Parser

_CONF = get_config()
_TEST_DIR = '/app/spec/test'
_VERBOSE = 0


def print_db_update(response, collection):
    if not _VERBOSE:
        return
    print(f"Saved docs to collection {collection}!")
    print(response.text)
    print('=' * 80)


class Test_DJORNL_Stored_Queries(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        check_spec_test_env()
        # import the results file
        results_file = os.path.join(_TEST_DIR, 'djornl', 'results.json')
        with open(results_file) as fh:
            cls.json_data = json.load(fh)

        cls.no_results = {'nodes': [], 'edges': []}
        cls.maxDiff = None

        # load the DB
        root_path = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        with modified_environ(RES_ROOT_DATA_PATH=root_path):
            parser = DJORNL_Parser()
            node_name = parser.config('node_name')
            edge_name = parser.config('edge_name')

            edge_data = parser.load_edges()
            r = create_test_docs(node_name, edge_data['nodes'])
            print_db_update(r, node_name)
            r = create_test_docs(edge_name, edge_data['edges'])
            print_db_update(r, edge_name)

            node_metadata = parser.load_nodes()
            r = create_test_docs(node_name, node_metadata['nodes'], True)
            print_db_update(r, node_name)

            cluster_data = parser.load_clusters()
            r = create_test_docs(node_name, cluster_data['nodes'], True)
            print_db_update(r, node_name)

    def test_expected_results(self, query_name=None, test_data=None):

        # don't run the tests if they're being called automatically
        if query_name is None:
            self.assertTrue(True)
            return

        # ensure we have either 'results' or 'error' in the test data
        self.assertTrue('results' in test_data or 'error' in test_data)

        params = {}
        if 'params' in test_data:
            params = test_data['params']

        response = run_query(query_name, params)

        if _VERBOSE:
            print("Running query " + query_name)
            if 'params' in test_data:
                print({'params': params})

        # expecting an error response
        if 'error' in test_data:
            if 'error' not in response:
                print({'response': response})

            self.assertIn('error', response)
            self.assertEqual(response['error'], test_data['error'])
            return response

        # expecting a valid response
        if 'results' not in response:
            print({'response': response})

        self.assertIn('results', response)
        results = response['results'][0]

        self.assertEqual(
            set([n["_key"] for n in results['nodes']]),
            set(test_data['results']['nodes'])
        )

        self.assertEqual(
            set([e["_key"] for e in results['edges']]),
            set(test_data['results']['edges'])
        )
        return response

    # indexing schema in results.json
    # self.json_data['queries'][query_name]
    # e.g. for fetch_clusters data:
    # "djornl_fetch_clusters": {
    #   "params": { "cluster_ids": ["markov_i2:6", "markov_i4:3"], "distance": "1"},
    #   "results": {
    #     "nodes": [ node IDs ],
    #     "edges": [ edge data ]
    #   }
    # }
    # nodes are represented as a list of node[_key]
    # edges are objects with keys _to, _from, edge_type and score

    def test_fetch_all(self):
        '''Ensure that data returned by the fetch all query has all the information that we expect'''
        response = self.test_expected_results(
            "djornl_fetch_all",
            self.json_data['queries']['djornl_fetch_all'][0]
        )

        # ensure that all the cluster data is returned OK
        node_data = response['results'][0]['nodes']
        expected_node_data = self.json_data['load_clusters']['nodes']
        self.assertEqual(
            {n['_key']: n['clusters'] for n in node_data if 'clusters' in n},
            {n['_key']: n['clusters'] for n in expected_node_data if 'clusters' in n},
        )

    def test_queries(self):
        '''Run parameterised queries and check for results or error messages'''

        for query in self.json_data['queries'].keys():
            for test in self.json_data['queries'][query]:
                with self.subTest(query=query, params=test['params']):
                    self.test_expected_results(query, test)
