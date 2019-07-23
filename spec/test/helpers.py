"""
Test helpers
"""
import os
import time
import requests
import functools


@functools.lru_cache(maxsize=1)
def get_config():
    """Return configuration data for tests."""
    return {
        'db_url': os.environ['DB_URL'],
        'db_auth': (os.environ['DB_USER'], os.environ.get('DB_PASS', ''))
    }


def wait_for_arangodb():
    """Wait for arangodb to go live."""
    conf = get_config()
    db_url = conf['db_url']
    auth = ('root', '')
    timeout = time.time() + 60
    while True:
        try:
            resp = requests.get(db_url + '/_admin/cluster/health', auth=auth)
            resp.raise_for_status()
            break
        except Exception as err:
            print(err)
            if time.time() > timeout:
                raise RuntimeError('Timed out waiting for arangodb')
            time.sleep(3)
