import io
import os
import unittest
from unittest.mock import patch

import responses

from importers.data_sources.importer import \
    Importer, note, do_import, main, get_args, \
    init, get_relative_dir
from spec.test.helpers import modified_environ

API_URL = 'http://localhost:5000'


def make_importer(data_path, use_env_data=True):
    # Data files are located in the test directory
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # ... in the data directory
    # ... and in the specified data path
    test_data_path = os.path.join(dir_path, "data", data_path)
    print('\nTEST DATA PATH', test_data_path, use_env_data)
    if use_env_data:
        with modified_environ(RES_ROOT_DATA_PATH=test_data_path):
            importer = Importer()
            return importer
    else:
        importer = Importer()
        return importer


class TestDataSourcesFunctions(unittest.TestCase):
    def test_note(self):
        """
        Tests all note styles, and a non-existent style.
        """
        cases = [
            {
                'input': ['info', 'hi'],
                'expected': '[importer] ℹ hi\n'
            },
            {
                'input': ['success', 'hello'],
                'expected': '[importer] ✓ hello\n'
            },
            {
                'input': ['warning', 'uh-oh'],
                'expected': '[importer] ⚠ uh-oh\n'
            },
            {
                'input': ['error', 'oops'],
                'expected': '[importer] 🐛 oops\n'
            },
            {
                'input': ['na', 'questionable'],
                'expected': '[importer] ? questionable\n'
            },
        ]

        for case in cases:
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                note(*case['input'])
                self.assertEqual(mock_stdout.getvalue(), case['expected'])


class MyArgs:
    def __init__(self, dry_run, quiet):
        self.dry_run = dry_run
        self.quiet = quiet


class TestDataSourcesImporter(unittest.TestCase):
    def test_get_config(self):
        """
        The `get_config` method does returns either the 
        requested config value, or a default value
        """
        imp = make_importer('standard')
        # The `API_URL` key should be defined.
        self.assertIsNotNone(imp.get_config('API_URL', None))
        # But "foo" not, and None is a good default value signal.
        self.assertIsNone(imp.get_config('foo', None))
        # But "foo" not, leave out default value.
        self.assertIsNone(imp.get_config('foo', None))
        # Provide a silly default values.
        # But "foo" not
        self.assertEquals(imp.get_config('foo', 'silly'), 'silly')

    def test_get_config_or_fail(self):
        """
        The `get_config_or_fail` method, on the other hand, raises a
        `KeyError` if the given config key does not exist.
        """
        imp = make_importer('standard')
        # The `API_URL` key should be defined.
        self.assertIsNotNone(imp.get_config_or_fail('API_URL'))
        # But the `foo` key is not, and should raise
        with self.assertRaises(KeyError):
            imp.get_config_or_fail('foo')

    def test_load_data_dry_run(self):
        """
        A dry run load using standard test data.
        """
        imp = make_importer('standard')
        self.assertTrue(imp)
        result = imp.load_data(dry_run=True)
        self.assertTrue(result)

    def test_load_data_dry_run_default_data_dir(self):
        """
        A dry run load which uses the canonical (built-in) data
        """
        imp = make_importer('standard', use_env_data=False)
        result = imp.load_data(dry_run=True)
        self.assertTrue(result)

    def test_load_data_dry_run_bad_dir(self):
        """
        A dry run load which uses a bad data loading directory.
        (Really a test of our test helper function.)
        """
        imp = make_importer('bad_dir')
        with self.assertRaises(Exception):
            imp.load_data(dry_run=True)

    def test_load_data_bad_ns(self):
        """
        Dry and non-dry runs using load data with bad namespaces (ns)
        """
        imp = make_importer('bad_ns')
        result = imp.load_data(dry_run=True)
        self.assertFalse(result)
        result = imp.load_data(dry_run=False)
        self.assertFalse(result)

    @responses.activate
    def test_load_data_non_dry_run_mocked(self):
        """
        Non-dry run load using a mocked RE API endpoint which should succeed.
        """
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=200)
        imp = make_importer('standard')
        result = imp.load_data(dry_run=False)
        self.assertTrue(result)

    @responses.activate
    def test_load_data_non_dry_run_mocked_error_response(self):
        """
        Non-dry run load using a moocked RE API endpoint which
        should fail.
        """
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=400)
        imp = make_importer('standard')
        with self.assertRaises(RuntimeError):
            imp.load_data(dry_run=False)

    def test_do_import_dry_run(self):
        do_import(dry_run=True)
        self.assertTrue(True)

    @responses.activate
    def test_do_import_not_dry_run(self):
        """
        Non-dry-run load should be happy with a 200 response
        """
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=200)
        do_import(dry_run=False)
        self.assertTrue(True)

    @responses.activate
    def test_do_import_exits_with_error(self):
        """
        Non-dry-run load should exit with an error return code (1) if
        the attempt yields a 400 error response.
        """
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=400)
        with self.assertRaises(SystemExit) as se:
            do_import(dry_run=False)
        self.assertEqual(se.exception.code, 1)

    def test_main_dry_run(self):
        """
        Calling the main() entry point with with a dry run requested,
        using the default data path should succeed.
        """
        my_get_args = MyArgs(dry_run=True, quiet=True)
        with patch('importers.data_sources.importer.get_args',
                   return_value=my_get_args) as mock_get_args:
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
                cases.append({'dry_run': dry_run, 'quiet': quiet})

        for case in cases:
            my_get_args = MyArgs(dry_run=case['dry_run'], quiet=case['quiet'])
            with patch('argparse.ArgumentParser.parse_args', return_value=my_get_args):
                args = get_args()
                self.assertEqual(args.dry_run, case['dry_run'])
                self.assertEqual(args.quiet, case['quiet'])

    def test__main__dry_run(self):
        """
        Ensure that the init() entry point, when invoked for dry run and
        using the default data files, succeeds.
        """
        from importers.data_sources import importer
        my_get_args = MyArgs(dry_run=True, quiet=True)
        with patch('argparse.ArgumentParser.parse_args', return_value=my_get_args):
            with patch.object(importer, '__name__', '__main__'):
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
        with patch.object(importer, '__file__', '/foo/file.py'):
            result = get_relative_dir('bar')
            self.assertEqual(result, '/foo/bar')
