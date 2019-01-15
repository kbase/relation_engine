"""
Authorization and authentication utilities.
"""
import os
import json
import flask
import requests

from .exceptions import MissingHeader, UnauthorizedAccess

_WS_URL = os.environ.get('KBASE_WORKSPACE_URL', 'https://ci.kbase.us/services/ws')


def require_auth_token(roles=[]):
    """
    Function that validates an authentication token in a flask request context.

    If any roles are provided, the token holder must have *at least one* of the roles.

    Raises some exception if any auth requirement is not met.
    """
    kbase_endpoint = os.environ.get('KBASE_ENDPOINT', 'https://ci.kbase.us/services')
    kbase_auth_url = os.environ.get('KBASE_AUTH_URL', kbase_endpoint + '/auth')
    if not flask.request.headers.get('Authorization'):
        # No authorization token was provided in the headers
        raise MissingHeader('Authorization')
    token = get_auth_header()
    # Make an authorization request to the kbase auth2 server
    headers = {'Authorization': token}
    url = kbase_auth_url + '/api/V2/me'
    auth_resp = requests.get(url, headers=headers)
    if not auth_resp.ok:
        print('-' * 80)
        print(auth_resp.text)
        raise UnauthorizedAccess(kbase_auth_url, auth_resp.text)
    auth_json = auth_resp.json()
    if len(roles):
        check_roles(required=roles, given=auth_json['customroles'], auth_url=kbase_auth_url)


def check_roles(required, given, auth_url):
    for role in required:
        if role in given:
            return
    raise UnauthorizedAccess(auth_url, 'Missing role')


def get_auth_header():
    return flask.request.headers.get('Authorization', '').replace('Bearer', '').strip()


def get_workspace_ids(auth_token):
    """Get a list of workspace IDs that the given username is allowed to access in the workspace."""
    ws_url = _WS_URL + '/api/V2'
    # Make an admin request to the workspace (command is 'listWorkspaceIds')
    payload = {
        'method': 'Workspace.list_workspace_ids',
        'params': [{'perm': 'r'}],
        'version': '1.1'
    }
    headers = {'Authorization': auth_token}
    resp = requests.post(
        ws_url,
        data=json.dumps(payload),
        headers=headers
    )
    if not resp.ok:
        raise UnauthorizedAccess(ws_url, resp.text)
    return resp.json()['result'][0]['workspaces']
