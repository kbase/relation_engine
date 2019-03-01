"""The main entrypoint for running the Flask server."""
import re
import flask
import json
import os
from uuid import uuid4
import traceback
from jsonschema.exceptions import ValidationError

from .exceptions import MissingHeader, UnauthorizedAccess, InvalidParameters
from .utils import arango_client, spec_loader
from .api_modules import api_v1

# All api version modules, from oldest to newest
_API_VERSIONS = [api_v1.endpoints]
_API_DEPRECATIONS = [api_v1.deprecations]

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`


@app.route('/', methods=['GET'])
def root():
    """Server status."""
    if os.path.exists('.git/refs/heads/master'):
        with open('.git/refs/heads/master', 'r') as fd:
            commit_hash = fd.read().strip()
    else:
        commit_hash = 'unknown'
    arangodb_status = arango_client.server_status()
    repo_url = 'https://github.com/kbase/relation_engine_api.git'
    body = {
        'arangodb_status': arangodb_status,
        'commit_hash': commit_hash,
        'repo_url': repo_url
    }
    return _json_resp(body)


@app.route('/api/<path:path>', methods=['GET', 'PUT', 'POST', 'DELETE'])
def api_call(path):
    """
    Handle an api request, dispatching it to the appropriate versioned module.

    Versioning system:
    - Every API version is a discrete python module that contains an 'endpoints' dictionary.
    - New versions don't need to redefine previous endpoints.
        - If an endpoint is not defined, we fall back to a previous version.
    - New versions can overwrite existing methods and add new ones.
    - Versions are simple incrementing integers. We only need a new version for breaking changes.
    - New modules can deprecate paths by putting them under the 'deprecations' key
    Note that endpoints cannot be removed with new versions, only overwritten or added.
    """
    path_parts = path.split('/')
    version_int = _get_version(path_parts[0])
    # Get the path and version number
    api_path = '/'.join(path_parts[1:])
    # Flag for whether the endpoint we find is deprecated
    deprecated = False
    # Find our method in the various versioned modules
    # If it is not present in a later version, fall back to a previous version
    # Iterates by starting at (version-1), stopping at 0, and stepping backwards
    # Note: the mypy type checker has difficulties with the path_funcs dicts, so we ignore type checking below
    for ver in range(version_int - 1, -1, -1):
        path_funcs = _API_VERSIONS[ver]
        deprecations = _API_DEPRECATIONS[ver]
        if api_path in deprecations:
            # We found a deprecation flag on the endpoint
            deprecated = True
        if api_path in path_funcs:
            methods = path_funcs[api_path].get('methods', {'GET'})  # type: ignore
            # Mypy is not able to infer that `methods` will always be a set
            if flask.request.method not in methods:  # type: ignore
                return (flask.jsonify({'error': '405 - Method not allowed.'}), 405)
            # We found a matching function for the endpoint and method
            func = path_funcs[api_path]['handler']  # type: ignore
            # Mypy is not able to infer that this is a function
            result = func()  # type: ignore
            return _json_resp(result, 200, deprecated)
    body = {'error': f'path not found: {api_path}'}
    return _json_resp(body, 404)


def _get_version(version_str):
    """From a list of path parts, initialize and validate a version int for the api."""
    ver_len = len(_API_VERSIONS)
    # Make sure the version looks like 'v12'
    if not re.match(r'^v\d+$', version_str):
        raise InvalidParameters('Make a request with the format /api/<version>/<path...>')
    # Parse to an int
    version_int = int(version_str.replace('v', ''))
    # Make sure the version number is valid
    if version_int <= 0:
        raise InvalidParameters('API version must be > 0')
    if version_int > ver_len:
        raise InvalidParameters(f'Invalid api version; max is {ver_len}')
    return version_int


def _json_resp(result, status=200, deprecated=False):
    """Send a json response back to the requester with the proper headers."""
    resp = flask.Response(json.dumps(result))
    resp.status_code = status
    if deprecated:
        # Add a deprecation warning in the headers
        resp.headers['Warning'] = 'DEPRECATED'
    print(' '.join([flask.request.method, flask.request.path, '->', resp.status]))
    # Enable CORS
    resp.headers['Access-Control-Allow-Origin'] = '*'
    env_allowed_headers = os.environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', 'authorization')
    resp.headers['Access-Control-Allow-Headers'] = env_allowed_headers
    # Set JSON content type and response length
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Content-Length'] = resp.calculate_content_length()
    return resp


@app.errorhandler(json.decoder.JSONDecodeError)
def json_decode_error(err):
    """A problem parsing json."""
    resp = {
        'error': 'Unable to parse JSON',
        'source_json': err.doc,
        'pos': err.pos,
        'lineno': err.lineno,
        'colno': err.colno
    }
    return _json_resp(resp, 400)


@app.errorhandler(arango_client.ArangoServerError)
def arango_server_error(err):
    resp = {
        'error': str(err),
        'arango_message': err.resp_json['errorMessage']
    }
    return _json_resp(resp, 400)


@app.errorhandler(InvalidParameters)
def invalid_params(err):
    """Invalid request body json params."""
    resp = {'error': str(err)}
    return _json_resp(resp, 400)


@app.errorhandler(spec_loader.SchemaNonexistent)
@app.errorhandler(spec_loader.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    resp = {'error': str(err), 'name': err.name}
    return _json_resp(resp, 400)


@app.errorhandler(ValidationError)
def validation_error(err):
    """Json Schema validation error."""
    resp = {
        'error': str(err).split('\n')[0],
        'instance': err.instance,
        'validator': err.validator,
        'validator_value': err.validator_value,
        'schema': err.schema
    }
    return _json_resp(resp, 400)


@app.errorhandler(UnauthorizedAccess)
def unauthorized_access(err):
    resp = {
        'error': '403 - Unauthorized',
        'auth_url': err.auth_url,
        'auth_response': err.response
    }
    return _json_resp(resp, 403)


@app.errorhandler(404)
def page_not_found(err):
    return _json_resp({'error': '404 - Not found.'}, 404)


@app.errorhandler(405)
def method_not_allowed(err):
    return _json_resp({'error': '405 - Method not allowed.'}, 405)


@app.errorhandler(MissingHeader)
def generic_400(err):
    return _json_resp({'error': str(err)}, 400)


# Any other unhandled exceptions -> 500
@app.errorhandler(Exception)
@app.errorhandler(500)
def server_error(err):
    print('=' * 80)
    print('500 Unexpected Server Error')
    print('-' * 80)
    traceback.print_exc()
    print('=' * 80)
    resp = {'error': '500 - Unexpected server error'}
    # if os.environ.get('FLASK_DEBUG'):  TODO
    resp['error_class'] = err.__class__.__name__
    resp['error_details'] = str(err)
    return _json_resp(resp, 500)
