"""
Block until all dependent services come online.
"""
import requests
import time
import os
import sys
import cursor
from test.integration.utils.clock import Clock

TIMEOUT = 60
POLL_INTERVAL = 0.5

RE_API_URL = os.environ.get('RE_API_URL')
if RE_API_URL is None:
    print('the "RE_API_URL" environment variable is required')
    sys.exit(1)


def wait_for_re_api() -> None:
    """wait for a service or list of services to start up"""
    TIMEOUT
    POLL_INTERVAL
    print(f'Waiting for RE_API to be available at {RE_API_URL}...', end='')
    timeout = int(time.time()) + TIMEOUT
    clock = Clock()
    while True:
        print(clock.tick(), end='\b')
        try:
            resp = requests.get(RE_API_URL)
            resp.raise_for_status()
            break
        except Exception as err:
            if int(time.time()) > timeout:
                raise RuntimeError(
                    f"Timed out waiting for RE_API to start at {RE_API_URL} with "
                    f"error: {err}"
                )
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        cursor.hide()
        wait_for_re_api()
    finally:
        cursor.show()
