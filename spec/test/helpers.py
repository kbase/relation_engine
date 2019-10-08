"""
Test helpers
"""
import sys
import os
import time
import requests
import functools


@functools.lru_cache(maxsize=1)
def get_config():
    """Return configuration data for tests."""
    return {
        're_api_url': os.environ['RE_API_URL'],
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
            print('Waiting for arangodb to come online')
            if time.time() > timeout:
                sys.stderr.write(str(err) + '\n')
                raise RuntimeError('Timed out waiting for arangodb')
            time.sleep(3)


def wait_for_api():
    wait_for_arangodb()
    # Wait for other dependent services to come online
    conf = get_config()
    timeout = int(time.time()) + 60
    auth_url = 'http://auth:5000'
    ws_url = 'http://workspace:5000'
    while True:
        try:
            # Reassign the `url` variable so we can print which service errored
            url = conf['re_api_url']
            requests.get(url).raise_for_status()
            url = auth_url
            requests.get(url)
            url = ws_url
            requests.get(url)
            break
        except Exception as err:
            print(f"Waiting for dependent service to come online: {url}")
            if int(time.time()) > timeout:
                sys.stderr.write(str(err) + "\n")
                raise RuntimeError(f"Timed out waiting for {url}")
            time.sleep(2)


def assert_subset(testCls, subset, _dict):
    """Replacement for the deprecated `assertDictContainsSubset` method."""
    for (key, val) in subset.items():
        testCls.assertEqual(subset.get(key), _dict.get(key))


if __name__ == '__main__':
    if sys.argv[1] == 'wait_for_api':
        wait_for_api()
