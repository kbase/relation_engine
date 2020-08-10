"""
Test JSON validation functions
"""
import unittest
import os.path as os_path
from yaml import safe_load
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
                    'pattern': '^\w+$',
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
                    'title': 'date of creation',
                    'description': 'Approx six thousand years ago',
                    'type': 'string',
                    'format': 'date',
                },
                'date': {
                    'title': 'date',
                    'description': 'A type of dried fruit',
                    'type': 'string',
                    'format': 'date',
                }
            }
        }
    }
}

test_schema_two = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Exascale parser file manifest",
  "type": "object",
  "required": ["name", "file_list"],
  "properties": {
    "name": {
      "title": "Dataset name",
      "type": "string",
      "description": "The name of the dataset",
      "examples": ["Dan Jacobson Exascale dataset"]
    },
    "release_date": {
      "title": "Release date",
      "type": "string",
      "description": "Date of the dataset release, in YYYY-MM-DD format",
      "format": "date"
    },
    "notes": {
      "type": "string",
      "title": "Release notes",
      "description": "Free text describing the release and any notes, or comments relevant to consumers of the data."
    },
    "file_list": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["data_type", "path"],
        "oneOf": [
          {
            "properties": {
              "data_type": {"enum": ["cluster"]}
            },
            "required": ["cluster_prefix"]
          },
          {
            "properties": {
              "data_type": {"enum": ["node", "edge"]}
            }
          }
        ],
        "properties": {
          "data_type": {
            "title": "Data type",
            "type": "string",
            "enum": ["node", "edge", "cluster"]
          },
          "date": {
            "title": "File creation date",
            "description": "date of file creation in the format YYYY-MM-DD",
            "type": "string",
            "format": "date"
          },
          "description": {
            "title": "Description of the cluster set",
            "type": "string"
          },
          "path": {
            "title": "File path",
            "type": "string"
          },
          "cluster_prefix": {
            "title": "Prefix",
            "type": "string",
            "description": "The prefix to be used for clusters"
          },
          "title": {
            "title": "Name of the cluster set",
            "type": "string"
          }
        }
      }
    }
  }
}


valid_json_loc = '/properties/params'


class TestJsonValidation(unittest.TestCase):

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

    def test_uri_validation(self):
        '''Test URI validation is operational'''

        err_str = "'where is it\?' is not a 'uri'"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=test_schema,
                data={'name': 'blank', 'distance': 3, 'home_page': 'where is it?'},
                validate_at=valid_json_loc)

        # this string is OK
        input = {'name': 'blank', 'distance': 3, 'home_page': 'http://www.home/com'}
        output = run_validator(
                schema=test_schema,
                data=input,
                validate_at=valid_json_loc)
        self.assertEqual(output, input)

    def test_date_format_validation(self):
        '''ensure that fancy date formats are correctly validated'''

        err_str = "'12345678' is not a 'date'"
        with self.assertRaisesRegex(ValidationError, err_str):
            input = {'name': 'whatever', 'distance': 1, 'creation_date': '12345678'}
            run_validator(
                schema=test_schema,
                data=input,
                validate_at=valid_json_loc)

        # date field NAMED date!
        err_str = "'12345678' is not a 'date'"
        with self.assertRaisesRegex(ValidationError, err_str):
            input = {'name': 'whatever', 'distance': 1, 'date': '12345678'}
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

        # use the manifest schema
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=test_schema_two,
                data={'name': 'a', 'file_list': [], 'release_date': '12345678'}
            )

        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema_file='/app/importers/djornl/manifest.schema.json',
                data={'name': 'a', 'file_list': [], 'release_date': '12345678'}
            )

        # valid inputs
        more_input = {'name': 'a', 'file_list': [], 'release_date': '1999-12-31'}
        more_output = run_validator(
            schema=test_schema_two,
            data=more_input
        )
        self.assertEqual(more_input, more_output)

        more_output = run_validator(
            schema_file='/app/importers/djornl/manifest.schema.json',
            data=more_input
        )
        self.assertEqual(more_input, more_output)

    def test_valid_manifest_validation(self):
        """ensure that a valid manifest passes validation"""

        manifest_schema = '/app/importers/djornl/manifest.schema.json'
        test_dir = '/app/spec/test/djornl/'
        with open(os_path.join(test_dir, 'test_data', 'manifest.yaml')) as fd:
            file_contents = safe_load(fd)

        # raw data
        manifest_data = run_validator(
            schema_file=manifest_schema,
            data=file_contents,
            nicer_errors=True
        )
        self.assertTrue(manifest_data)

        # data file
        manifest_data = run_validator(
            schema_file=manifest_schema,
            data_file=os_path.join(test_dir, 'test_data', 'manifest.yaml'),
            nicer_errors=True
        )
        self.assertTrue(manifest_data)

        # data file
        manifest_data = run_validator(
            schema_file=manifest_schema,
            data_file=os_path.join(test_dir, 'valid', 'with_descriptions.yaml'),
            nicer_errors=True
        )
        self.assertTrue(manifest_data)

    def test_schema_references(self):
        """ensure referenced schemas can be accessed"""

        valid_edge_data = {
            "_from": "here",
            "_to": "eternity",
            "score": 1.23456,
            "_key": "abcdefg",
            "edge_type": "domain_co_occur",
        }

        invalid_edge_data = {
            "_from": "here",
            "_to": "eternity",
            "score": 1.23456,
            "_key": "abcdefg",
            "edge_type": "whatever",
        }

        schema_ref_dir = ['/app', 'spec', 'test', 'sample_schemas', 'schema_refs']

        # same schema in different places
        path_list = [
            [],
            ['level_1'],
            ['level_1', 'level_2']
        ]

        err_msg = "'whatever' is not valid under any of the given schemas"
        for path in path_list:

            for file_ext in ['json', 'yaml']:
                file_path = os_path.join(*(schema_ref_dir + path), 'edge.' + file_ext)
                with self.assertRaisesRegex(ValidationError, err_msg):
                    run_validator(
                        schema_file=file_path,
                        data=invalid_edge_data,
                    )

                self.assertEqual(
                    run_validator(
                        schema_file=file_path,
                        data=valid_edge_data,
                    ),
                    valid_edge_data
                )
