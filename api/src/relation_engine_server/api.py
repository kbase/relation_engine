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
    Auth:
     - only kbase re admins for ad-hoc queries
     - public for views (views will have access controls within them based on params)
    """
    # Note that flask.request.json only works if the request Content-Type is application/json
    json_body = json.loads(flask.request.get_data() or '{}')
    # Don't allow the user to set the special 'ws_ids' field
    json_body['ws_ids'] = []
    auth_token = auth.get_auth_header()
    if auth_token:
        # Handle workspace authentication
        json_body['ws_ids'] = auth.get_workspace_ids(auth_token)
    if 'query' in json_body:
        # Run an adhoc query for a sysadmin
        auth.require_auth_token(roles=['RE_ADMIN'])
        query_text = json_body['query']
        del json_body['query']
        resp_body = arango_client.run_query(query_text=query_text, bind_vars=json_body)
        return flask.jsonify(resp_body)
    if 'view' in flask.request.args:
        # Run a query from a view name
        view_name = flask.request.args['view']
        view_source = spec_loader.get_view(view_name)
        resp_body = arango_client.run_query(query_text=view_source, bind_vars=json_body)
        return flask.jsonify(resp_body)
    if 'cursor_id' in flask.request.args:
        # Run a query from a cursor ID
        cursor_id = flask.request.args['cursor_id']
        resp_body = arango_client.run_query(cursor_id=cursor_id)
        return flask.jsonify(resp_body)
    # No valid options were passed
    resp_body = {'error': 'Pass in a view or a cursor_id'}
    return (flask.jsonify(resp_body), 400)


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
    Manually check for updates, download spec releases, and init new collections.
    Auth: admin
    """
    auth.require_auth_token(['RE_ADMIN'])
    pull_spec.download_latest(init_collections='init_collections' in flask.request.args)
    return flask.jsonify({'status': 'updated'})


@api.route('/documents', methods=['PUT'])
def save_documents():
    """
    Create, update, or replace many documents in a batch.
    Auth: admin
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
