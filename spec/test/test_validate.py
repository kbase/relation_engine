"""
Tests for the schema validation functions
"""
import unittest
import os.path as os_path

from spec.test.helpers import capture_stdout
from relation_engine_server.utils.wait_for import wait_for_arangodb
from jsonschema.exceptions import ValidationError
from spec.validate import (
    validate_schema,
    validate_collection,
    validate_stored_query,
    validate_data_source,
    validate_view,
    validate_all
)

_TEST_DIR = '/app/spec/test/sample_schemas'


class TestValidate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        wait_for_arangodb()

    def test_validate_schema(self):
        """Validate a single file using the generic validate_schema method"""

        err_msg = 'No validation schema found for made-up_schema'
        with self.assertRaisesRegex(ValueError, err_msg):
            validate_schema('/path/to/file', 'made-up_schema')

    def test_validate_collection(self):
        """Testing collection-specific schema errors"""

        base_dir = os_path.join(_TEST_DIR, 'collections')

        error_list = [
            {
                'msg': "Name key should match filename: test_nodes vs wrong_name",
                'file': 'wrong_name.yaml',
                'err': ValueError
            },
            {
                'msg': "'http://json-schema.org/draft-07/schema#' is not of type 'object'",
                'file': 'schema_not_object.yaml',
            },
            {
                'msg': "Additional properties are not allowed \('title' was unexpected\)",
                'file': 'extra_top_level_entries.yaml',
            },
            {
                'msg': 'Time-travel edge schemas must require "from" and "to" attributes in ',
                'file': 'edge_delta_missing_to_from.yaml',
            },
            {
                'msg': 'Edge schemas must require "_from" and "_to" attributes in ',
                'file': 'edge_missing_to_from.yaml',
            },
            {
                'msg': 'Vertex schemas must require the "_key" attribute in ',
                'file': 'vertex_missing_key.yaml',
            },
            {
                'msg': 'Time-travel vertex schemas must require the "id" attribute in ',
                'file': 'vertex_missing_id.yaml',
            },
        ]

        for entry in error_list:
            err_type = entry['err'] if 'err' in entry else ValidationError
            # generic method, requires schema type
            with self.assertRaisesRegex(err_type, entry['msg']):
                validate_schema(os_path.join(base_dir, entry['file']), 'collection')
            # specific method
            with self.assertRaisesRegex(err_type, entry['msg']):
                validate_collection(os_path.join(base_dir, entry['file']))

        # TODO: add an example of a schema that validates but where data['schema'] is
        # not a valid json schema.

    def test_validate_data_source(self):

        base_dir = os_path.join(_TEST_DIR, 'data_sources')

        # working example
        output = validate_data_source(os_path.join(base_dir, 'minimal.yaml'))
        self.assertEqual(
            output,
            {
                "name": "minimal",
                "category": "network",
                "title": "Example minimal data source",
            }
        )

        error_list = [
            {
                'msg': "Additional properties are not allowed \('type' was unexpected\)",
                'file': 'invalid_additional_property.json',
            },
        ]

        for entry in error_list:
            err_type = entry['err'] if 'err' in entry else ValidationError

            # generic method
            with self.assertRaisesRegex(err_type, entry['msg']):
                validate_schema(os_path.join(base_dir, entry['file']), 'data_source')

            # same thing as above via specific method
            with self.assertRaisesRegex(err_type, entry['msg']):
                validate_data_source(os_path.join(base_dir, entry['file']))

        # TODO: add in a test for URL validation (once URL validation is working)
        # see uri_validation.json for example

    def test_validate_stored_query(self):

        base_dir = os_path.join(_TEST_DIR, 'stored_queries')

        err_str = "False is not of type 'object'"
        with self.assertRaisesRegex(ValidationError, err_str):
            validate_stored_query(os_path.join(base_dir, 'params_not_object.yaml'))

        # total nonsense instead of AQL
        err_str = 'syntax error, unexpected identifier, expecting assignment'
        with self.assertRaisesRegex(ValueError, err_str):
            validate_stored_query(os_path.join(base_dir, 'invalid_aql.yaml'))

        # invalid bind params
        err_str = 'Bind vars are invalid'
        with self.assertRaisesRegex(ValueError, err_str):
            validate_stored_query(os_path.join(base_dir, 'invalid_bind_params.yaml'))

    def test_validate_view(self):

        base_dir = os_path.join(_TEST_DIR, 'views')
        output = {
            "name": "minimal",
            "type": "arangosearch",
        }

        self.assertEqual(
            validate_schema(os_path.join(base_dir, 'minimal.json'), 'view'),
            output
        )

        self.assertEqual(
            validate_view(os_path.join(base_dir, 'minimal.json')),
            output
        )

        err_str = "'from the shore' is not one of \['arangosearch'\]"
        with self.assertRaisesRegex(ValidationError, err_str):
            validate_view(os_path.join(base_dir, 'wrong_type.json'))

    def test_validate_all(self):
        """test all the files in a directory"""

        sample_schemas = {
            'collection': 'collections',
            'stored_query': 'stored_queries',
            'view': 'views',
            'data_source': 'data_sources',
        }

        for (schema_type, directory) in sample_schemas.items():

            # n.b. this assumes all the schemas in /spec are valid!
            stdout = capture_stdout(validate_all, schema_type)
            self.assertRegex(stdout, r'...all valid')

            with self.assertRaises(Exception):
                validate_all(schema_type, os_path.join(_TEST_DIR, directory))
