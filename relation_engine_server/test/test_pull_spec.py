import unittest
from unittest import mock
import re

from relation_engine_server.utils.pull_spec import download_specs
from relation_engine_server.utils.wait_for import wait_for_api
from spec.test.test_ensure_specs import ensure_borked_indexes


class Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wait_for_api()

    def test_download_specs(self):
        download_specs(init_collections=True, reset=True)

    @mock.patch(
        "relation_engine_server.utils.ensure_specs.ensure_indexes",
        ensure_borked_indexes,
    )
    def test_download_specs__fail(self):
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
