"""The primary router for the Relation Engine API."""
import flask
import json
import tempfile
import jsonschema
from jsonschema.exceptions import ValidationError

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
    Auth: public
    """
    view_names = relation_engine_spec.views.get_view_names()
    resp = {'names': view_names}
    if flask.request.args.get('show_source'):
        resp['content'] = {}
        for name in view_names:
            resp['content'][name] = relation_engine_spec.views.get_view_content(name)
    return flask.jsonify(resp)


@api.route('/query_cursor', methods=['GET'])
def run_query_cursor():
    """
    Continue fetching query results from a cursor id
    Auth: only kbase users (any role)
    """
    require_auth_token(roles=[])
    cursor_id = flask.request.args['id']
    resp = run_query(cursor_id=cursor_id)
    return flask.jsonify(resp)


@api.route('query', methods=['POST'])
def run_query():
    """
    Run a stored view as a query against the database.
    Auth: only kbase users (any role)
    """
    require_auth_token(roles=[])
    view_name = flask.request.args['view']
    view_source = relation_engine_spec.views.get_view_content(view_name)
    bind_vars = flask.request.json
    # Make a request to the Arango server to run the query
    resp = run_query(query=view_source, bind_vars=bind_vars)
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
    temp_fd = tempfile.NamedTemporaryFile()
    with open(temp_fd.name, 'a') as fd:
        for line in flask.request.stream:
            json_line = json.loads(line)
            jsonschema.validate(json_line, schema)
            fd.write(json.dumps(json_line) + '\n')
    resp_text = bulk_import(temp_fd.name, query)
    temp_fd.close()  # Also deletes the file
    return resp_text


@api.errorhandler(json.decoder.JSONDecodeError)
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


@api.errorhandler(ArangoServerError)
@api.errorhandler(relation_engine_spec.views.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    return (flask.jsonify({'error': str(err)}), 400)


@api.errorhandler(ValidationError)
def validation_error(err):
    """Json Schema validation error."""
    resp = {
        'error': str(err).split('\n')[0],
        'instance': err.instance,
        'validator': err.validator,
        'validator_value': err.validator_value,
        'schema': err.schema
    }
    return (flask.jsonify(resp), 400)


@api.errorhandler(relation_engine_spec.schemas.SchemaNonexistent)
def schema_nonexistent(err):
    """A schema/collection was requested but does not exist."""
    resp = {
        'error': str(err)
        # 'available_schemas': err.available_schemas
        # 'nonexistent_schema': err.schema_name
    }
    return (flask.jsonify(resp), 400)
