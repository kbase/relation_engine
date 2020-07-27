"""
Tests for workspace workspace stored queries under the ws* namespace
"""
import unittest
import json
import requests
from test.stored_queries.helpers import create_test_docs

from test.helpers import get_config

_CONF = get_config()


def _ws_obj(wsid, objid, ver, is_public=True):
    """Create data for a dummy test workspace obj"""
    return {
        '_key': ':'.join((str(n) for n in (wsid, objid, ver))),
        'name': 'obj',
        'workspace_id': wsid,
        'object_id': objid,
        'version': ver,
        'hash': 'x',
        'size': 0,
        'epoch': 0,
        'deleted': False,
        'is_public': is_public,
    }


class TestWs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Create all test data.
        """
        ws_object_version = [
            _ws_obj(1, 1, 1),  # root/origin object
            _ws_obj(1, 2, 1),  # copy object
            _ws_obj(1, 3, 1),  # provenance object
            _ws_obj(1, 4, 1),  # reference object
            _ws_obj(1, 5, 1, is_public=False),  # private copy obj
            _ws_obj(1, 6, 1, is_public=False),  # private prov obj
            _ws_obj(1, 7, 1, is_public=False),  # private ref obj
        ]
        create_test_docs('ws_object_version', ws_object_version)
        ws_type_version = [{'_key': 'Module.Type1-1.0'}]
        create_test_docs('ws_type_version', ws_type_version)
        ws_obj_instance_of_type = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_type_version/Module.Type1-1.0'},
            {'_from': 'ws_object_version/1:2:1', '_to': 'ws_type_version/Module.Type1-1.0'},
            {'_from': 'ws_object_version/1:3:1', '_to': 'ws_type_version/Module.Type1-1.0'},
            {'_from': 'ws_object_version/1:4:1', '_to': 'ws_type_version/Module.Type1-1.0'},
        ]
        create_test_docs('ws_obj_instance_of_type', ws_obj_instance_of_type)
        ws_prov_descendant_of = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:3:1'},
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:6:1'},
        ]
        create_test_docs('ws_prov_descendant_of', ws_prov_descendant_of)
        ws_refers_to = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:4:1'},
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:7:1'},
        ]
        create_test_docs('ws_refers_to', ws_refers_to)
        ws_copied_from = [
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:2:1'},
            {'_from': 'ws_object_version/1:1:1', '_to': 'ws_object_version/1:5:1'},
        ]
        create_test_docs('ws_copied_from', ws_copied_from)

    def test_fetch_related_data_valid(self):
        """
        Test for the basic happy path.
        This also covers the case of private-scope object results, which will be hidden from results.
        """
        resp = requests.post(
            _CONF['re_api_url'] + '/api/v1/query_results',
            params={'stored_query': 'ws_fetch_related_data', 'show_public': True},
            data=json.dumps({'obj_key': '1:1:1'})
        ).json()
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['has_more'], False)
        res = resp['results'][0]
        # Check the root object results
        self.assertEqual(res['obj']['_key'], '1:1:1')
        self.assertEqual(res['obj_type']['_key'], 'Module.Type1-1.0')
        # Check the copy results
        self.assertEqual(res['copies']['count'], 1)
        self.assertEqual(len(res['copies']['data']), 1)
        self.assertEqual(res['copies']['data'][0]['data']['_id'], 'ws_object_version/1:2:1')
        self.assertEqual(res['copies']['data'][0]['hops'], 1)
        self.assertEqual(res['copies']['data'][0]['type']['_id'], 'ws_type_version/Module.Type1-1.0')
        # Check the provenance results
        self.assertEqual(res['prov']['count'], 1)
        self.assertEqual(len(res['prov']['data']), 1)
        self.assertEqual(res['prov']['data'][0]['data']['_id'], 'ws_object_version/1:3:1')
        self.assertEqual(res['prov']['data'][0]['hops'], 1)
        self.assertEqual(res['prov']['data'][0]['type']['_id'], 'ws_type_version/Module.Type1-1.0')
        # Check the ref results
        self.assertEqual(res['refs']['count'], 1)
        self.assertEqual(len(res['refs']['data']), 1)
        self.assertEqual(res['refs']['data'][0]['data']['_id'], 'ws_object_version/1:4:1')
        self.assertEqual(res['refs']['data'][0]['hops'], 1)
        self.assertEqual(res['refs']['data'][0]['type']['_id'], 'ws_type_version/Module.Type1-1.0')
