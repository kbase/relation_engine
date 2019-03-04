import requests

_API_URL = 'http://re_api:5000/api'


if __name__ == '__main__':
    resp = requests.get(
        _API_URL + '/update_specs',
        headers={'Authorization': 'admin_token'},
        params={'init_collections': '1'}
    )
    print(resp)
