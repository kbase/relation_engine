import requests
import json
from test.helpers import get_config

_CONF = get_config()

def create_test_docs(coll_name, docs, update_on_dupe=False):
    """Create a set of documents for use in tests."""
    body = '\n'.join([json.dumps(d) for d in docs])
    params = {'overwrite': True, 'collection': coll_name, 'display_errors': '1'}

    if update_on_dupe:
        del params['overwrite']
        params['on_duplicate'] = 'update'

    resp = requests.put(
        _CONF['re_api_url'] + '/api/v1/documents',
        params=params,
        data=body,
        headers={'Authorization': 'admin_token'}
    )
    if not resp.ok:
        raise RuntimeError(resp.text)

    return resp
