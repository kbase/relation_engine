import io
import os
import unittest
from unittest.mock import patch

import responses

from importers.data_sources.importer import (
    Importer,
    note,
    do_import,
    main,
    get_args,
    init,
    get_relative_dir,
)

RE_API_URL = "http://localhost:5000"
AUTH_URL = "http://auth:5000"
AUTH_TOKEN = "admin_token"

ME_RESPONSE = {
    "created": 1578347292120,
    "lastlogin": 1628886788908,
    "display": "KBase UI Test User",
    "roles": [],
    "customroles": [],
    "policyids": [
        {"id": "data-policy.1", "agreedon": 1578347292120},
        {"id": "kbase-user.1", "agreedon": 1578347292120},
    ],
    "user": "kbaseuitest",
    "local": False,
    "email": "eapearson+kbaseuitest@lbl.gov",
    "idents": [
        {
            "provusername": "kbaseuitest@globusid.org",
            "provider": "Globus",
            "id": "91436b502ec80a8165c6691ca8a64029",
        }
    ],
}


def get_test_data_dir(data_path):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(dir_path, "data", data_path)


def make_importer(data_path, dry_run=None, auth_token=AUTH_TOKEN):
    test_data_path = get_test_data_dir(data_path)
    return Importer(
        re_api_url=RE_API_URL,
        data_dir=test_data_path,
        dry_run=dry_run,
        auth_token=auth_token,
    )


class TestDataSourcesFunctions(unittest.TestCase):
    def test_note(self):
        """
        Tests all note styles, and a non-existent style.
        """
        cases = [
            {"input": ["info", "hi"], "expected": "[importer] ℹ hi\n"},
            {"input": ["success", "hello"], "expected": "[importer] ✓ hello\n"},
            {"input": ["warning", "uh-oh"], "expected": "[importer] ⚠ uh-oh\n"},
            {"input": ["error", "oops"], "expected": "[importer] 🐛 oops\n"},
            {
                "input": ["na", "questionable"],
                "expected": "[importer] ? questionable\n",
            },
        ]

        for case in cases:
            with patch("sys.stdout", new=io.StringIO()) as mock_stdout:
                note(*case["input"])
                self.assertEqual(mock_stdout.getvalue(), case["expected"])


class MyArgs:
    def __init__(self, dry_run, quiet, re_api_url, auth_token, data_dir):
        self.dry_run = dry_run
        self.quiet = quiet
        self.re_api_url = re_api_url
        self.auth_token = auth_token
        self.data_dir = data_dir


class TestDataSourcesImporter(unittest.TestCase):
    def test_load_data_dry_run(self):
        """
        A dry run load using standard test data.
        """
        imp = make_importer("standard", dry_run=True)
        self.assertTrue(imp)
        result = imp.load_data()
        self.assertTrue(result)

    def test_load_data_dry_run_bad_dir(self):
        """
        A dry run load which uses a bad data loading directory.
        (Really a test of our test helper function.)
        """
        imp = make_importer("bad_dir", dry_run=True)
        with self.assertRaises(Exception):
            imp.load_data()

    def test_load_data_bad_ns(self):
        """
        Dry and non-dry runs using load data with bad namespaces (ns)
        """
        imp = make_importer("bad_ns", dry_run=True)
        result = imp.load_data()
        self.assertFalse(result)
        imp2 = make_importer("bad_ns", dry_run=False)
        result = imp2.load_data()
        self.assertFalse(result)

    @responses.activate
    def test_load_data_non_dry_run_mocked(self):
        """
        Non-dry run load using a mocked RE API endpoint which should succeed.
        """
        responses.add(
            responses.PUT,
            f"{RE_API_URL}/api/v1/documents",
            json={"do_not": "care"},
            status=200,
        )
        responses.add(
            responses.PUT, f"{AUTH_URL}/api/v2/me", json=ME_RESPONSE, status=200
        )
        imp = make_importer("standard", dry_run=False)
        result = imp.load_data()
        self.assertTrue(result)

    @responses.activate
    def test_load_data_non_dry_run_mocked_error_response(self):
        """
        Non-dry run load using a mocked RE API endpoint which
        should fail.
        """
        responses.add(
            responses.PUT,
            f"{RE_API_URL}/api/v1/documents",
            json={"do_not": "care"},
            status=400,
        )
        imp = make_importer("standard", dry_run=False, auth_token=AUTH_TOKEN)
        with self.assertRaises(RuntimeError):
            imp.load_data()

    def test_do_import_dry_run(self):
        do_import(
            dry_run=True,
            data_dir=get_test_data_dir("standard"),
            re_api_url=RE_API_URL,
            auth_token=AUTH_TOKEN,
        )
        self.assertTrue(True)

    @responses.activate
    def test_do_import_not_dry_run(self):
        """
        Non-dry-run load should be happy with a 200 response
        """
        responses.add(
            responses.PUT,
            f"{RE_API_URL}/api/v1/documents",
            json={"do_not": "care"},
            status=200,
        )
        do_import(
            dry_run=False,
            data_dir=get_test_data_dir("standard"),
            re_api_url=RE_API_URL,
            auth_token=AUTH_TOKEN,
        )
        self.assertTrue(True)

    @responses.activate
    def test_do_import_exits_with_error(self):
        """
        Non-dry-run load should exit with an error return code (1) if
        the attempt yields a 400 error response.
        """
        responses.add(
            responses.PUT,
            f"{RE_API_URL}/api/v1/documents",
            json={"do_not": "care"},
            status=400,
        )
        with self.assertRaises(SystemExit) as se:
            do_import(
                dry_run=False,
                data_dir=get_test_data_dir("standard"),
                re_api_url=RE_API_URL,
                auth_token=AUTH_TOKEN,
            )
        self.assertEqual(se.exception.code, 1)

    def test_main_dry_run(self):
        """
        Calling the main() entry point with with a dry run requested,
        using the default data path should succeed.
        """
        my_get_args = MyArgs(
            dry_run=True,
            quiet=True,
            re_api_url=RE_API_URL,
            data_dir=get_test_data_dir("standard"),
            auth_token=AUTH_TOKEN,
        )
        with patch(
            "importers.data_sources.importer.get_args", return_value=my_get_args
        ) as mock_get_args:
            with self.assertRaises(SystemExit) as se:
                main()
            self.assertEqual(se.exception.code, 0)

    def test_get_args_(self):
        """
        Ensure that the MyArgs helper class works correctly.
        """
        cases = []
        for dry_run in [True, False]:
            for quiet in [True, False]:
                cases.append({"dry_run": dry_run, "quiet": quiet})

        for case in cases:
            my_get_args = MyArgs(
                dry_run=case["dry_run"],
                quiet=case["quiet"],
                re_api_url=RE_API_URL,
                data_dir=get_test_data_dir("standard"),
                auth_token=AUTH_TOKEN,
            )
            with patch("argparse.ArgumentParser.parse_args", return_value=my_get_args):
                args = get_args()
                self.assertEqual(args.dry_run, case["dry_run"])
                self.assertEqual(args.quiet, case["quiet"])

    def test__main__dry_run(self):
        """
        Ensure that the init() entry point, when invoked for dry run and
        using the default data files, succeeds.
        """
        from importers.data_sources import importer

        my_get_args = MyArgs(
            dry_run=True,
            quiet=True,
            re_api_url=RE_API_URL,
            data_dir=get_test_data_dir("standard"),
            auth_token=AUTH_TOKEN,
        )
        with patch("argparse.ArgumentParser.parse_args", return_value=my_get_args):
            with patch.object(importer, "__name__", "__main__"):
                with self.assertRaises(SystemExit) as se:
                    init()
                self.assertEqual(se.exception.code, 0)

    def test_get_relative_dir(self):
        """
        Ensure that the helper function "get_relative_dir" finds a
        directory relative to the parent directory of the current script
        (mocked).
        """
        from importers.data_sources import importer

        with patch.object(importer, "__file__", "/foo/file.py"):
            result = get_relative_dir("bar")
            self.assertEqual(result, "/foo/bar")
