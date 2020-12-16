"""
Tests for manifest.schema.json

Ensure that the manifest schema correctly validates data.

These tests run within the re_api docker image.
"""
import unittest
import os.path as os_path
from relation_engine_server.utils.json_validation import run_validator
from jsonschema.exceptions import ValidationError

schema_file = os_path.join("/app", "spec", "datasets", "djornl", "manifest.schema.json")
_TEST_DIR = os_path.join("/app", "spec", "test", "djornl")


class Test_Manifest_Schema(unittest.TestCase):
    def test_load_invalid_manifest(self):
        """ test an invalid manifest file """

        invalid_dir = os_path.join(_TEST_DIR, "invalid_manifest")

        error_list = [
            {
                # no file list provided
                "file": "no_file_list",
                "msg": "'file_list' is a required property",
            },
            {
                # a cluster file entry should have a prefix
                "file": "cluster_no_prefix",
                "msg": r"{'data_type': 'cluster', 'path': 'I2_named.tsv'} is not valid under any of the given schemas",
            },
            {
                # each file_list entry has to have a path
                "file": "missing_path",
                "msg": "'path' is a required property",
            },
            {
                # if the date is not quoted, pyyaml will turn it into a date object. Doh!
                "file": "date_not_in_quotes",
                "msg": "datetime.date\(2020, 12, 25\) is not of type 'string'",
            },
            {
                # file format is invalid
                "file": "invalid_format",
                "msg": "'txt' is not one of \['tsv', 'csv'\]",
            },
            {
                # there must be an indicator of file format
                "file": "no_file_format",
                "msg": r"{'data_type': 'edge', 'date': '2020-12-25', 'path': 'edge_data'}"
                + " is not valid under any of the given schemas",
            },
        ]

        for entry in error_list:
            data_file = os_path.join(invalid_dir, entry["file"] + ".yaml")
            print("looking at " + data_file)

            with self.assertRaisesRegex(ValidationError, entry["msg"]):
                run_validator(
                    schema_file=schema_file, data_file=data_file, nicer_errors=True
                )

    def test_load_valid_manifests(self):

        valid_dir = os_path.join(_TEST_DIR, "valid_manifest")
        file_list = ["with_descriptions", "no_file_ext", "no_file_format"]

        for file in file_list:
            data_file = os_path.join(valid_dir, file + ".yaml")
            print("looking at " + data_file)

            self.assertTrue(
                run_validator(
                    schema_file=schema_file, data_file=data_file, nicer_errors=True
                )
            )
