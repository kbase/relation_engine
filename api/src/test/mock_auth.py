import os
import responses
from contextlib import contextmanager

kbase_endpoint = os.environ.get('KBASE_ENDPOINT', 'https://ci.kbase.us/services')
auth_url = kbase_endpoint + '/auth/api/V2/me'

# Some test auth tokens
tokens = {
    'admin': 're_admin',
    'non_admin': 'standard_dev'
}

valid_non_admin_response = {
    'created': 1528306100471,
    'lastlogin': 1542068355002,
    'display': 'Test User',
    'roles': [],
    'customroles': [],
    'policyids': [],
    'user': 'username',
    'local': False,
    'email': 'user@example.com',
    'idents': []
}

valid_re_admin_response = {
    'created': 1528306100471,
    'lastlogin': 1542068355002,
    'display': 'Test User',
    'roles': [],
    'customroles': ['RE_ADMIN'],
    'policyids': [],
    'user': 'username',
    'local': False,
    'email': 'user@example.com',
    'idents': []
}

web_url = os.environ.get('TEST_URL', 'http://web:5000')
responses.add_passthru(web_url)


@contextmanager
def mock_auth(*args, **kwargs):
    with responses.RequestsMock() as resps:
        # Mock an admin authorization
        resps.add(responses.Response(
            method='GET',
            url=auth_url,
            headers={'Authorization': tokens['admin']},
            json=valid_re_admin_response
        ))
        # Mock a non-admin user auth
        resps.add(responses.Response(
            method='GET',
            url=auth_url,
            headers={'Authorization': tokens['non_admin']},
            json=valid_non_admin_response
        ))
        yield resps
