"""The main entrypoint for running the Flask server."""
import flask
import json
import os
from uuid import uuid4
import traceback
from jsonschema.exceptions import ValidationError

from .api_versions.api_v1 import api_v1
from .exceptions import MissingHeader, UnauthorizedAccess, InvalidParameters
from .utils import arango_client, spec_loader

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`
app.register_blueprint(api_v1, url_prefix='/api/v1')


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
    return flask.jsonify(body)


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
    return (flask.jsonify(resp), 400)


@app.errorhandler(arango_client.ArangoServerError)
def arango_server_error(err):
    resp = {
        'error': str(err),
        'arango_message': err.resp_json['errorMessage']
    }
    return (flask.jsonify(resp), 400)


@app.errorhandler(InvalidParameters)
def invalid_params(err):
    """Invalid request body json params."""
    resp = {'error': str(err)}
    return (flask.jsonify(resp), 400)


@app.errorhandler(spec_loader.SchemaNonexistent)
@app.errorhandler(spec_loader.StoredQueryNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    resp = {'error': str(err), 'name': err.name}
    return (flask.jsonify(resp), 400)


@app.errorhandler(ValidationError)
def validation_error(err):
    """Json Schema validation error."""
    # Refer to the documentation on jsonschema.exceptions.ValidationError:
    # https://python-jsonschema.readthedocs.io/en/stable/errors/
    resp = {
        'error': err.message,
        'failed_validator': err.validator,
        'validator_value': err.validator_value,
        'path': list(err.absolute_path),
        'schema_path': list(err.schema_path)
    }
    return (flask.jsonify(resp), 400)


@app.errorhandler(UnauthorizedAccess)
def unauthorized_access(err):
    resp = {
        'error': '403 - Unauthorized',
        'auth_url': err.auth_url,
        'auth_response': err.response
    }
    return (flask.jsonify(resp), 403)


@app.errorhandler(404)
def page_not_found(err):
    return (flask.jsonify({'error': '404 - Not found.'}), 404)


@app.errorhandler(405)
def method_not_allowed(err):
    return (flask.jsonify({'error': '405 - Method not allowed.'}), 405)


@app.errorhandler(MissingHeader)
def generic_400(err):
    return (flask.jsonify({'error': str(err)}), 400)


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
    resp['error_class'] = err.__class__.__name__
    resp['error_details'] = str(err)
    return (flask.jsonify(resp), 500)


@app.after_request
def after_request(resp):
    # Log request
    print(' '.join([flask.request.method, flask.request.path, '->', resp.status]))
    # Enable CORS
    resp.headers['Access-Control-Allow-Origin'] = '*'
    env_allowed_headers = os.environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', 'Authorization, Content-Type')
    resp.headers['Access-Control-Allow-Headers'] = env_allowed_headers
    # Set JSON content type and response length
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Content-Length'] = resp.calculate_content_length()
    return resp
