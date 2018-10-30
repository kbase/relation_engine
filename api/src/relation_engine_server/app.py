"""The main entrypoint for running the Flask server."""
import flask
import os
from uuid import uuid4
import traceback

from .arango_utils.arango_requests import arango_server_status

from .api import api
from .docs import docs
from .exceptions import MissingHeader, UnauthorizedAccess

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(docs, url_prefix='/docs')


@app.route('/', methods=['GET'])
def root():
    """Server status and link to docs."""
    with open('.git/refs/heads/master', 'r') as fd:
        commit_hash = fd.read().strip()
    arangodb_status = arango_server_status()
    repo_url = 'https://github.com/kbase/relation_engine_api.git'
    return flask.jsonify({
        'arangodb_status': arangodb_status,
        'commit_hash': commit_hash,
        'repo_url': repo_url,
        'docs': '/docs'
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
    return (flask.jsonify({'error': 'Unexpected server error'}), 500)


@app.after_request
def log_response(response):
    """Simple log of each request's response."""
    print(' '.join([flask.request.method, flask.request.path, '->', response.status]))
    return response
