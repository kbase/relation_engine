"""
Authorization and authentication utilities.
"""
import os
import flask
import requests

from .exceptions import MissingHeader, UnauthorizedAccess


def require_auth_token(roles=[]):
    """
    Function that validates an authentication token in a flask request context.

    If any roles are provided, the token holder must have *at least one* of the roles.

    Raises some exception if any auth requirement is not met.
    """
    kbase_endpoint = os.environ.get('KBASE_ENDPOINT', 'https://ci.kbase.us/services')
    kbase_auth_url = kbase_endpoint + '/auth'
    if not flask.request.headers.get('Authorization'):
        # No authorization token was provided in the headers
        raise MissingHeader('Authorization')
    token = flask.request.headers.get('Authorization').replace('Bearer', '').strip()
    # Make an authorization request to the kbase auth2 server
    headers = {'Authorization': token}
    url = kbase_auth_url + '/api/V2/me'
    print(url)
    auth_resp = requests.get(url, headers=headers)
    if not auth_resp.ok:
        print('-' * 80)
        print(auth_resp.text)
        raise UnauthorizedAccess(kbase_auth_url)
    auth_json = auth_resp.json()
    if len(roles):
        check_roles(required=roles, given=auth_json['customroles'], auth_url=kbase_auth_url)


def check_roles(required, given, auth_url):
    for role in required:
        if role in given:
            return
    raise UnauthorizedAccess(auth_url)
