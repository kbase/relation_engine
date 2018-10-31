"""The primary router for the Relation Engine API."""
import flask
import json
import tempfile
import jsonschema
from jsonschema.exceptions import ValidationError

from .auth import require_auth_token
from . import spec_loader
from . import arango_client

api = flask.Blueprint('api', __name__)


@api.route('/views', methods=['GET'])
def show_views():
    """
    Fetch view names and content.
    Auth: public
    """
    view_names = spec_loader.get_view_names()
    resp = {'names': view_names}
    if flask.request.args.get('show_source'):
        resp['content'] = spec_loader.get_view_content(view_names)
    return flask.jsonify(resp)


@api.route('/query_cursor', methods=['GET'])
def run_query_cursor():
    """
    Continue fetching query results from a cursor id
    Auth: only kbase users (any role)
    """
    require_auth_token(roles=[])
    cursor_id = flask.request.args['id']
    resp = arango_client.run_query(cursor_id=cursor_id)
    return flask.jsonify(resp)


@api.route('query', methods=['POST'])
def run_query_from_view():
    """
    Run a stored view as a query against the database.
    Auth: only kbase users (any role)
    """
    require_auth_token(roles=[])
    view_name = flask.request.args['view']
    view_source = spec_loader.get_view_content([view_name])[view_name]
    bind_vars = flask.request.json or {}
    # Make a request to the Arango server to run the query
    resp = arango_client.run_query(query_text=view_source, bind_vars=bind_vars)
    return flask.jsonify(resp)


@api.route('/schemas', methods=['GET'])
def show_schemas():
    """
    Fetch schema names and content.
    See ./show_schemas.yaml for documentation.
    Auth: public
    """
    schema_names = spec_loader.get_schema_names()
    resp = {'names': schema_names}
    if flask.request.args.get('show_source'):
        resp['content'] = spec_loader.get_schema_dicts(schema_names)
    return flask.jsonify(resp)


@api.route('/documents', methods=['PUT'])
def save_documents():
    """
    Create, update, or replace many documents in a batch.
    See ./save_documents.yaml for documentation.
    Auth: only sysadmins
    """
    require_auth_token(['RE_ADMIN'])
    coll = flask.request.args['collection']
    query = {'collection': coll, 'type': 'documents'}
    schema = spec_loader.get_schema_dicts([coll])[coll]
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
    resp_text = arango_client.bulk_import(temp_fd.name, query)
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


@api.errorhandler(arango_client.ArangoServerError)
def arango_server_error(err):
    resp = {
        'error': str(err),
        'arango_message': err.resp_json['errorMessage']
    }
    return (flask.jsonify(resp), 400)


@api.errorhandler(spec_loader.SchemaNonexistent)
@api.errorhandler(spec_loader.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    resp = {
        'error': str(err),
        'name': err.name,
        'available': err.available
    }
    return (flask.jsonify(resp), 400)


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


@api.errorhandler(spec_loader.SchemaNonexistent)
def schema_nonexistent(err):
    """A schema/collection was requested but does not exist."""
    resp = {
        'error': str(err)
        # 'available_schemas': err.available_schemas
        # 'nonexistent_schema': err.schema_name
    }
    return (flask.jsonify(resp), 400)
