"""
Test JSON validation functions
"""
from relation_engine_server.utils.json_validation import run_validator
import unittest


class TestUtils(unittest.TestCase):

    def test_json_validation_defaults(self):
        """Test that the jsonschema validator sets default values."""
        schema = {'properties': {'foo': {'default': 'bar'}}}
        obj = run_validator(data={}, schema=schema)
        self.assertEqual(obj, {'foo': 'bar'})
