"""The main entrypoint for running the Flask server."""
import flask
import os
from uuid import uuid4
import traceback

from .api import api
from .exceptions import MissingHeader, UnauthorizedAccess
from . import arango_client

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`

app.register_blueprint(api, url_prefix='/api')


@app.route('/', methods=['GET'])
def root():
    """Server status."""
    with open('.git/refs/heads/master', 'r') as fd:
        commit_hash = fd.read().strip()
    arangodb_status = arango_client.server_status()
    repo_url = 'https://github.com/kbase/relation_engine_api.git'
    return flask.jsonify({
        'arangodb_status': arangodb_status,
        'commit_hash': commit_hash,
        'repo_url': repo_url
    })


@app.errorhandler(UnauthorizedAccess)
def unauthorized_access(err):
    resp = {
        'error': '403 - Unauthorized',
        'auth_url': err.auth_url
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
    if os.environ.get('FLASK_DEBUG'):
        resp['error_class'] = err.__class__.__name__
        resp['error_details'] = str(err)
    return (flask.jsonify(resp), 500)


@app.after_request
def log_response(response):
    """Simple log of each request's response."""
    print(' '.join([flask.request.method, flask.request.path, '->', response.status]))
    return response
