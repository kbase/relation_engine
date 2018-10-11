"""The primary router for the Relation Engine API v1."""
import flask
from flasgger import swag_from

api_v1 = flask.Blueprint('api_v1', __name__)


@swag_from('create_view.yaml')
@api_v1.route('/views', methods=['POST'])
def create_view():
    """See ./create_view.yaml for documentation."""
    return flask.jsonify({'test': True})


@swag_from('query_view.yaml')
@api_v1.route('/views', methods=['GET'])
def query_view():
    """See ./query_view.yaml for documentation."""
    return flask.jsonify([])


@swag_from('create_schema.yaml')
@api_v1.route('/schemas', methods=['POST'])
def create_schema():
    """See ./create_schema.yaml for documentation."""
    return flask.jsonify({})


@swag_from('fetch_schemas.yaml')
@api_v1.route('/schemas', methods=['GET'])
def fetch_schemas():
    """See ./fetch_schemas.yaml for documentation."""
    return flask.jsonify({})


@api_v1.route('/documents', methods=['PUT'])
def save_documents():
    """See ./save_documents.yaml for documentation."""
    return flask.jsonify({})


@swag_from('delete_documents.yaml')
@api_v1.route('/documents', methods=['DELETE'])
def delete_documents():
    """See ./delete_documents.yaml for documentation."""
    return flask.jsonify({})
