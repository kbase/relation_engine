"""
Tests for the prepare_ontology

These tests run within the re_api docker image.
"""
import unittest
import os
from scripts.prepare_ontology import (
    prepare_collections_file,
    prepare_data_sources_file,
    parse_input,
    parse_namespace,
    clean_up_data,
)

_TEST_DIR = "/app/scripts/test"
_TEST_NAMESPACE = "fake_ontology"


class Test_prepare_ontology(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.data_sources_file = os.path.join(_TEST_DIR, "data", "data_sources.json")

    def test_parse_input(self):
        d = parse_input(self.data_sources_file, _TEST_NAMESPACE)
        self.assertEqual(d["ns"], _TEST_NAMESPACE)

    def test_parse_namespace(self):
        n, t = parse_namespace(_TEST_NAMESPACE)
        self.assertEqual(n, "fake")
        self.assertEqual(t, "ontology")

    def test_data_sources_file(self):
        d = parse_input(self.data_sources_file, _TEST_NAMESPACE)
        ret = prepare_data_sources_file(d, _TEST_DIR)
        self.assertTrue(os.path.exists(ret))
        clean_up_data(ret)
        self.assertFalse(os.path.exists(ret))

    def test_collections_file(self):
        d = parse_input(self.data_sources_file, _TEST_NAMESPACE)
        ret = prepare_collections_file(d, _TEST_DIR)
        self.assertTrue(os.path.exists(ret))
        clean_up_data(ret)
        self.assertFalse(os.path.exists(ret))
