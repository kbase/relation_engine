import requests
import json
from test.helpers import get_config

_CONF = get_config()


def create_test_docs(coll_name, docs):
    """Create a set of documents for use in tests."""
    body = '\n'.join([json.dumps(d) for d in docs])
    resp = requests.put(
        _CONF['re_api_url'] + '/api/v1/documents',
        params={'overwrite': True, 'collection': coll_name, 'display_errors': '1'},
        data=body,
        headers={'Authorization': 'admin_token'}
    )
    if not resp.ok:
        raise RuntimeError(resp.text)
