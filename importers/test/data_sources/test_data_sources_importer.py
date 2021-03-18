import os
import unittest
import io
import responses
from unittest.mock import patch
from importers.data_sources.importer import \
    Importer, note, do_import, main, get_args, \
    init, get_relative_dir
from spec.test.helpers import modified_environ

API_URL = 'http://localhost:5000'


def make_importer(data_path, warm_config=True, use_env_data=True):
    # Data files are located in the test directory
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # ... in the data directory
    # ... and in the specified data path
    test_data_path = os.path.join(dir_path, "data", data_path)
    print('\nTEST DATA PATH', test_data_path, use_env_data)
    if use_env_data:
        with modified_environ(RES_ROOT_DATA_PATH=test_data_path):
            importer = Importer()
            # coerce the importer to pick up ROOT_DATA_PATH from the temporary
            # env. If done after leaving this block, the env var will return to
            # its previous value.
            if warm_config:
                path = importer.get_config_or_fail('ROOT_DATA_PATH')
                assert path == test_data_path
            return importer
    else:
        importer = Importer()
        if warm_config:
            path = importer.get_config_or_fail('API_URL')
            assert path is not None
        return importer


class Test_data_sources_functions(unittest.TestCase):
    def test_note(self):
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
            with patch('sys.stdout', new = io.StringIO()) as mock_stdout:
                note(*case['input'])
                self.assertEqual(mock_stdout.getvalue(), case['expected'])



class Test_data_sources_Importer(unittest.TestCase):
    # @classmethod
    # def setUp(cls):
    #     # import the results file
    #     # results_file = os.path.join(_TEST_DIR, "djornl", "results.json")
    #     dir_path = os.path.dirname(os.path.realpath(__file__))
    #     root_data_path = os.path.join(dir_path, "data")
    #     with modified_environ(RES_ROOT_DATA_PATH=root_data_path):

    def test_get_config(self):
        imp = make_importer('standard')
        self.assertIsNotNone(imp.get_config('API_URL', None))
        self.assertIsNone(imp.get_config('foo', None))
        imp = make_importer('standard', warm_config=False)
        self.assertIsNotNone(imp.get_config('API_URL', None))

    def test_get_config_or_fail(self):
        imp = make_importer('standard')
        self.assertIsNotNone(imp.get_config_or_fail('API_URL'))
        with self.assertRaises(KeyError):
            imp.get_config_or_fail('foo')
        imp = make_importer('standard', warm_config=False)
        self.assertIsNotNone(imp.get_config_or_fail('API_URL'))

    def test_happy_load(self):
        imp = make_importer('standard')
        self.assertTrue(imp)
        result = imp.load_data(dry_run=True)
        self.assertTrue(result)

    def test_happy_load_default_data_dir(self):
        """Create importer which uses canonical data"""
        imp = make_importer('standard', use_env_data=False)
        result = imp.load_data(dry_run=True)
        self.assertTrue(result)

    def test_happy_load_bad_dir(self):
        imp = make_importer('bad_dir')
        result = imp.load_data(dry_run=True)
        self.assertFalse(result)

    def test_bad_ns(self):
        imp = make_importer('bad_ns')
        result = imp.load_data(dry_run=True)
        self.assertFalse(result)
        result = imp.load_data(dry_run=False)
        self.assertFalse(result)

    @responses.activate
    def test_save_docs(self):
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=200)
        imp = make_importer('standard')
        result = imp.load_data(dry_run=False)
        self.assertTrue(result)

    @responses.activate
    def test_save_docs_error(self):
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=400)
        imp = make_importer('standard')
        with self.assertRaises(RuntimeError):
            result = imp.load_data(dry_run=False)

    def test_do_import_dry_run(self):
        do_import(dry_run=True)
        self.assertTrue(True)

    @responses.activate
    def test_do_import_dry_run(self):
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=200)
        do_import(dry_run=False)
        self.assertTrue(True)

    @responses.activate
    def test_do_import_dry_run(self):
        responses.add(responses.PUT, f'{API_URL}/api/v1/documents',
                      json={'do_not': 'care'}, status=400)
        with self.assertRaises(SystemExit) as se:
            do_import(dry_run=False)
        self.assertEqual(se.exception.code, 1)

    def test_main_dry_run(self):
        my_get_args = MyArgs(True)
        with patch('importers.data_sources.importer.get_args', return_value=my_get_args) as mock_get_args:
            with self.assertRaises(SystemExit) as se:
                main()
            self.assertEqual(se.exception.code, 0)

    def test_get_args_(self):
        my_get_args = MyArgs(True)
        with patch('argparse.ArgumentParser.parse_args', return_value=my_get_args) as mock_parse_args:
            args = get_args()
            self.assertEqual(args.dry_run, True)

        my_get_args = MyArgs(False)
        with patch('argparse.ArgumentParser.parse_args', return_value=my_get_args) as mock_parse_args:
            args = get_args()
            self.assertEqual(args.dry_run, False)

    def test__main__dry_run(self):
        from importers.data_sources import importer
        my_get_args = MyArgs(True)
        with patch('argparse.ArgumentParser.parse_args', return_value=my_get_args) as mock_parse_args:
            with patch.object(importer, '__name__', '__main__'):
                with self.assertRaises(SystemExit) as se:
                    init()
                self.assertEqual(se.exception.code, 0)

    def test_get_relative_dir(self):
        from importers.data_sources import importer
        with patch.object(importer, '__file__', '/foo/file.py'):
            result = get_relative_dir('bar')
            self.assertEqual(result, '/foo/bar')


class MyArgs:
    def __init__(self, dry_run):
        self.dry_run = dry_run


# def make_my_args(dry_run):
#     args = MyArgs(dry_run)

# tests:
# happy path:
# - load data




# sad  path:
# - load dta with all sorts of problems
