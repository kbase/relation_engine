"""
Test helpers
"""
import contextlib
import functools
import io
import json
import os
import requests
import sys


@functools.lru_cache(maxsize=1)
def get_config():
    """Return configuration data for tests."""
    return {
        're_api_url': os.environ['RE_API_URL'],
        're_query_results_url': os.environ['RE_API_URL'] + '/api/v1/query_results',
        'db_url': os.environ['DB_URL'],
        'db_auth': (os.environ['DB_USER'], os.environ.get('DB_PASS', ''))
    }


def run_query(query_name, query_data={}):
    """submit a database query"""

    query_results_url = get_config()['re_query_results_url']

    return requests.post(
        query_results_url,
        params={'stored_query': query_name},
        data=json.dumps(query_data)
    ).json()


def assert_subset(testCls, subset, _dict):
    """Replacement for the deprecated `assertDictContainsSubset` method."""
    for (key, val) in subset.items():
        testCls.assertEqual(subset.get(key), _dict.get(key))


def create_test_docs(coll_name, docs, update_on_dupe=False):
    """Create a set of documents for use in tests."""
    body = '\n'.join([json.dumps(d) for d in docs])
    params = {'overwrite': True, 'collection': coll_name, 'display_errors': '1'}

    if update_on_dupe:
        del params['overwrite']
        params['on_duplicate'] = 'update'

    conf = get_config()

    resp = requests.put(
        conf['re_api_url'] + '/api/v1/documents',
        params=params,
        data=body,
        headers={'Authorization': 'admin_token'}
    )
    if not resp.ok:
        raise RuntimeError(resp.text)

    return resp


def capture_stdout(function, *args, **kwargs):
    """capture and return the standard output from a function"""
    io_stdout = io.StringIO()
    sys.stdout = io_stdout
    function(*args, **kwargs)
    sys.stdout = sys.__stdout__
    return io_stdout.getvalue()


@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]
