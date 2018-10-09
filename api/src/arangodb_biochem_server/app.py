"""The main entrypoint for running the Flask server."""
import flask
import os
from uuid import uuid4

from .api.api_v1 import api_v1

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`

app.register_blueprint(api_v1, url_prefix='/v1')


@app.route('/', methods=['GET'])
def root():
    """Root path for the entire service; lists all API endpoints."""
    return flask.jsonify({'test': True})


@app.errorhandler(404)
def page_not_found(err):
    return (flask.jsonify({'status': 'error', 'error': '404 - Not found.'}), 404)
