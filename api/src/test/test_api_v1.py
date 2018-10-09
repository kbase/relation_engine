"""
Simple integration tests on the API itself.

We make actual ajax requests to the running docker container.
"""
import unittest
import requests

url = 'http://web:5000/v1'


class TestApiV1(unittest.TestCase):

    def test_root(self):
        """Test root path for api."""
        resp = requests.get(url)
        json = resp.json()
        self.assertTrue(json['test'])
