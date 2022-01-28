import unittest
from unittest import mock
import re

from relation_engine_server.utils.pull_spec import download_specs
from relation_engine_server.utils.wait_for import wait_for_api
from relation_engine_server.utils.config import get_config
from spec.test.test_ensure_specs import ensure_borked_indexes

_CONF = get_config()


class TestPullSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wait_for_api()

    def test_download_specs__success(self):
        """Test ensure specs in `download_specs` for success case"""
        update_name = download_specs(init_collections=True, reset=True)
        self.assertEqual(_CONF["spec_release_path"], update_name)

    @mock.patch(
        "relation_engine_server.utils.ensure_specs.ensure_indexes",
        ensure_borked_indexes,
    )
    def test_download_specs__fail(self):
        """Test ensure specs in `download_specs` for fail case"""
        with self.assertRaisesRegex(
            RuntimeError,
            re.escape(
                """Some local specs have no matching server specs:
{
    "indexes": [
        "%s"
    ],
    "views": [],
    "analyzers": []
}"""
                % ensure_borked_indexes()[0][0]
            ),
        ):
            download_specs(init_collections=True, reset=True)
