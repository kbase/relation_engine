"""The primary router for the Relation Engine API v1."""
import time
import subprocess
import flask
from flasgger import swag_from

api_v1 = flask.Blueprint('api_v1', __name__)


@api_v1.route('/', methods=['GET'])
def root():
    """
    Server status.
    ---
    tags: ["root"]
    parameters: []
    responses:
      200: {description: "Server status."}
    """
    return flask.jsonify({
        'docs': '/apidocs',
        'server_time': int(time.time() * 1000),
        'current_commit_hash': subprocess.check_output(['cat', '.git/refs/heads/master']).strip()
    })


@swag_from('show_views.yaml')
@api_v1.route('/views', methods=['GET'])
def show_views():
    """See ./show_views.yaml for documentation."""
    return flask.jsonify({'test': True})


@swag_from('run_query.yaml')
@api_v1.route('/query', methods=['GET'])
def run_query():
    """See ./run_query.yaml for documentation."""
    return flask.jsonify([])


@swag_from('show_schemas.yaml')
@api_v1.route('/schemas', methods=['GET'])
def show_schemas():
    """See ./show_schemas.yaml for documentation."""
    return flask.jsonify({})


@swag_from('save_documents.yaml')
@api_v1.route('/documents', methods=['PUT'])
def save_documents():
    """See ./save_documents.yaml for documentation."""
    return flask.jsonify({})


# @swag_from('delete_documents.yaml')
# @api_v1.route('/documents', methods=['DELETE'])
# def delete_documents():
#     """See ./delete_documents.yaml for documentation."""
#     return flask.jsonify({})
