"""The main entrypoint for running the Flask server."""
import flask
import os
from uuid import uuid4
from flasgger import Swagger

from .api.api_v1 import api_v1

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`

app.register_blueprint(api_v1, url_prefix='/v1')

swagger_template = {
    'openapi': '3.0.2',
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
    """Redirects to the Swagger API docs."""
    return flask.redirect('/apidocs')


@app.errorhandler(404)
def page_not_found(err):
    return (flask.jsonify({'status': 'error', 'error': '404 - Not found.'}), 404)


@app.errorhandler(405)
def method_not_allowed(err):
    return (flask.jsonify({'status': 'error', 'error': '405 - Method not allowed.'}), 405)
