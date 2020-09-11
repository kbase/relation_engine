"""
Test spec_loader functions

These tests run within the re_api docker image.
"""
import unittest
import os.path as os_path
from urllib.parse import urlparse
from relation_engine_server.utils import spec_loader
from relation_engine_server.utils.spec_loader import SchemaNonexistent
from relation_engine_server.utils.config import get_config


class TestSpecLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os_path.join('/app', 'relation_engine_server', 'test')
        cls.test_spec_dir = os_path.join(cls.test_dir, 'spec_release', 'sample_spec_release')

        cls.config = get_config()
        cls.repo_path = cls.config['spec_paths']['repo']
        for key in cls.config['spec_paths'].keys():
            if cls.repo_path in cls.config['spec_paths'][key]:
                cls.config['spec_paths'][key] = cls.config['spec_paths'][key].replace(
                    cls.repo_path,
                    cls.test_spec_dir
                )

    @classmethod
    def tearDownClass(cls):
        # undo all the config changes
        for key in cls.config['spec_paths'].keys():
            if cls.test_spec_dir in cls.config['spec_paths'][key]:
                cls.config['spec_paths'][key] = cls.config['spec_paths'][key].replace(
                    cls.test_spec_dir,
                    cls.repo_path
                )

    def test_get_names(self, schema_type_names=[], expected=[]):
        """test getting the names of all the schemas of a given type"""

        # this method should only be run from another test method
        if len(schema_type_names) == 0:
            self.assertTrue(True)
            return

        schema_type_singular = schema_type_names[0]
        schema_type_plural = schema_type_names[1]
        method = getattr(spec_loader, 'get_' + schema_type_singular + '_names')

        # save the original value
        original_config_dir = self.config['spec_paths'][schema_type_plural]
        # set the config to the test directory
        self.config['spec_paths'][schema_type_plural] = os_path.join(self.test_dir, 'data', schema_type_plural)

        got_names_method = method()
        got_names_singular = spec_loader.get_names(schema_type_singular)
        got_names_plural = spec_loader.get_names(schema_type_plural)

        self.config['spec_paths'][schema_type_plural] = os_path.join(self.test_dir, 'data', 'empty')
        got_names_method_empty = method()
        got_names_empty = spec_loader.get_names(schema_type_singular)

        # restore the original value before running tests
        self.config['spec_paths'][schema_type_plural] = original_config_dir

        # ensure the results are as expected
        # get_collection_names
        self.assertEqual(set(expected), set(got_names_method))
        # get_names('collection')
        self.assertEqual(set(expected), set(got_names_singular))
        # get_names('collections')
        self.assertEqual(set(expected), set(got_names_plural))

        # empty collections dir
        self.assertEqual(got_names_method_empty, [])
        self.assertEqual(got_names_empty, [])

    def test_run_spec_loading_tests(self, schema_type_names=[], test_name=None):
        """test the different ways of returning a schema file path or its contents"""

        # only run the test if it's being called from another test
        if test_name is None:
            self.assertTrue(True)
            return

        schema_type_singular = schema_type_names[0]
        schema_type_plural = schema_type_names[1]
        # e.g. 'spec_loader.get_collection'
        method = getattr(spec_loader, 'get_' + schema_type_singular)

        # get the path of the requested file
        result_path = method(test_name, path_only=True)
        self.assertIsInstance(result_path, str)
        self.assertIn(test_name, result_path)
        self.assertIn(
            self.config['spec_paths'][schema_type_plural],
            result_path,
        )

        # use get_schema directly to get the file path
        for schema_type in schema_type_names:
            self.assertEqual(
                result_path,
                spec_loader.get_schema(schema_type, test_name, True)
            )

        # get the file contents
        result_obj = method(test_name)
        self.assertIs(type(result_obj), dict)
        self.assertEqual(result_obj['name'], test_name)

        # check the contents of the dict when getting a data source
        if schema_type_singular == 'data_source':

            # logo_url should start with the same base as config['kbase_endpoint']
            endpoint = urlparse(self.config['kbase_endpoint'])
            self.assertIn(endpoint.scheme + '://' + endpoint.netloc, result_obj['logo_url'])

            # logo_path is deleted
            self.assertNotIn('logo_path', result_obj.keys())

        # a nonexistent file raises the appropriate error
        fake_name = 'test/test_node'
        err_msg = schema_type_singular.capitalize().replace("_", " ") + " '" + fake_name + "' does not exist."
        with self.assertRaisesRegex(SchemaNonexistent, err_msg):
            method(fake_name, path_only=True)

    def test_get_schemas_of_various_types(self):
        """test retrieving schemas or paths to schemas for the different schema types"""

        schema_type_list = [
            {
                # schema_type_names: singular, plural
                'schema_type_names': ['collection', 'collections'],
                'example': 'ncbi_taxon',
                'names': ['core', 'edge', 'point', 'test_another_node', 'test_edge', 'test_node'],
            },
            {
                'schema_type_names': ['data_source', 'data_sources'],
                'example': 'ncbi_taxonomy',
            },
            {
                'schema_type_names': ['stored_query', 'stored_queries'],
                'example': 'ncbi_fetch_taxon',
            },
            {
                'schema_type_names': ['view', 'views'],
                'example': 'test_vertices',
            }
        ]

        for schema in schema_type_list:
            with self.subTest(schema=schema['schema_type_names'][0]):
                self.test_run_spec_loading_tests(schema['schema_type_names'], schema['example'])
                if 'names' in schema:
                    self.test_get_names(schema['schema_type_names'], schema['names'])

    def test_non_existent_schema(self):

        err_msg = 'Reality does not exist'
        with self.assertRaisesRegex(SchemaNonexistent, err_msg):
            spec_loader.get_names('Reality')

    def test_get_schema_for_doc(self):
        """test getting the schema for a specific document"""

        test_name = 'ncbi_taxon'
        test_doc = test_name + '/12345'
        # get the path of the requested file
        result_path = spec_loader.get_schema_for_doc(test_doc, path_only=True)
        self.assertIsInstance(result_path, str)
        self.assertIn(test_name, result_path)
        self.assertIn(
            self.config['spec_paths']['collections'],
            result_path,
        )

        # get the file contents
        result_obj = spec_loader.get_schema_for_doc(test_doc)
        self.assertIs(type(result_obj), dict)
        self.assertEqual(result_obj['name'], test_name)

        fake_name = 'fake_name/12345'
        # a nonexistent file raises the appropriate error
        err_msg = f"Collection 'fake_name' does not exist."
        with self.assertRaisesRegex(SchemaNonexistent, err_msg):
            spec_loader.get_schema_for_doc(fake_name, path_only=True)

    def test_prevent_non_spec_dir_access(self):
        """
        Ensure that matching files in directories outside the designated spec repo cannot be retrieved
        """

        # this query is OK as the file is still in the spec repo
        path_in_spec_repo = '../../../../../**/fetch_test_vertex'
        result = spec_loader.get_schema('stored_queries', path_in_spec_repo, path_only=True)
        self.assertEqual(
            result,
            os_path.join(self.test_spec_dir, 'stored_queries', 'test', 'fetch_test_vertex.yaml')
        )

        # this matches a file in one of the other test data dirs => should throw an error
        path_outside_spec_repo = '../../../../data/collections/test_node'
        err_msg = f"Stored query '{path_outside_spec_repo}' does not exist"
        with self.assertRaisesRegex(SchemaNonexistent, err_msg):
            spec_loader.get_schema('stored_queries', path_outside_spec_repo, path_only=True)
