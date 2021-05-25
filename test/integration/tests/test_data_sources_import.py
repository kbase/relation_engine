import subprocess
import requests
import json
import sys
import os
import unittest

#
# We are already running Python, of course, but we need to invoke another
# python instance in a subprocess.
#
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)

#
# Set up urls required by the integration tests.
# The default values are for local tests
#
RE_API_URL = os.environ.get("RE_API_URL")
if RE_API_URL is None:
    print(f'the "RE_API_URL" environment variable is required')
    sys.exit(1)

ARANGO_URL = os.environ.get("ARANGO_URL")
if ARANGO_URL is None:
    print(f'the "ARANGO_URL" environment variable is required')
    sys.exit(1)

#
# If true, causes --quiet to be passed to the importer, which will cause it
# to suppress any console notes.
#
QUIET = os.environ.get("QUIET", "True") == "True"


# Utilities


def get_relative_dir(relative_path):
    """
    Utility function to return the full path for a given sub-path
    relative to the directory this source file resides in.
    """
    this_dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(this_dir_path, "..", relative_path)


def fail_test():
    assert False


class RequestError(Exception):
    def __init__(self, message, response):
        self.message = message
        self.status_code = response.status_code


# Tiny arrango client to support the tests


def arango(path, method="GET"):
    url = f"{ARANGO_URL}/_api/{path}"

    params = {}

    return requests.request(method=method, url=url, params=params)


def collection_count():
    return arango("collection/data_sources_nodes/count")


def clear_collection():
    return arango("collection/data_sources_nodes/truncate", "PUT")


# Tiny RE_API client to support the tests


def query(token, collection_type, namespaces):
    url = f"{RE_API_URL}/api/v1/query_results"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token

    if namespaces is None:
        stored_query = "data_sources_get_all_data_sources"
    else:
        stored_query = "data_sources_get_data_sources"
    params = {"stored_query": stored_query}

    data = {"type": collection_type}
    if namespaces is not None:
        data["ns"] = namespaces

    return requests.request(
        method="POST", url=url, data=json.dumps(data), params=params
    )


def fetch_data_sources(token, source_type):
    return query(token, source_type, None)


def check_response(response):
    if response.status_code != 200:
        raise RequestError(f"Request Unsuccessful: {response.status_code}", response)
    return response


def do_import(token, data_path=None):
    command_args = [PYTHON_BIN, "-m", "importers.data_sources.importer"]
    if QUIET:
        command_args.append("--quiet")

    env = {"RES_AUTH_TOKEN": token, "RES_API_URL": os.environ.get("RE_API_URL")}
    if data_path is not None:
        env["RES_ROOT_DATA_PATH"] = data_path

    subprocess.run(command_args, check=True, env=env)


# The Tests


class DataSourcesTests(unittest.TestCase):
    # Assertion helpers
    def assert_collection_count(self, count):
        collection_stats = check_response(collection_count()).json()
        self.assertEqual(collection_stats["count"], count)

    def assert_data_sources_count(self, source_type, count):
        all_data_sources = check_response(
            fetch_data_sources("non_admin_token", source_type)
        ).json()
        self.assertEqual(all_data_sources["count"], count)
        self.assertFalse(all_data_sources["has_more"])
        self.assertEqual(len(all_data_sources["results"]), count)

    def assert_will_fail(self, fun):
        expected_code = 1
        check_response(clear_collection())
        with self.assertRaises(subprocess.CalledProcessError) as cpe:
            fun()

        self.assertEqual(cpe.exception.returncode, expected_code)
        collection_stats = check_response(collection_count()).json()
        self.assertEqual(collection_stats["count"], 0)

    # Tests
    def test_import_admin(self):
        check_response(clear_collection())
        self.assert_collection_count(0)
        do_import("admin_token")
        self.assert_collection_count(6)
        self.assert_data_sources_count("taxonomy", 4)
        self.assert_data_sources_count("ontology", 2)

    def test_import_non_admin(self):
        def importer():
            do_import("non_admin_token")

        self.assert_will_fail(importer)

    def test_import_invalid_token(self):
        def importer():
            do_import("invalid_token")

        self.assert_will_fail(importer)

    def test_import_no_token(self):
        def importer():
            do_import("")

        self.assert_will_fail(importer)

    def test_import_alternate_data(self):
        check_response(clear_collection())
        self.assert_collection_count(0)
        do_import("admin_token", get_relative_dir("data/data_sources/good"))
        self.assert_collection_count(3)
        self.assert_data_sources_count("taxonomy", 2)
        self.assert_data_sources_count("ontology", 1)

    def test_import_bad_data(self):
        def importer():
            do_import("admin_token", get_relative_dir("data/data_sources/bad"))

        self.assert_will_fail(importer)

    def test_import_alternate_no_data(self):
        check_response(clear_collection())
        self.assert_collection_count(0)
        do_import("admin_token", get_relative_dir("data/data_sources/none"))
        self.assert_collection_count(0)
        self.assert_data_sources_count("taxonomy", 0)
        self.assert_data_sources_count("ontology", 0)

    def test_import_bad_directory(self):
        def importer():
            do_import(
                "admin_token", get_relative_dir("data/data_sources/does_not_exist")
            )

        self.assert_will_fail(importer)


# Main and friends


def main():
    unittest.main()


if __name__ == "__main__":
    main()
