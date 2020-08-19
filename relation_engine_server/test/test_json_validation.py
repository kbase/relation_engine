"""
Test JSON validation functions
"""
import unittest
import os.path as os_path
import json
import yaml
from relation_engine_server.utils.json_validation import run_validator
from jsonschema.exceptions import ValidationError, RefResolutionError
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

valid_json_loc = '/properties/params'
test_data_dirs = ['/app', 'relation_engine_server', 'test', 'data']
json_validation_dir = os_path.join(*(test_data_dirs + ['json_validation']))
schema_refs_dir = os_path.join(*(test_data_dirs + ['schema_refs']))

test_schema_list = [
    ['schema', test_schema],
    ['schema_file', os_path.join(json_validation_dir, 'test_schema.json')],
    ['schema_file', os_path.join(json_validation_dir, 'test_schema.yaml')],
]

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

    def test_json_validation(self):

        test_list = [
            self.add_defaults,
            self.pattern_validation,
            self.uri_validation,
            self.date_format_validation,
        ]

        for test_schema in test_schema_list:
            schema_file_arg = schema_arg = test_schema[1]

            if test_schema[0] == 'schema':
                schema_file_arg = None
            else:
                schema_arg = None

            for test in test_list:
                test(schema_arg, schema_file_arg)

    def add_defaults(self, schema_arg, schema_file_arg):
        """Test that the jsonschema validator sets default values."""

        test_data = run_validator(
            schema=schema_arg,
            schema_file=schema_file_arg,
            data={},
            validate_at=valid_json_loc)
        self.assertEqual(test_data, {'name': 'blank', 'distance': 1})

        for file_ext in ['json', 'yaml']:
            file_path = os_path.join(json_validation_dir, 'defaults.' + file_ext)
            self.assertEqual(
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc
                ),
                {'name': 'blank', 'distance': 1}
            )

    def pattern_validation(self, schema_arg, schema_file_arg):
        '''Test pattern validation'''

        # validation error - string does not match regex
        err_str = "'Mr Blobby' does not match .*?"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=schema_arg,
                schema_file=schema_file_arg,
                data={'name': 'Mr Blobby', 'distance': 3},
                validate_at=valid_json_loc)

        # this string is OK
        output = run_validator(
              schema=schema_arg,
              schema_file=schema_file_arg,
              data={'name': 'Mr_Blobby_666', 'distance': 3},
              validate_at=valid_json_loc)
        self.assertEqual(output, {'name': 'Mr_Blobby_666', 'distance': 3})

        for file_ext in ['json', 'yaml']:
            # validation error - string does not match regex
            err_str = '"what\'s-the-problem with-this-string\?" does not match .*?'
            file_path = os_path.join(json_validation_dir, 'invalid_pattern.' + file_ext)
            with self.assertRaisesRegex(ValidationError, err_str):
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc)

            file_path = os_path.join(json_validation_dir, 'valid_pattern.' + file_ext)
            self.assertEqual(
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc),
                {'name': 'No_problem_with_this_string', 'distance': 3}
            )

    def uri_validation(self, schema_arg, schema_file_arg):
        '''Test URI validation is operational'''

        err_str = "'where is it\?' is not a 'uri'"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=schema_arg,
                schema_file=schema_file_arg,
                data={'name': 'blank', 'distance': 3, 'home_page': 'where is it?'},
                validate_at=valid_json_loc)

        # this string is OK
        input = {'name': 'valid_uri', 'distance': 3, 'home_page': 'http://www.home.com'}
        output = run_validator(
            schema=schema_arg,
            schema_file=schema_file_arg,
            data=input,
            validate_at=valid_json_loc)
        self.assertEqual(output, input)

        # data files
        for file_ext in ['json', 'yaml']:
            file_path = os_path.join(json_validation_dir, 'invalid_uri.' + file_ext)
            err_str = "'where is it\?' is not a 'uri'"
            with self.assertRaisesRegex(ValidationError, err_str):
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc)

            file_path = os_path.join(json_validation_dir, 'valid_uri.' + file_ext)
            self.assertEqual(
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc),
                {
                    "name": "valid_uri",
                    "distance": 3,
                    "home_page": "http://json-validation.com:5000/this/is/valid"
                }
            )

    def date_format_validation(self, schema_arg, schema_file_arg):
        '''ensure that fancy date formats are correctly validated'''

        err_str = "'202001017' is not a 'date'"
        with self.assertRaisesRegex(ValidationError, err_str):
            input = {'name': 'whatever', 'distance': 1, 'date': '202001017'}
            run_validator(
                schema=schema_arg,
                schema_file=schema_file_arg,
                data=input,
                validate_at=valid_json_loc)

        input = {'name': 'whatever', 'distance': 1, 'date': '2020-05-23'}
        output = run_validator(
            schema=schema_arg,
            schema_file=schema_file_arg,
            data=input,
            validate_at=valid_json_loc)
        self.assertEqual(input, output)

        # data files
        for file_ext in ['json', 'yaml']:
            # invalid type (number instead of string)
            file_path = os_path.join(json_validation_dir, 'invalid_date_type.' + file_ext)
            err_str = "20200606 is not of type 'string'"
            with self.assertRaisesRegex(ValidationError, err_str):
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc)

            # quoted string but not in the correct format
            file_path = os_path.join(json_validation_dir, 'invalid_date.' + file_ext)
            err_str = "'20200606' is not a 'date'"
            with self.assertRaisesRegex(ValidationError, err_str):
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc)

            file_path = os_path.join(json_validation_dir, 'valid_date.' + file_ext)
            self.assertEqual(
                run_validator(
                    schema=schema_arg,
                    schema_file=schema_file_arg,
                    data_file=file_path,
                    validate_at=valid_json_loc),
                {
                    "name": "valid_date",
                    "date": "2020-06-06",
                    "distance": 3,
                }
            )

        # pyyaml-specific issue: dates get automatically parsed into datetime objects (doh!)
        file_path = os_path.join(json_validation_dir, 'unquoted_date.yaml')
        err_str = "datetime.date\(2020, 6, 6\) is not of type 'string'"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=schema_arg,
                schema_file=schema_file_arg,
                data_file=file_path,
                validate_at=valid_json_loc)

    def test_schema_references(self):
        """Ensure referenced schemas, including those written in yaml, can be accessed."""

        # same schema in different places
        path_list = [
            [],
            ['level_1'],
            ['level_1', 'level_2']
        ]

        err_msg = "'whatever' is not valid under any of the given schemas"
        for path in path_list:

            for file_ext in ['json', 'yaml']:
                file_path = os_path.join(*(test_data_dirs + ['schema_refs'] + path), 'edge.' + file_ext)

                # fails due to invalid data
                with self.assertRaisesRegex(ValidationError, err_msg):
                    run_validator(
                        schema_file=file_path,
                        data=invalid_edge_data,
                    )

                # valid data
                self.assertEqual(
                    run_validator(
                        schema_file=file_path,
                        data=valid_edge_data,
                    ),
                    valid_edge_data
                )

                # validate using the schema instead of the schema_file
                with open(file_path) as fd:
                    contents = yaml.safe_load(fd) if file_ext == 'yaml' else json.load(fd)

                # if there is no $id in the schema, the ref resolver won't know
                # where the schema file is located and will not resolve relative references
                with self.assertRaisesRegex(RefResolutionError, 'No such file or directory'):
                    run_validator(
                        schema=contents,
                        data=valid_edge_data
                    )

                # inject an $id with the current file path
                contents['$id'] = file_path
                self.assertEqual(
                    run_validator(
                        schema=contents,
                        data=valid_edge_data,
                    ),
                    valid_edge_data
                )

    def test_complex_schema_references(self):
        """test validation with complex references that reference other references"""

        valid_data = {
          'node': {
            'id': 'TAIR:19830',
            'type': 'gene',
          },
          'edge': valid_edge_data,
          'marks_out_of_ten': 5
        }

        invalid_data = {
          'node': {
            'id': 'TAIR:19830',
            'type': 'gene',
          },
          'edge': invalid_edge_data,
          'marks_out_of_ten': 5
        }

        err_msg = "'whatever' is not valid under any of the given schemas"
        for file_ext in ['json', 'yaml']:
            file_path = os_path.join(
                *(test_data_dirs + ['schema_refs', 'level_1']),
                'test_object.' + file_ext
            )

            # data fails validation
            with self.assertRaisesRegex(ValidationError, err_msg):
                run_validator(
                    schema_file=file_path,
                    data=invalid_data,
                )

            self.assertEqual(
                run_validator(
                    schema_file=file_path,
                    data=valid_data,
                ),
                valid_data
            )
