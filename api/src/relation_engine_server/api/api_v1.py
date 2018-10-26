"""The primary router for the Relation Engine API v1."""
import time
import flask
from flasgger import swag_from
import relation_engine_spec.views
import relation_engine_spec.schemas

from src.relation_engine_server.arango_utils.arango_requests import (
    arango_post_request,
    arango_server_status,
    ArangoServerError
)

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
    with open('.git/refs/heads/master', 'r') as fd:
        commit_hash = fd.read().strip()
    return flask.jsonify({
        'server_time': int(time.time() * 1000),
        'current_commit_hash': commit_hash,
        'arangodb_status': arango_server_status()
    })


@swag_from('show_views.yaml', validation=True)
@api_v1.route('/views', methods=['GET'])
def show_views():
    """See ./show_views.yaml for documentation."""
    view_names = relation_engine_spec.views.get_view_names()
    resp = {'names': view_names}
    if flask.request.args.get('show_source'):
        resp['content'] = {}
        for name in view_names:
            resp['content'][name] = relation_engine_spec.views.get_view_content(name)
    return flask.jsonify(resp)


@swag_from('run_query.yaml', validation=True)
@api_v1.route('/views/<view_name>/query', methods=['POST'])
def run_query(view_name):
    """See ./run_query.yaml for documentation."""
    view_source = relation_engine_spec.views.get_view_content(view_name)
    bind_vars = flask.request.json
    # Make a request to the Arango server to run the query
    req_json = {'query': view_source, 'batchSize': 100, 'count': True, 'bindVars': bind_vars}
    resp_data = arango_post_request('/_api/cursor', data=req_json)
    return flask.jsonify(resp_data)


@swag_from('show_schemas.yaml', validation=True)
@api_v1.route('/schemas', methods=['GET'])
def show_schemas():
    """See ./show_schemas.yaml for documentation."""
    schema_names = relation_engine_spec.schemas.get_schema_names()
    resp = {'names': schema_names}
    if flask.request.args.get('show_source'):
        resp['content'] = {}
        for name in schema_names:
            resp['content'][name] = relation_engine_spec.schemas.get_schema_content(name)
    return flask.jsonify({})


@swag_from('save_documents.yaml', validation=True)
@api_v1.route('/documents', methods=['PUT'])
def save_documents():
    """See ./save_documents.yaml for documentation."""
    data_stream = flask.request.stream
    q = {
        'collection': flask.request.args['collection'],
        'onDuplicate': flask.request.args['onDuplicate'],
        'type': 'documents'
    }
    arango_post_request('/_api/import', data_stream, query=q)
    return flask.jsonify({})


@api_v1.errorhandler(ArangoServerError)
@api_v1.errorhandler(relation_engine_spec.views.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    return (flask.jsonify({'error': str(err)}), 400)
