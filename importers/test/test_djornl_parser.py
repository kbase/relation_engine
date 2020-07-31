"""
Tests for the DJORNL Parser

At the present time, this just ensures that the files are parsed correctly;
it does not check data loading into the db.
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

    def init_parser_with_path(self, root_path):

        with modified_environ(RES_ROOT_DATA_PATH=root_path):
            parser = DJORNL_Parser()
            # ensure that the configuration has been set
            parser.config()
            return parser

    def test_load_empty_files(self):
        """ test loading files containing no data """

        # path: test/djornl/empty_files
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'empty_files')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        self.assertEqual(parser.load_edges(), {"nodes": [], "edges": []})
        self.assertEqual(parser.load_node_metadata(), {"nodes": []})
        self.assertEqual(parser.load_cluster_data(), {"nodes": []})

    def test_load_missing_files(self):
        """ test loading when files cannot be found """

        # this dir does not contain the correct file structure
        # path: test/djornl/empty_files/cluster_data
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'empty_files', 'cluster_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        err_str = "No such file or directory: '" + RES_ROOT_DATA_PATH
        with self.assertRaisesRegex(FileNotFoundError, err_str):
            parser.load_edges()

        with self.assertRaisesRegex(FileNotFoundError, err_str):
            parser.load_node_metadata()

        with self.assertRaisesRegex(FileNotFoundError, err_str):
            parser.load_cluster_data()

    def test_load_invalid_types(self):
        """ test file format errors """

        # path: test/djornl/invalid_types
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'invalid_types')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # invalid edge type
        edge_err_msg = 'line 2: invalid edge type: AraGWAS-Some-Old-Rubbish-I-Made-Up'
        with self.assertRaisesRegex(RuntimeError, edge_err_msg):
            parser.load_edges()

        # invalid node type
        node_err_msg = 'line 4: invalid node type: Monkey'
        with self.assertRaisesRegex(RuntimeError, node_err_msg):
            parser.load_node_metadata()

    def test_load_col_count_errors(self):
        """ test files with invalid numbers of columns """

        # path: test/djornl/col_count_errors
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'col_count_errors')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        # invalid edge type
        edge_err_msg = 'line 6: expected 5 cols, found 3'
        with self.assertRaisesRegex(RuntimeError, edge_err_msg):
            parser.load_edges()

        # invalid node type
        node_err_msg = 'line 3: expected 20 cols, found 22'
        with self.assertRaisesRegex(RuntimeError, node_err_msg):
            parser.load_node_metadata()

    def test_load_valid_edge_data(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        self.maxDiff = None

        edge_data = parser.load_edges()
        self.assertEqual(
            edge_data,
            self.json_data["load_edges"]
        )

    def test_load_valid_node_metadata(self):

        self.maxDiff = None
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        node_metadata = parser.load_node_metadata()
        self.assertEqual(
            node_metadata,
            self.json_data["load_node_metadata"]
        )

    def test_load_valid_cluster_data(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, 'djornl', 'test_data')
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        cluster_data = parser.load_cluster_data()
        self.assertEqual(
            cluster_data,
            self.json_data["load_cluster_data"]
        )
