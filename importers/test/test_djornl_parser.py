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

_TEST_DIR = "/app/spec/test"


class Test_DJORNL_Parser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # import the results file
        results_file = os.path.join(_TEST_DIR, "djornl", "results.json")
        with open(results_file) as fh:
            cls.json_data = json.load(fh)

        cls.maxDiff = None

    def init_parser_with_path(self, root_path):

        with modified_environ(RES_ROOT_DATA_PATH=root_path):
            parser = DJORNL_Parser()
            # ensure that the configuration has been set
            parser._configure()
            return parser

    def test_errors(self, parser=None, errs={}):
        if parser is None:
            self.assertTrue(True)
            return

        all_errs = []
        for data_type in parser.parse_order:
            if data_type not in errs:
                continue

            all_errs = all_errs + errs[data_type]
            method = f"load_{data_type}"
            output = getattr(parser, method)()
            with self.subTest(data_type=data_type):
                self.assertEqual(output["err_list"], errs[data_type])

        with self.subTest(data_type="all types"):
            # test all errors
            summary = parser.load_data(dry_run=True)
            err_list = summary["errors"]
            self.assertEqual(err_list, all_errs)

    def test_missing_required_env_var(self):
        """test that the parser exits with code 1 if the RES_ROOT_DATA_PATH env var is not set"""
        with self.assertRaisesRegex(
            RuntimeError, "Missing required env var: RES_ROOT_DATA_PATH"
        ):
            parser = DJORNL_Parser()
            parser.load_edges()

    def test_config(self):
        """test that the parser raises an error if a config value cannot be found"""
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)
        with self.assertRaisesRegex(KeyError, "No such config value: bananas"):
            parser.config("bananas")

    def test_load_no_manifest(self):
        """test loading when the manifest does not exist"""
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "no_manifest")
        err_str = "No manifest file found at " + os.path.join(
            RES_ROOT_DATA_PATH, "manifest.yaml"
        )
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_invalid_manifest(self):
        """test an invalid manifest file"""
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "invalid_manifest")
        err_str = "The manifest file failed validation"
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_invalid_file(self):
        """test loading when what is supposed to be a file is actually a directory"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "invalid_file")

        # edges: directory, not a file
        err_str = os.path.join(RES_ROOT_DATA_PATH, "edges.tsv") + ": not a file"
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_missing_files(self):
        """test loading when files cannot be found"""
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "missing_files")
        # not found
        err_str = (
            os.path.join(RES_ROOT_DATA_PATH, "edges.tsv") + ": file does not exist"
        )
        with self.assertRaisesRegex(RuntimeError, err_str):
            self.init_parser_with_path(RES_ROOT_DATA_PATH)

    def test_load_empty_files(self):
        """test loading files containing no data"""

        # path: test/djornl/empty_files
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "empty_files")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        errs = {
            # mix of problems
            "clusters": [
                "cluster_data/headers_only.tsv: no valid data found",
                "cluster_data/no_content.tsv: no header line found",
                "cluster_data/comment_only.tsv: no header line found",
            ],
            # comments only
            "edges": ["merged_edges-AMW-060820_AF.tsv: no header line found"],
            # header only, no content
            "nodes": [
                "aranet2-aragwas-MERGED-AMW-v2_091319_nodeTable.csv: no valid data found"
            ],
        }
        self.test_errors(parser, errs)

    def test_load_missing_headers(self):
        """test loading when files lack required headers"""
        RES_ROOT_DATA_PATH = os.path.join(
            _TEST_DIR, "djornl", "missing_required_headers"
        )
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        def invalid_err(file_name, header_list):
            return f"{file_name}: invalid additional headers: " + ", ".join(
                sorted(header_list)
            )

        def missing_err(file_name, header_list):
            return f"{file_name}: missing required headers: " + ", ".join(
                sorted(header_list)
            )

        def dupe_err(file_name, header_list):
            return f"{file_name}: duplicate headers: " + ", ".join(sorted(header_list))

        errs = {
            "clusters": [
                # tuple containing file name and list of invalid column headers in that file
                missing_err("I2_named.tsv", ["cluster_id", "node_ids"]),
                invalid_err("I2_named.tsv", ["cluster", "node_list"]),
                invalid_err("I4_named.tsv", ["other cool stuff"]),
                dupe_err("I6_named.tsv", ["node_ids"]),
            ],
            "edges": [
                missing_err("edges.tsv", ["score"]),
                missing_err("hithruput-edges.csv", ["edge_type"]),
            ],
            "nodes": [
                missing_err("extra_node.tsv", ["node_type"]),
                invalid_err("extra_node.tsv", ["node_types"]),
                missing_err("pheno_nodes.csv", ["node_id"]),
                invalid_err("pheno_nodes.csv", ["id", "pheno_ref", "usernotes"]),
            ],
        }
        self.test_errors(parser, errs)

    def test_load_invalid_types(self):
        """test file format errors"""

        # path: test/djornl/invalid_types
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "invalid_types")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        errs = {
            "edges": [
                # invalid edge type
                r"edges.tsv line 3: 'Same-Old-Stuff' is not valid under any of the given schemas",
                # empty to/from
                r"edges.tsv line 4: '' does not match '^\\S{2,}.*$'",
                r"edges.tsv line 5: '' does not match '^\\S{2,}.*$'",
                # empty edge type
                r"edges.tsv line 6: '' is not valid under any of the given schemas",
                # invalid score
                r"edges.tsv line 7: '2.' does not match '^\\d+(\\.\\d+)?$'",
                # invalid edge type
                r"edges.tsv line 8: 'raNetv2-DC_' is not valid under any of the given schemas",
                # invalid score
                r"edges.tsv line 10: 'score!' does not match '^\\d+(\\.\\d+)?$'",
                # various permutations of edge directedness
                r"directed_edges.tsv line 4: 'true' is not one of ['1', '0']",
                r"directed_edges.tsv line 5: '' is not one of ['1', '0']",
                r"directed_edges.tsv line 6: 'directed' is not one of ['1', '0']",
                r"directed_edges.tsv line 8: 'false' is not one of ['1', '0']",
            ],
            "nodes": [
                # invalid node type
                r"nodes.csv line 5: 'Monkey' is not valid under any of the given schemas",
                r"nodes.csv line 7: 'A' does not match '^\\S{2,}.*$'",
                r"pheno_nodes.csv: no valid data found",
            ],
            "clusters": [
                r"markov2_named.tsv line 7: 'HoneyNutCluster3' does not match '^Cluster\\d+$'",
                r"markov2_named.tsv line 8: expected 2 cols, found 1",
            ],
        }
        self.test_errors(parser, errs)

    def test_load_col_count_errors(self):
        """test files with invalid numbers of columns"""

        # path: test/djornl/col_count_errors
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "col_count_errors")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        errs = {
            "edges": [
                "edges.tsv line 2: expected 5 cols, found 6",
                "edges.tsv line 6: expected 5 cols, found 3",
                "directed_edges.tsv line 4: expected 6 cols, found 5",
                "directed_edges.tsv line 6: expected 6 cols, found 3",
            ],
            "nodes": ["nodes.csv line 3: expected 20 cols, found 22"],
        }
        self.test_errors(parser, errs)

    def test_load_valid_edge_data(self):
        """ensure that valid edge data can be parsed"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        edge_data = parser.load_edges()
        expected = self.json_data["load_edges"]

        for data_structure in [edge_data, expected]:
            for k in data_structure.keys():
                data_structure[k] = sorted(data_structure[k], key=lambda n: n["_key"])
        expected["err_list"] = []

        self.assertEqual(edge_data, expected)

    def test_load_valid_node_data(self):
        """ensure that valid node data can be parsed"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        node_data = parser.load_nodes()
        expected = self.json_data["load_nodes"]

        for data_structure in [node_data, expected]:
            for k in data_structure.keys():
                data_structure[k] = sorted(data_structure[k], key=lambda n: n["_key"])
                data_structure[k] = [n["_key"] for n in data_structure[k]]
        expected["err_list"] = []

        self.assertEqual(node_data, expected)

    def test_load_valid_cluster_data(self):
        """ensure that valid cluster data can be parsed"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        cluster_data = parser.load_clusters()
        expected = self.json_data["load_clusters"]
        expected["err_list"] = []

        self.assertEqual(cluster_data, expected)

    def test_duplicate_data(self):
        """test files with duplicate data that should throw an error"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "duplicate_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        errs = {
            "edges": [
                "edges.tsv line 17: duplicate data for edge "
                + "AT1G01100__SDV__protein-protein-interaction_literature-curated_AraNet_v2__False",
                "hithruput-edges.csv line 5: duplicate data for edge "
                + "AT1G01010__AT1G01030__protein-protein-interaction_high-throughput_AraNet_v2__False",
                "hithruput-edges.csv line 9: duplicate data for edge "
                + "AT1G01030__AT1G01050__pairwise-gene-coexpression_AraNet_v2__False",
                "hithruput-edges.csv line 11: duplicate data for edge "
                + "SDV__AT1G01100__protein-protein-interaction_literature-curated_AraNet_v2__True",
            ],
            "nodes": ["extra_node.tsv line 5: duplicate data for node AT1G01080"],
        }
        self.test_errors(parser, errs)

    def test_duplicate_cluster_data(self):
        """test files with duplicate cluster data, which should be seamlessly merged"""

        # path: test/djornl/duplicate_data
        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "duplicate_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        cluster_data = parser.load_clusters()
        expected = self.json_data["load_clusters"]
        expected["err_list"] = []

        self.assertEqual(cluster_data, expected)

    def test_dry_run(self):

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        output = parser.load_data(dry_run=True)
        self.assertEqual(
            {
                "edge_type_count": {
                    "phenotype-association_AraGWAS": 3,
                    "pairwise-gene-coexpression_AraNet_v2": 1,
                    "domain-co-occurrence_AraNet_v2": 1,
                    "protein-protein-interaction_high-throughput_AraNet_v2": 2,
                    "protein-protein-interaction_literature-curated_AraNet_v2": 6,
                },
                "edges_total": 13,
                "node_data_available": {"cluster": 0, "full": 14, "key_only": 0},
                "node_type_count": {"__NO_TYPE__": 0, "gene": 10, "pheno": 4},
                "nodes_in_edge": 12,
                "nodes_total": 14,
                "errors_total": 0,
                "errors": [],
            },
            output,
        )

    def test_try_node_merge(self):
        """test node merging"""

        RES_ROOT_DATA_PATH = os.path.join(_TEST_DIR, "djornl", "test_data")
        parser = self.init_parser_with_path(RES_ROOT_DATA_PATH)

        tests = [
            {
                "desc": "existing node is just a _key",
                "old": {"_key": "abcde"},
                "new": {
                    "_key": "abcde",
                    "node_type": "gene",
                    "node_quality": "highest",
                },
                "out": (
                    {"_key": "abcde", "node_type": "gene", "node_quality": "highest"},
                    [],
                ),
            },
            {
                "desc": "new node is just a _key",
                "old": {"_key": "abcde", "node_type": "gene"},
                "new": {"_key": "abcde"},
                "out": ({"_key": "abcde", "node_type": "gene"}, []),
            },
            {
                "desc": "no overlapping keys",
                "old": {"_key": "abcde", "node_type": "gene"},
                "new": {"_key": "abcde", "node_size": 24},
                "out": ({"_key": "abcde", "node_type": "gene", "node_size": 24}, []),
            },
            {
                "desc": "mergeable fields",
                "old": {
                    "_key": "abcde",
                    "go_terms": ["this", "that"],
                    "colour": "pink",
                },
                "new": {"_key": "abcde", "go_terms": ["the other"]},
                "out": (
                    {
                        "_key": "abcde",
                        "go_terms": ["this", "that", "the other"],
                        "colour": "pink",
                    },
                    [],
                ),
            },
            {
                "desc": "mergeable fields, removing list duplicates",
                "old": {
                    "_key": "abcde",
                    "go_terms": ["this", "that", "this", "that", "the"],
                    "colour": "pink",
                },
                "new": {
                    "_key": "abcde",
                    "go_terms": ["this", "the", "that", "that", "other", "other"],
                },
                "out": (
                    {
                        "_key": "abcde",
                        "go_terms": ["this", "that", "the", "other"],
                        "colour": "pink",
                    },
                    [],
                ),
            },
            {
                "desc": "mergeable fields, complex list contents, removing list duplicates",
                "old": {"_key": 123, "list": [{"a": "b"}, {"a": "b"}, {"c": "d"}]},
                "new": {"_key": 123, "list": [{"a": "b"}, {"a": "c"}, {"c": "d"}]},
                "out": (
                    {"_key": 123, "list": [{"a": "b"}, {"c": "d"}, {"a": "c"}]},
                    [],
                ),
            },
            {
                "desc": "mergeable fields, no overlapping keys, nested version",
                "old": {"_key": "abcde", "type": "gene", "info": {"teeth": 16}},
                "new": {"_key": "abcde", "size": 24, "info": {"colour": "pinkish"}},
                "out": (
                    {
                        "_key": "abcde",
                        "type": "gene",
                        "size": 24,
                        "info": {"teeth": 16, "colour": "pinkish"},
                    },
                    [],
                ),
            },
            {
                "desc": "single field error: duplicate",
                "old": {"_key": "abcde", "node_type": "gene"},
                "new": {"_key": "abcde", "node_type": "pheno"},
                "out": (None, ["node_type"]),
            },
            {
                "desc": "single field error: type mismatch",
                "old": {"_key": "abcde", "node_type": "gene"},
                "new": {"_key": "abcde", "node_type": ["pheno"]},
                "out": (None, ["node_type"]),
            },
            {
                "desc": "multiple field errors",
                "old": {"_key": "abcde", "node_type": "gene", "shark": "Jaws"},
                "new": {
                    "_key": "abcde",
                    "node_type": "pheno",
                    "shark": "Loan",
                    "fish": "guppy",
                },
                "out": (None, ["node_type", "shark"]),
            },
            {
                "desc": "multiple field errors, nested dicts",
                "old": {
                    "_key": 123,
                    "a": "A",
                    "b": {"c": {"d": "D"}, "e": {}, "f": "F"},
                },
                "new": {
                    "_key": 123,
                    "a": "A",
                    "b": {"c": {"d": ["D"]}, "e": "E", "f": "f"},
                },
                "out": (None, ["b/c/d", "b/e", "b/f"]),
            },
        ]

        for t in tests:
            with self.subTest(desc=t["desc"]):
                output = parser._try_node_merge(t["old"], t["new"])
                self.assertEqual(output, t["out"])
