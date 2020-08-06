"""
Test JSON validation functions
"""
import unittest
from relation_engine_server.utils.json_validation import run_validator
from jsonschema.exceptions import ValidationError
from jsonpointer import JsonPointerException


test_schema = {
    'properties': {
        'params': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'format': 'regex',
                    'pattern': '^\\w+$',
                    'default': 'blank',
                },
                'distance': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 10,
                    'default': 1,
                },
                'home_page': {
                    'type': 'string',
                    'format': 'uri',
                },
                'creation_date': {
                    'type': 'string',
                    'format': 'date',
                }
            }
        }
    }
}

valid_json_loc = '/properties/params'


class TestUtils(unittest.TestCase):

    def test_non_validation_validator_errors(self):
        '''test errors in the validator that are unrelated to the valiation functionality'''

        err_str = "Please supply either a schema or a schema file path"
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator()

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(data={})

        # only supply one of schema or schema_file
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, schema_file='/path/to/file')

        err_str = "Please supply either a data structure or a data file path"
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={})

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, data={}, data_file='')

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, data=None, data_file=None)

        # invalid jsonpointer string - note the grammar error is from jsonpointer
        err_str = 'location must starts with /'
        json_loc = 'start validating here'
        with self.assertRaisesRegex(JsonPointerException, err_str):
            run_validator(schema=test_schema, data={}, validate_at=json_loc)

        # invalid jsonpointer ref
        err_str = "member 'property' not found in"
        json_loc = '/properties/params/property'
        with self.assertRaisesRegex(JsonPointerException, err_str):
            run_validator(schema=test_schema, data={}, validate_at=json_loc)

        # finally!!
        output = run_validator(
                schema=test_schema,
                data={'name': 'name', 'distance': 3},
                validate_at='/properties/params')
        self.assertEqual(output, {'name': 'name', 'distance': 3})

    def test_json_validation_defaults(self):
        """Test that the jsonschema validator sets default values."""

        test_data = run_validator(schema=test_schema, data={}, validate_at=valid_json_loc)
        self.assertEqual(test_data, {'name': 'blank', 'distance': 1})

    def test_pattern_validation(self):
        '''Test pattern validation'''

        # validation error - string does not match regex
        err_str = "'Mr Blobby' does not match .*?"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=test_schema,
                data={'name': 'Mr Blobby', 'distance': 3},
                validate_at=valid_json_loc)

        # this string is OK
        output = run_validator(
                schema=test_schema,
                data={'name': 'Mr_Blobby_666', 'distance': 3},
                validate_at=valid_json_loc)
        self.assertEqual(output, {'name': 'Mr_Blobby_666', 'distance': 3})

    def test_date_format_validation(self):
        '''ensure that fancy date formats are correctly validated'''

        err_str = "'12345678' is not a 'date'"
        with self.assertRaisesRegex(ValidationError, err_str):
            input = {'name': 'whatever', 'distance': 1, 'creation_date': '12345678'}
            run_validator(
                schema=test_schema,
                data=input,
                validate_at=valid_json_loc)

        input = {'name': 'whatever', 'distance': 1, 'creation_date': '2020-05-23'}
        output = run_validator(
            schema=test_schema,
            data=input,
            validate_at=valid_json_loc)
        self.assertEqual(input, output)
