"""
Test utility functions
"""
from relation_engine_server.utils import json_validation

import unittest


class TestUtils(unittest.TestCase):

    def test_json_validation_defaults(self):
        """Test that the jsonschema validator sets default values."""
        schema = {'properties': {'foo': {'default': 'bar'}}}
        obj = {}  # type: dict
        json_validation.Validator(schema).validate(obj)
        self.assertEqual(obj, {'foo': 'bar'})
