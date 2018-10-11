"""The main entrypoint for running the Flask server."""
import time
import flask
import os
import subprocess
from uuid import uuid4
from flasgger import Swagger

from .api.api_v1 import api_v1

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`

app.register_blueprint(api_v1, url_prefix='/v1')

swagger_template = {
    'swagger': '2.0',
    'info': {
        'title': 'Relation Engine API',
        'description': 'API for working with the KBase Relation Engine graph database.',
        'contact': {
            'responsibleOrganization': 'DOE KBase',
            'responsibleDeveloper': 'Jay R Bolton <jrbolton@lbl.gov>',
            'email': 'scanon@lbl.gov',
            'url': 'https://kbase.us'
        },
        'version': '1'
    },
    'schemes': ['https']
}

swagger = Swagger(app, template=swagger_template)


@app.route('/', methods=['GET'])
def root():
    """
    Root endpoint that gives server status.
    ---
    tags: ["root"]
    parameters: []
    responses:
        200:
            description: "An object of API version links in the form {version_name: version_path}"
            schema: {type: object}
        schema:
            type: object
            properties:
                versions: {type: array, items: {type: string}}
                server_time: {type: integer}
                current_commit_hash: {type: string}
    """
    return flask.jsonify({
        'versions': ['/v1'],
        'server_time': int(time.time() * 1000),
        'current_commit_hash': subprocess.check_output(['cat', '.git/refs/heads/master']).strip()
    })


@app.errorhandler(404)
def page_not_found(err):
    return (flask.jsonify({'status': 'error', 'error': '404 - Not found.'}), 404)
