"""
Tests for the schema validation functions

These tests run within the re_api docker image, and require access to the ArangoDB image for validation of AQL strings.
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
    validate_all,
    validate_all_by_type,
)

_TEST_DIR = "/app/spec/test/sample_schemas"


class TestValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wait_for_arangodb()

    def test_validate_schema(self):
        """Validate a single file using the generic validate_schema method"""

        err_msg = "No validation schema found for 'made-up_schema'"
        with self.assertRaisesRegex(ValueError, err_msg):
            validate_schema("/path/to/file", "made-up_schema")

    def test_validate_collection_errors(self):
        """Testing collection-specific schema errors"""

        base_dir = os_path.join(_TEST_DIR, "collections")

        error_list = [
            {
                "msg": "Name key should match filename: test_nodes vs wrong_name",
                "file": "wrong_name.yaml",
                "err": ValueError,
            },
            {
                "msg": "'http://json-schema.org/draft-07/schema#' is not of type 'object'",
                "file": "schema_not_object.yaml",
            },
            {
                "msg": "Additional properties are not allowed \('title' was unexpected\)",
                "file": "extra_top_level_entries.yaml",
            },
            {
                "msg": 'Time-travel edge schemas must require "from" and "to" attributes in ',
                "file": "edge_delta_missing_to_from.yaml",
            },
            {
                "msg": 'Edge schemas must require "_from" and "_to" attributes in ',
                "file": "edge_missing_to_from.yaml",
            },
            {
                "msg": 'Vertex schemas must require the "_key" attribute in ',
                "file": "vertex_missing_key.yaml",
            },
            {
                "msg": 'Time-travel vertex schemas must require the "id" attribute in ',
                "file": "vertex_missing_id.yaml",
            },
        ]

        for entry in error_list:
            err_type = entry["err"] if "err" in entry else ValidationError
            # generic method, requires schema type
            with self.assertRaisesRegex(err_type, entry["msg"]):
                validate_schema(os_path.join(base_dir, entry["file"]), "collection")
            # specific method
            with self.assertRaisesRegex(err_type, entry["msg"]):
                validate_collection(os_path.join(base_dir, entry["file"]))

        # TODO: add an example of a schema that validates but where data['schema'] is
        # not a valid json schema.

    def test_validate_collection(self):
        """Testing collection-specific schema errors"""

        base_dir = os_path.join(_TEST_DIR, "collections")

        # valid schemas -- check delta is set appropriately
        for type in ["edge", "vertex"]:
            data = validate_collection(os_path.join(base_dir, "test_" + type + ".yaml"))
            self.assertEqual(data["delta"], False)

            # delta is true:
            data = validate_collection(
                os_path.join(base_dir, "test_delta_" + type + ".yaml")
            )
            self.assertEqual(data["delta"], True)

    def test_validate_data_source(self):

        base_dir = os_path.join(_TEST_DIR, "data_sources")

        # working example
        output = validate_data_source(os_path.join(base_dir, "minimal.yaml"))
        self.assertEqual(
            output,
            {
                "name": "minimal",
                "category": "network",
                "title": "Example minimal data source",
            },
        )

        error_list = [
            {
                "msg": "Additional properties are not allowed \('type' was unexpected\)",
                "file": "invalid_additional_property.json",
            },
            {
                "msg": "'this is not a valid URI' is not a 'uri'",
                "file": "uri_validation.json",
            },
        ]

        for entry in error_list:
            err_type = entry["err"] if "err" in entry else ValidationError

            # generic method
            with self.assertRaisesRegex(err_type, entry["msg"]):
                validate_schema(os_path.join(base_dir, entry["file"]), "data_source")

            # same thing as above via specific method
            with self.assertRaisesRegex(err_type, entry["msg"]):
                validate_data_source(os_path.join(base_dir, entry["file"]))

    def test_validate_stored_query(self):

        base_dir = os_path.join(_TEST_DIR, "stored_queries")

        err_str = "False is not of type 'object'"
        with self.assertRaisesRegex(ValidationError, err_str):
            validate_stored_query(os_path.join(base_dir, "params_not_object.yaml"))

        # total nonsense instead of AQL
        err_str = "syntax error, unexpected identifier, expecting assignment"
        with self.assertRaisesRegex(ValueError, err_str):
            validate_stored_query(os_path.join(base_dir, "invalid_aql.yaml"))

        # invalid bind params
        err_str = "Bind vars are invalid"
        with self.assertRaisesRegex(ValueError, err_str):
            validate_stored_query(os_path.join(base_dir, "invalid_bind_params.yaml"))

    def test_validate_view(self):

        base_dir = os_path.join(_TEST_DIR, "views")
        output = {
            "name": "minimal",
            "type": "arangosearch",
        }

        self.assertEqual(
            validate_schema(os_path.join(base_dir, "minimal.json"), "view"), output
        )

        self.assertEqual(validate_view(os_path.join(base_dir, "minimal.json")), output)

        err_str = "'from the shore' is not one of \['arangosearch'\]"
        with self.assertRaisesRegex(ValidationError, err_str):
            validate_view(os_path.join(base_dir, "wrong_type.json"))

    def test_validate_all(self):
        """test all the files in a directory"""

        with self.assertRaisesRegex(
            ValueError, "No validation schema found for 'muffins'"
        ):
            validate_all("muffins")

        def validate_all_duplicate_names(self):
            with self.assertRaisesRegex(
                ValidationError, "duplicate_names failed validation"
            ):
                validate_all("collection", os_path.join(_TEST_DIR, "duplicate_names"))

        stdout = capture_stdout(validate_all_duplicate_names, self)
        self.assertRegex(stdout, "Duplicate queries named 'test_vertex'")

        sample_schemas = {
            "collection": "collections",
            "stored_query": "stored_queries",
            "view": "views",
            "data_source": "data_sources",
        }

        for (schema_type, directory) in sample_schemas.items():
            # n.b. this assumes all the schemas in /spec are valid!
            stdout = capture_stdout(validate_all, schema_type)
            self.assertRegex(stdout, r"...all valid")

            with self.assertRaises(Exception):
                validate_all(schema_type, os_path.join(_TEST_DIR, directory))

    def test_validate_all_by_type(self):
        """test all files of all types from a root directory"""

        # use value from config
        n_errors = validate_all_by_type()
        self.assertEqual(n_errors, 0)

        # known dodgy dir
        n_errors = validate_all_by_type(_TEST_DIR)
        self.assertGreater(n_errors, 0)
