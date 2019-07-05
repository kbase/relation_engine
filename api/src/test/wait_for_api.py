"""
Block until the api starts up
"""
import requests
import time


def main():
    started = False
    timeout = int(time.time()) + 60
    while not started:
        try:
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
