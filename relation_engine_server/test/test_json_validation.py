"""
Test JSON validation functions

The majority of the validation tests use `test_schema`, defined below and replicated as
JSON and YAML files. The tests are run with files and data structures for both the schema
and the data to be validated to ensure that all formats function the same.

Test data files are in relation_engine_server/test/data/json_validation

schema files: test_schema.json and test_schema.yaml (replicates test_schema)
data files: generally named (in)?valid_<test_type>.(json|yaml)

Other validation tests are at the bottom of the file.

These tests run within the re_api docker image.
"""
import unittest
import os.path as os_path
import json
import yaml
from relation_engine_server.utils.json_validation import run_validator
from jsonschema.exceptions import ValidationError, RefResolutionError
from jsonpointer import JsonPointerException

test_data_dirs = ["/app", "relation_engine_server", "test", "data"]
json_validation_dir = os_path.join(*(test_data_dirs + ["json_validation"]))
schema_refs_dir = os_path.join(*(test_data_dirs + ["schema_refs"]))


test_schema = {
    "properties": {
        "params": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "format": "regex",
                    "pattern": "^\\w+$",
                    "default": "blank",
                },
                "distance": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 1,
                },
                "home_page": {
                    "type": "string",
                    "format": "uri",
                },
                "date": {
                    "title": "date",
                    "description": "A type of dried fruit",
                    "type": "string",
                    "format": "date",
                },
                "fruits": {
                    "type": "array",
                    "items": {
                        "name": "fruit",
                        "type": "string",
                        "oneOf": [
                            {"const": "peach"},
                            {"const": "plum"},
                            {"const": "pear"},
                            {"const": "strawberry"},
                        ],
                    },
                    "default": [],
                    "uniqueItems": True,
                },
            },
        }
    }
}

fruits_explicit = {
    "type": "array",
    "items": {
        "name": "fruit",
        "type": "string",
        "oneOf": [
            {"const": "peach"},
            {"const": "plum"},
            {"const": "pear"},
            {"const": "strawberry"},
        ],
    },
    "default": [],
    "uniqueItems": True,
}

fruits_array_ref = {
    "$ref": "file://"
    + os_path.join(json_validation_dir, "fruits_array.yaml")
    + "#/definitions/fruits"
}

fruit_ref = {
    "type": "array",
    "items": {"$ref": "file://" + os_path.join(json_validation_dir, "fruit.yaml")},
    "default": [],
    "uniqueItems": True,
}

valid_json_loc = "/properties/params"
schema_defaults = {"name": "blank", "distance": 1, "fruits": []}

test_schema_list = [
    ["schema", test_schema],
    ["schema_file", os_path.join(json_validation_dir, "test_schema.json")],
    ["schema_file", os_path.join(json_validation_dir, "test_schema.yaml")],
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
        """test errors in the validator that are unrelated to the validation functionality"""

        err_str = "Please supply either a schema or a schema file path"
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator()

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(data={})

        # only supply one of schema or schema_file
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, schema_file="/path/to/file")

        err_str = "Please supply either a data structure or a data file path"
        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={})

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, data={}, data_file="")

        with self.assertRaisesRegex(ValueError, err_str):
            run_validator(schema={}, data=None, data_file=None)

        # invalid file type
        test_file = os_path.join(*(test_data_dirs + ["test_file.md"]))
        err_msg = f"Unknown file type encountered: {test_file}"
        with self.assertRaisesRegex(TypeError, err_msg):
            run_validator(schema_file=test_file, data={})

        # invalid jsonpointer string
        err_str = "Location must start with /"
        json_loc = "start validating here"
        with self.assertRaisesRegex(JsonPointerException, err_str):
            run_validator(schema=test_schema, data={}, validate_at=json_loc)

        # invalid jsonpointer ref
        err_str = "member 'property' not found in"
        json_loc = "/properties/params/property"
        with self.assertRaisesRegex(JsonPointerException, err_str):
            run_validator(schema=test_schema, data={}, validate_at=json_loc)

        # finally!!
        output = run_validator(
            schema=test_schema,
            data={"name": "name", "distance": 3},
            validate_at=valid_json_loc,
        )
        self.assertEqual(output, {**schema_defaults, **{"name": "name", "distance": 3}})

    def test_json_validation(self):
        """ Generic JSON validation tests to ensure that all is working as expected """

        # run these tests with the schema as a data structure, as JSON, and as YAML
        test_list = [
            self.test_add_defaults,
            self.test_pattern_validation,
            self.test_uri_validation,
            self.test_date_format_validation,
            self.test_array_validation,
        ]

        for test_schema in test_schema_list:
            schema_file_arg = schema_arg = test_schema[1]

            if test_schema[0] == "schema":
                schema_file_arg = None
            else:
                schema_arg = None

            for test_name in test_list:
                with self.subTest(test_name=test_name.__name__):
                    test_name(schema_arg, schema_file_arg)

    def execute_tests(
        self, schema_arg, schema_file_arg, tests, file_types=[None, "json", "yaml"]
    ):

        for t in tests:
            for file_ext in file_types:
                data = t["input"]
                data_file = os_path.join(json_validation_dir, f"{t['file']}.{file_ext}")
                if file_ext is None:
                    data_file = None
                else:
                    data = None

                with self.subTest(input=t["input"], file_type=file_ext):
                    if "err_str" in t:
                        with self.assertRaisesRegex(ValidationError, t["err_str"]):
                            run_validator(
                                schema=schema_arg,
                                schema_file=schema_file_arg,
                                data=data,
                                data_file=data_file,
                                validate_at=valid_json_loc,
                            )

                    else:
                        output = run_validator(
                            schema=schema_arg,
                            schema_file=schema_file_arg,
                            data=data,
                            data_file=data_file,
                            validate_at=valid_json_loc,
                        )
                        self.assertEqual(output, {**schema_defaults, **t["output"]})

    def test_add_defaults(self, schema_arg=None, schema_file_arg=None):
        """Test that the jsonschema validator sets default values."""

        # skip if the test is not being called from test_json_validation
        if schema_arg is None and schema_file_arg is None:
            self.assertTrue(True)
            return

        tests = [
            {
                "input": {},
                "file": "defaults",
                "output": schema_defaults,
            }
        ]

        self.execute_tests(schema_arg, schema_file_arg, tests)

    def test_pattern_validation(self, schema_arg=None, schema_file_arg=None):
        """Test pattern validation"""

        # skip if the test is not being called from test_json_validation
        if schema_arg is None and schema_file_arg is None:
            self.assertTrue(True)
            return

        tests = [
            {
                "input": {
                    "name": "what's-the-problem with-this-string?",
                    "distance": 3,
                },
                "file": "invalid_pattern",
                "err_str": r'"what\'s-the-problem with-this-string\?" does not match .*?',
            },
            {
                "input": {"name": "No_problem_with_this_string", "distance": 3},
                "file": "valid_pattern",
                "output": {
                    "name": "No_problem_with_this_string",
                    "distance": 3,
                },
            },
        ]
        self.execute_tests(schema_arg, schema_file_arg, tests)

    def test_uri_validation(self, schema_arg=None, schema_file_arg=None):
        """Test URI validation is operational"""

        # skip if the test is not being called from test_json_validation
        if schema_arg is None and schema_file_arg is None:
            self.assertTrue(True)
            return

        tests = [
            {
                "input": {
                    "name": "valid_uri",
                    "distance": 3,
                    "home_page": "http://json-validation.com:5000/this/is/valid",
                },
                "file": "valid_uri",
                "output": {
                    "name": "valid_uri",
                    "distance": 3,
                    "home_page": "http://json-validation.com:5000/this/is/valid",
                },
            },
            {
                "input": {"name": "invalid_uri", "home_page": "where is it?"},
                "file": "invalid_uri",
                "err_str": r"'where is it\?' is not a 'uri'",
            },
        ]

        self.execute_tests(schema_arg, schema_file_arg, tests)

    def test_date_format_validation(self, schema_arg=None, schema_file_arg=None):
        """ensure that fancy date formats are correctly validated"""

        # skip if the test is not being called from test_json_validation
        if schema_arg is None and schema_file_arg is None:
            self.assertTrue(True)
            return

        tests = [
            {
                "input": {"date": "20200606"},
                "file": "invalid_date",
                "err_str": "'20200606' is not a 'date'",
            },
            {
                "input": {"date": 20200606},
                "file": "invalid_date_type",
                "err_str": "20200606 is not of type 'string'",
            },
            {
                "input": {"name": "valid_date", "date": "2020-06-06", "distance": 3},
                "file": "valid_date",
                "output": {
                    **schema_defaults,
                    "name": "valid_date",
                    "date": "2020-06-06",
                    "distance": 3,
                },
            },
        ]

        self.execute_tests(schema_arg, schema_file_arg, tests)

        # pyyaml-specific issue: dates get automatically parsed into datetime objects (doh!)
        file_path = os_path.join(json_validation_dir, "unquoted_date.yaml")
        err_str = r"datetime.date\(2020, 6, 6\) is not of type 'string'"
        with self.assertRaisesRegex(ValidationError, err_str):
            run_validator(
                schema=schema_arg,
                schema_file=schema_file_arg,
                data_file=file_path,
                validate_at=valid_json_loc,
            )

    def test_array_validation(self, schema_arg=None, schema_file_arg=None):
        """
        check array validation and default population works correctly when refs are used

        The current implementation of the population of defaults does not allow defaults to be
        populated if the property is a reference, i.e.

        'properties': {
            'fruits': {
                '$ref': '...'
            }
        }

        """

        # skip if the test is not being called from test_json_validation
        if schema_arg is None and schema_file_arg is None:
            self.assertTrue(True)
            return

        # test the use of refs when populating defaults
        tests = [
            {
                "fruits": fruit_ref,
                "name": "using fruit.yaml -- array item is a ref",
                "output": {"params": {"name": "name", "distance": 1, "fruits": []}},
            },
            {
                # N.b. the default does not get populated in this case!
                # This is a change from the expected functionality
                "fruits": fruits_array_ref,
                "name": "using fruits_array.yaml -- the array is a ref",
                "output": {
                    "params": {
                        "name": "name",
                        "distance": 1,
                    }
                },
            },
            {
                "fruits": fruits_explicit,
                "name": "with no references",
                "output": {"params": {"name": "name", "distance": 1, "fruits": []}},
            },
        ]

        for t in tests:
            with self.subTest(desc=t["name"]):
                test_schema["properties"]["params"]["properties"]["fruits"] = t[
                    "fruits"
                ]
                output = run_validator(
                    schema=test_schema, data={"params": {"name": "name"}}
                )
                self.assertEqual(output, t["output"])

        # restore the original value
        test_schema["properties"]["params"]["properties"]["fruits"] = fruits_explicit

    def test_schema_references(self):
        """Ensure referenced schemas, including those written in yaml, can be accessed."""

        # same schema in different places
        path_list = [[], ["level_1"], ["level_1", "level_2"]]

        err_msg = "'whatever' is not valid under any of the given schemas"
        for path in path_list:

            for file_ext in ["json", "yaml"]:
                with self.subTest(file_ext=file_ext):
                    file_path = os_path.join(
                        *(test_data_dirs + ["schema_refs"] + path), "edge." + file_ext
                    )

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
                        valid_edge_data,
                    )

                    # validate using the schema instead of the schema_file
                    with open(file_path) as fd:
                        contents = (
                            yaml.safe_load(fd) if file_ext == "yaml" else json.load(fd)
                        )

                    # if there is no $id in the schema, the ref resolver won't know
                    # where the schema file is located and will not resolve relative references
                    with self.assertRaisesRegex(
                        RefResolutionError, "No such file or directory"
                    ):
                        run_validator(schema=contents, data=valid_edge_data)

                    # inject an $id with the current file path
                    contents["$id"] = file_path
                    self.assertEqual(
                        run_validator(
                            schema=contents,
                            data=valid_edge_data,
                        ),
                        valid_edge_data,
                    )

    def test_complex_schema_references(self):
        """test validation with complex references that reference other references"""

        valid_data = {
            "node": {
                "id": "TAIR:19830",
                "type": "gene",
            },
            "edge": valid_edge_data,
            "marks_out_of_ten": 5,
        }

        invalid_data = {
            "node": {
                "id": "TAIR:19830",
                "type": "gene",
            },
            "edge": invalid_edge_data,
            "marks_out_of_ten": 5,
        }

        err_msg = "'whatever' is not valid under any of the given schemas"
        for file_ext in ["json", "yaml"]:
            with self.subTest(file_ext=file_ext):
                file_path = os_path.join(
                    *(test_data_dirs + ["schema_refs", "level_1"]),
                    "test_object." + file_ext,
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
                    valid_data,
                )
