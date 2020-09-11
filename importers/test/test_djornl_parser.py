"""
Tests for the DJORNL Parser

At the present time, this just ensures that the files are parsed correctly;
it does not check data loading into the db.

These tests run within the re_api docker image.
"""
import json
import unittest
import os

from importers.djornl.parser import DJORNL_Parser
from spec.test.helpers import modified_environ

_TEST_DIR = '/app/spec/test'


class Test_DJORNL_Parser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # import the results file
        results_file = os.path.join(_TEST_DIR, 'djornl', 'results.json')
        with open(results_file) as fh:
            cls.json_data = json.load(fh)

        cls.maxDiff = None

    def init_parser_with_path(self, root_path):

        with modified_environ(RES_ROOT_DATA_PATH=root_path):
            parser = DJORNL_Parser()
            # ensure that the configuration has been set
            parser._configure()
            return parser

    def test_missing_required_env_var(self):
        '''test that the parser exits with code 1 if the RES_ROOT_DATA_PATH env var is not set'''
        with self.assertRaisesRegex(RuntimeError, 'Missing required env var: RES_ROOT_DATA_PATH'):
            parser = DJORNL_Parser()
            parser.load_edges()

    def test_config(self):
        '''test that the parser raises an error if a config value cannot be found'''
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)
        with self.assertRaisesRegex(KeyError, 'No such config value: bananas'):
            parser.config('bananas')

    def test_load_no_manifest(self):
        """ test loading when the manifest does not exist """
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'no_manifest')
        err_str = 'No manifest file found at ' + os.path.join(RES_ROOT_DATA_PATH, 'manifest.yaml')
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_invalid_manifest(self):
        """ test an invalid manifest file """
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_manifest')
        err_str = "The manifest file failed validation"
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_invalid_file(self):
        """ test loading when what is supposed to be a file is actually a directory """

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_file')

        # edges: directory, not a file
        err_str = os.path.join(RES_ROOT_DATA_PATH, "edges.tsv") + ": not a file"
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_empty_files(self):
        """ test loading files containing no data """

        # path: test/djornl/empty_files
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'empty_files')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # header only, no content
        err_str = 'aranet2-aragwas-MERGED-AMW-v2_091319_nodeTable.csv: no valid data found'
        with self.assertRaisesRegex(RuntimeError, err_str):
            parser.load_nodes()

        # comments only
        err_str = 'merged_edges-AMW-060820_AF.tsv: no header line found'
        with self.assertRaisesRegex(RuntimeError, err_str):
            parser.load_edges()

        # mix of problems
        err_str = "\n".join([
            'cluster_data/headers_only.tsv: no valid data found',
            'cluster_data/no_content.tsv: no header line found',
            'cluster_data/comment_only.tsv: no header line found',
        ])
        with self.assertRaisesRegex(RuntimeError, err_str):
            parser.load_clusters()

    def test_load_missing_files(self):
        """ test loading when files cannot be found """

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'missing_files')
        # not found
        err_str = os.path.join(RES_ROOT_DATA_PATH, "edges.tsv") + ': file does not exist'
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_invalid_edges(self):
        """ test file format errors """

        # path: test/djornl/invalid_types
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_types')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # invalid edge type, invalid scores
        edge_err_msg = "\n".join([
            r"edges.tsv line 3: 'Same-Old-Stuff' is not valid under any of the given schemas",
            r"edges.tsv line 7: '2.' does not match .*?",
            r"edges.tsv line 8: 'raNetv2-DC_' is not valid under any of the given schemas",
            r"edges.tsv line 10: 'score!' does not match .*?"
        ])
        with self.assertRaisesRegex(RuntimeError, edge_err_msg):
            parser.load_edges()

    def test_load_invalid_nodes(self):
        """ test file format errors """

        # path: test/djornl/invalid_types
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_types')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # invalid node type
        node_err_msg = "nodes.csv line 5: 'Monkey' is not valid under any of the given schemas"
        with self.assertRaisesRegex(RuntimeError, node_err_msg):
            parser.load_nodes()

    def test_load_invalid_clusters(self):
        """ test file format errors """

        # path: test/djornl/invalid_types
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_types')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # invalid node type
        cluster_err_msg = "markov2_named.tsv line 7: 'HoneyNutCluster3' does not match"
        with self.assertRaisesRegex(RuntimeError, cluster_err_msg):
            parser.load_clusters()

    def test_load_col_count_errors(self):
        """ test files with invalid numbers of columns """

        # path: test/djornl/col_count_errors
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'col_count_errors')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # not enough cols
        edge_err_msg = 'merged_edges-AMW-060820_AF.tsv line 6: expected 5 cols, found 3'
        with self.assertRaisesRegex(RuntimeError, edge_err_msg):
            parser.load_edges()

        # too many cols
        node_err_msg = 'aranet2-aragwas-MERGED-AMW-v2_091319_nodeTable.csv line 3: expected 20 cols, found 22'
        with self.assertRaisesRegex(RuntimeError, node_err_msg):
            parser.load_nodes()

    def test_load_valid_edge_data(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        edge_data = parser.load_edges()
        expected = self.json_data["load_edges"]

        for data_structure in [edge_data, expected]:
            for k in data_structure.keys():
                data_structure[k] = sorted(data_structure[k], key=lambda n: n['_key'])

        self.assertEqual(edge_data, expected)

    def test_load_valid_node_metadata(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        node_metadata = parser.load_nodes()
        expected = self.json_data["load_nodes"]

        for data_structure in [node_metadata, expected]:
            for k in data_structure.keys():
                data_structure[k] = sorted(data_structure[k], key=lambda n: n['_key'])
                data_structure[k] = [n['_key'] for n in data_structure[k]]

        self.assertEqual(node_metadata, expected)

    def test_load_valid_cluster_data(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        cluster_data = parser.load_clusters()
        self.assertEqual(
            cluster_data,
            self.json_data["load_clusters"]
        )

    def test_duplicate_edge_data(self):
        """ test files with duplicate edge data, which should throw an error """

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'duplicate_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        err_msg = "\n".join([
            "hithruput-edges.csv line 5: duplicate data for edge AT1G01010__AT1G01030__AraNetv2-HT_.*?",
            "hithruput-edges.csv line 9: duplicate data for edge AT1G01030__AT1G01050__AraNetv2-CX_.*?"
        ])
        with self.assertRaisesRegex(RuntimeError, err_msg):
            parser.load_edges()

    def test_duplicate_node_data(self):
        """ test files with duplicate node data, which should throw an error """

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'duplicate_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        err_msg = "extra_node.tsv line 5: duplicate data for node AT1G01080"
        with self.assertRaisesRegex(RuntimeError, err_msg):
            parser.load_nodes()

    def test_duplicate_cluster_data(self):
        """ test files with duplicate cluster data, which should be seamlessly merged """

        # path: test/djornl/col_count_errors
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'duplicate_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        cluster_data = parser.load_clusters()
        self.assertEqual(
            cluster_data,
            self.json_data["load_clusters"]
        )
