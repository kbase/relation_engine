"""The primary router for the Relation Engine API."""
import flask
import json
from jsonschema.exceptions import ValidationError

from . import spec_loader, arango_client, auth, bulk_import, pull_spec

api = flask.Blueprint('api', __name__)


@api.route('/views', methods=['GET'])
def show_views():
    """
    Fetch view names and content.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_view_names())


@api.route('/query_results', methods=['POST'])
def run_query():
    """
    Run a stored view as a query against the database.
    Auth: only kbase users (any role)
    """
    auth.require_auth_token(roles=[])
    if 'view' in flask.request.args:
        view_name = flask.request.args['view']
        view_source = spec_loader.get_view(view_name)
        bind_vars = flask.request.json or {}
        resp = arango_client.run_query(query_text=view_source, bind_vars=bind_vars)
    elif 'cursor_id' in flask.request.args:
        cursor_id = flask.request.args['cursor_id']
        resp = arango_client.run_query(cursor_id=cursor_id)
    else:
        resp = {'error': 'Pass in a view or a cursor_id'}
        return (flask.jsonify(resp), 400)
    return flask.jsonify(resp)


@api.route('/schemas', methods=['GET'])
def show_schemas():
    """
    Fetch schema names and content.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_schema_names())


@api.route('/schemas/<name>', methods=['GET'])
def show_schema(name):
    """
    Fetch the JSON for a single schema.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_schema(name))


@api.route('/views/<name>', methods=['GET'])
def show_view(name):
    """
    Fetch the AQL for a single view.
    Auth: public
    """
    return flask.Response(spec_loader.get_view(name), mimetype='text/plain')


@api.route('/update_specs', methods=['GET'])
def refresh_specs():
    """
    Manually pull from the spec git repo to get updates.
    """
    auth.require_auth_token(['RE_ADMIN'])
    status = pull_spec.download_latest(
        reset='reset' in flask.request.args,
        init_collections='init_collections' in flask.request.args
    )
    return flask.jsonify({'status': status})


@api.route('/documents', methods=['PUT'])
def save_documents():
    """
    Create, update, or replace many documents in a batch.
    Auth: only sysadmins
    """
    auth.require_auth_token(['RE_ADMIN'])
    collection_name = flask.request.args['collection']
    query = {'collection': collection_name, 'type': 'documents'}
    if flask.request.args.get('display_errors'):
        # Display an array of error messages
        query['details'] = 'true'
    if flask.request.args.get('on_duplicate'):
        query['onDuplicate'] = flask.request.args['on_duplicate']
    if flask.request.args.get('overwrite'):
        query['overwrite'] = 'true'
    resp_text = bulk_import.bulk_import(query)
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
        'name': err.name
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
