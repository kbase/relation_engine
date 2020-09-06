"""
Tests for the Dan Jacobson ORNL Arabidopsis collection schemas.

These tests ensure that specific elements of the collection schemas validate correctly.

"""
import unittest

from spec.test.helpers import check_spec_test_env
from relation_engine_server.utils.spec_loader import get_schema
from relation_engine_server.utils.json_validation import get_schema_validator
from jsonschema.exceptions import ValidationError


class Test_DJORNL_Collections(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        check_spec_test_env()

    def test_node(self, query_name=None, test_data=None):
        """ ensure node data validates correctly """

        schema_file = get_schema('collection', 'djornl_node', path_only=True)
        validator = get_schema_validator(schema_file=schema_file, validate_at='/schema')

        test_data = [
            {
                'data': {'_key': 'AT1G01010', 'go_terms': ['GO:0003700', 'GO:0003677']},
                'valid': True,
            },
            {
                'data': {'_key': 'ABCDE', 'node_type': 'vertex'},
                'valid': False,
                'error': "'vertex' is not valid under any of the given schemas",
            },
            {
                'data': {'_key': 'ABCDE', 'clusters': ['GO:0003700', 'GO:0003700']},
                'valid': False,
                'error': "\['GO:0003700', 'GO:0003700'\] has non-unique elements"
            }
        ]

        for test in test_data:
            if test['valid']:
                self.assertTrue(
                    validator.is_valid(test['data'])
                )
            else:
                with self.assertRaisesRegex(ValidationError, test['error']):
                    validator.validate(test['data'])
