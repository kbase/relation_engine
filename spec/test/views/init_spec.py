import requests

_API_URL = 'http://re_api:5000/api/v1'


if __name__ == '__main__':
    resp = requests.put(
        _API_URL + '/specs',
        headers={'Authorization': 'admin_token'},
        params={'init_collections': '1'}
    )
    print(resp.text)
