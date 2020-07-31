"""
Block until the api starts up
"""
import requests
import time


def main():
    timeout = int(time.time()) + 60
    while True:
        try:
            requests.get('http://localhost:5000').raise_for_status()
            break
        except Exception:
            print('Waiting for app to start..')
            if int(time.time()) > timeout:
                raise RuntimeError('Timed out waiting for services.')
            time.sleep(3)
    print('Services started!')


if __name__ == '__main__':
    main()
