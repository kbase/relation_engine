"""
Tests for the DJORNL Parser

At the present time, this just ensures that the files are parsed correctly;
it does not check data loading into the db.
"""
import unittest
import os

from importers.djornl.parser import DJORNL_Parser
from spec.test.helpers import modified_environ, check_spec_test_env

_TEST_DIR = "/app/spec/test"


class Test_DJORNL_Parser_Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_spec_test_env()

    def test_the_full_shebang(self):

        with modified_environ(
            RES_ROOT_DATA_PATH=os.path.join(_TEST_DIR, "djornl", "test_data")
        ):
            parser = DJORNL_Parser()
            parser.load_data()
            self.assertTrue(bool(parser.load_data()))
