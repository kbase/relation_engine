"""
Block until all dependent services come online.
"""
import requests
import time
import sys
from relation_engine_server.utils.config import get_config

_CONF = get_config()


def wait_for_service(service_list):
    '''wait for a service or list of services to start up'''
    timeout = int(time.time()) + 60

    service_conf_list = [get_service_conf(s) for s in service_list]

    while True:
        try:
            for service in service_conf_list:
                name = service['name']
                url = service['url']
                if service['auth'] is not None:
                    resp = requests.get(service['url'], auth=service['auth']).raise_for_status()
                    if service.get('callback') is not None:
                        service['callback'](resp)
                else:
                    # auth and workspace both return 500, so don't raise_for_status
                    requests.get(service['url'])
            break
        except Exception:
            print(f"Waiting for {name} to start...")
            if int(time.time()) > timeout:
                raise RuntimeError(f"Timed out waiting for {name}, {url}")
            time.sleep(3)
    print(f"{name} started!")


def get_service_conf(service_name):

    service_conf = {
        'arangodb': {
            'url': _CONF['api_url'] + '/database/current',
            'callback': _assert_content,
        },
        'auth': {
            'url': _CONF['auth_url'],
        },
        'workspace': {
            'url': _CONF['workspace_url'],
        },
        'localhost': {
            'url': 'http://127.0.0.1:5000',
        }
    }

    if service_name not in service_conf:
        raise KeyError(f'Configuration for {service_name} not found')

    return {
        'name': service_name,
        # auth defaults to None if there is nothing set
        'auth': service_conf[service_name].get('auth'),
        'url': service_conf[service_name]['url'],
    }


def wait_for_arangodb():
    '''wait for arangodb to be ready'''
    wait_for_service(['arangodb'])


def wait_for_services():
    '''wait for the workspace, auth, and arango to start up'''

    wait_for_service(['auth', 'workspace', 'arangodb'])


def wait_for_api():
    '''wait for the workspace, auth, arango, AND localhost:5000 to start up'''

    wait_for_services()
    wait_for_service(['localhost'])


def _assert_content(resp):
    """Assert that a response body is non-empty"""
    if len(resp.content) == 0:
        raise RuntimeError("No content in response")


if __name__ == '__main__':
    if sys.argv[1] == 'services':
        wait_for_services()
    elif sys.argv[1] == 'api':
        wait_for_api()
