import unittest
from unittest import mock
import copy

from relation_engine_server.utils import arango_client
from relation_engine_server.utils.ensure_specs import (
    ensure_indexes,
    ensure_views,
    ensure_analyzers,
    ensure_all,
    mod_obj_literal,
    round_float,
    excise_namespace,
    get_names,
)
from spec.test.helpers import (
    check_spec_test_env,
)


def ensure_borked_indexes():
    """Get all the test server indexes, but with 1st one borked"""
    coll_name_2_indexes_server = arango_client.get_all_indexes()
    borked_coll_name = list(coll_name_2_indexes_server.keys())[0]
    borked_index = coll_name_2_indexes_server[borked_coll_name][0]
    borked_index["type"] = "fake_type"
    borked_name = f"{borked_coll_name}/{borked_index['type']}/{borked_index['fields']}"
    return ([borked_name], {borked_coll_name: [borked_index]})


def ensure_borked_views():
    """Get all the test server views, but with 1st one borked"""
    all_views_server = arango_client.get_all_views()
    borked_view = all_views_server[0]
    borked_view["type"] = "fake_type"
    borked_name = f"{borked_view['name']}/{borked_view['type']}"
    return ([borked_name], [borked_view])


def ensure_borked_analyzers():
    """Get all the test server analyzers, but with 1st one borked"""
    all_analyzers_server = arango_client.get_all_analyzers()
    borked_analyzer = all_analyzers_server[0]
    borked_analyzer["type"] = "fake_type"
    borked_name = f"{borked_analyzer['name']}/{borked_analyzer['type']}"
    return ([borked_name], [borked_analyzer])


class TestEnsureSpecs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        check_spec_test_env()

    def test_ensure_indexes(self):
        failed_names, failed_specs = ensure_indexes()
        self.assertFalse(len(failed_names))
        self.assertFalse(len(failed_specs))

    def test_ensure_views(self):
        failed_names, failed_specs = ensure_views()
        self.assertFalse(len(failed_names))
        self.assertFalse(len(failed_specs))

    def test_ensure_analyzers(self):
        failed_names, failed_specs = ensure_analyzers()
        self.assertFalse(len(failed_names))
        self.assertFalse(len(failed_specs))

    def test_ensure_all(self):
        failed_names = ensure_all()
        self.assertEqual(
            failed_names,
            {
                "indexes": [],
                "views": [],
                "analyzers": [],
            },
        )

    @mock.patch(
        "relation_engine_server.utils.ensure_specs.ensure_indexes",
        ensure_borked_indexes,
    )
    @mock.patch(
        "relation_engine_server.utils.ensure_specs.ensure_views", ensure_borked_views
    )
    @mock.patch(
        "relation_engine_server.utils.ensure_specs.ensure_analyzers",
        ensure_borked_analyzers,
    )
    def test_ensure_all__fail(self):
        """Mock server spec fetches so that 1st spec of each type is borked"""
        borked_index_names, _ = ensure_borked_indexes()
        borked_view_names, _ = ensure_borked_views()
        borked_analyzer_names, _ = ensure_borked_analyzers()
        failed_names = ensure_all()

        self.assertEqual(
            {
                "indexes": borked_index_names,
                "views": borked_view_names,
                "analyzers": borked_analyzer_names,
            },
            failed_names,
        )

    # ------------------
    # --- Unit tests ---
    # ------------------

    def _copy_mod_obj_literal(self, obj, literal_type, func):
        obj = copy.deepcopy(obj)
        mod_obj_literal(obj, literal_type, func)
        return obj

    def test_mod_obj_literal__round_float(self):
        """Test recursively finding floats in obj to correct round off error"""
        obj = {
            "english": {
                "hello": "hello",
                "one": 1.00000,
            },
            "spanish": {
                "hello": "hola",
                "one": 1.0000000089,
                "_castilian": {
                    "hello": "hola",
                    "one": 1,
                },
            },
            "japanese": {
                "hello": "konichiwa",
                "one": 0.999999999999,
            },
        }

        exp = {
            "english": {
                "hello": "hello",
                "one": 1.0,
            },
            "spanish": {
                "hello": "hola",
                "one": 1.0,
                "_castilian": {
                    "hello": "hola",
                    "one": 1,
                },
            },
            "japanese": {
                "hello": "konichiwa",
                "one": 1.0,
            },
        }

        self.assertEqual(exp, self._copy_mod_obj_literal(obj, float, round_float))

    def test_mod_obj_literal__excise_namespace(self):
        """Test recursively find namespace::name strings in obj to excise namespace prefix"""
        obj = {
            "english": {
                "hello": "hello",
                "thing": "thing",
            },
            "spanish": {
                "hello": "hola",
                "thing": "spanish::cosa",
                "_castilian": {
                    "hello": "hola",
                    "thing": "spanish_castilian::cosa",
                },
            },
            "japanese": {
                "hello": "konichiwa",
                "thing": "japanese::mono",
            },
        }

        exp = {
            "english": {
                "hello": "hello",
                "thing": "thing",
            },
            "spanish": {
                "hello": "hola",
                "thing": "cosa",
                "_castilian": {
                    "hello": "hola",
                    "thing": "cosa",
                },
            },
            "japanese": {
                "hello": "konichiwa",
                "thing": "mono",
            },
        }

        self.assertEqual(exp, self._copy_mod_obj_literal(obj, str, excise_namespace))

    def test_get_view_analyzer_names(self):
        """Test getting names of list of analyzer/view properties"""
        views_analyzers = [
            {"name": "thing0", "type": "type0"},
            {"name": "thing1", "type": "type1"},
        ]

        self.assertEqual(
            get_names(views_analyzers, "views"), ["thing0/type0", "thing1/type1"]
        )

    def test_get_coll_names(self):
        """Test getting names of dict of list of index properties"""
        coll_names_2_indexes = {
            "coll0": [
                {"type": "type00", "fields": ["fields000", "fields001"]},
                {"type": "type01", "fields": ["fields010"]},
            ],
            "coll1": [{"type": "type10", "fields": ["fields100"]}],
        }

        self.assertEqual(
            get_names(coll_names_2_indexes, "indexes"),
            [
                "coll0/type00/['fields000', 'fields001']",
                "coll0/type01/['fields010']",
                "coll1/type10/['fields100']",
            ],
        )
