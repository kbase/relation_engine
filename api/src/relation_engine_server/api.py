"""The primary router for the Relation Engine API."""
import flask
import json
import tempfile
import jsonschema

import relation_engine_spec.views
import relation_engine_spec.schemas

from src.relation_engine_server.arango_utils.arango_requests import (
    bulk_import,
    ArangoServerError
)

from .auth import require_auth_token

api = flask.Blueprint('api', __name__)


@api.route('/views', methods=['GET'])
def show_views():
    """
    Fetch view names and content.
    See ./show_views.yaml for documentation.
    Auth: public
    """
    view_names = relation_engine_spec.views.get_view_names()
    resp = {'names': view_names}
    if flask.request.args.get('show_source'):
        resp['content'] = {}
        for name in view_names:
            resp['content'][name] = relation_engine_spec.views.get_view_content(name)
    return flask.jsonify(resp)


@api.route('/views/<view_name>/query', methods=['POST'])
def run_query(view_name):
    """
    Run a stored view as a query against the database.
    See ./run_query.yaml for documentation.
    Auth: only kbase users (any role)
    """
    require_auth_token([])
    view_source = relation_engine_spec.views.get_view_content(view_name)
    bind_vars = flask.request.json
    # Make a request to the Arango server to run the query
    resp = run_query(view_source, bind_vars)
    return flask.jsonify(resp)


@api.route('/schemas', methods=['GET'])
def show_schemas():
    """
    Fetch schema names and content.
    See ./show_schemas.yaml for documentation.
    Auth: public
    """
    schema_names = relation_engine_spec.schemas.get_schema_names()
    resp = {'names': schema_names}
    if flask.request.args.get('show_source'):
        resp['content'] = {}
        for name in schema_names:
            resp['content'][name] = relation_engine_spec.schemas.get_schema_as_dict(name)
    return flask.jsonify(resp)


@api.route('/documents', methods=['PUT'])
def save_documents():
    """
    Create, update, or replace many documents in a batch.
    See ./save_documents.yaml for documentation.
    Auth: only sysadmins
    """
    require_auth_token(['RE_ADMIN'])
    query = {
        'collection': flask.request.args['collection'],
        'type': 'documents'
    }
    schema = relation_engine_spec.schemas.get_schema_as_dict(query['collection'])
    if flask.request.args.get('on_duplicate'):
        query['onDuplicate'] = flask.request.args['on_duplicate']
    if flask.request.args.get('overwrite'):
        query['overwrite'] = 'true'
    with tempfile.TemporaryFile(mode='w', encoding='utf-8') as temp_fd:
        for line in flask.request.stream:
            json_line = json.loads(line)
            jsonschema.validate(json_line, schema)
            json.dump(json_line, temp_fd)
        resp_text = bulk_import(temp_fd, query)
    return resp_text


@api.errorhandler(ArangoServerError)
@api.errorhandler(relation_engine_spec.views.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    return (flask.jsonify({'error': str(err)}), 400)
