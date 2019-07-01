"""
Block until all dependency services (arango, workspace, auth) to come online.
"""
import requests
import time

from .utils.config import get_config

_CONFIG = get_config()


def main():
    started = False
    timeout = int(time.time()) + 60
    while not started:
        try:
            requests.get(_CONFIG['workspace_url'])
            requests.get(_CONFIG['auth_url'])
            auth = (_CONFIG['db_user'], _CONFIG['db_pass'])
            requests.get(_CONFIG['db_url'] + '/_admin/cluster/health', auth=auth).raise_for_status()
            requests.get('http://localhost:5000').raise_for_status()
            started = True
        except Exception as err:
            print('Waiting for services:', err)
            if int(time.time()) > timeout:
                raise RuntimeError('Timed out waiting for services.')
            time.sleep(3)
    print('Services started!')


if __name__ == '__main__':
    main()
