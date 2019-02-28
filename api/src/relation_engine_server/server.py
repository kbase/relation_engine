"""The main entrypoint for running the Flask server."""
import flask
import json
import os
from uuid import uuid4
import traceback
from jsonschema.exceptions import ValidationError

from .exceptions import MissingHeader, UnauthorizedAccess
from .utils import arango_client, spec_loader, auth, bulk_import, pull_spec, config

app = flask.Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', True)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`


@app.route('/', methods=['GET'])
def root():
    """Server status."""
    if os.path.exists('.git/refs/heads/master'):
        with open('.git/refs/heads/master', 'r') as fd:
            commit_hash = fd.read().strip()
    else:
        commit_hash = 'unknown'
    arangodb_status = arango_client.server_status()
    repo_url = 'https://github.com/kbase/relation_engine_api.git'
    return flask.jsonify({
        'arangodb_status': arangodb_status,
        'commit_hash': commit_hash,
        'repo_url': repo_url
    })


@app.route('/config', methods=['GET'])
def show_config():
    conf = config.get_config()
    return flask.jsonify({
        'auth_url': conf['auth_url'],
        'workspace_url': conf['workspace_url'],
        'kbase_endpoint': conf['kbase_endpoint'],
        'db_url': conf['db_url'],
        'db_name': conf['db_name'],
        'spec_url': conf['spec_url']
    })


@app.route('/api/views', methods=['GET'])
def show_views():
    """
    Fetch view names and content.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_view_names())


@app.route('/api/query_results', methods=['POST'])
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
    # Fetch any authorized workspace IDs using a KBase auth token, if present
    json_body['ws_ids'] = auth.get_workspace_ids(auth_token)
    # fetch number of documents to return
    batch_size = int(flask.request.args.get('batch_size', 100))
    if 'query' in json_body:
        # Run an adhoc query for a sysadmin
        auth.require_auth_token(roles=['RE_ADMIN'])
        query_text = json_body['query']
        del json_body['query']
        resp_body = arango_client.run_query(query_text=query_text,
                                            bind_vars=json_body,
                                            batch_size=batch_size)
        return flask.jsonify(resp_body)
    if 'view' in flask.request.args:
        # Run a query from a view name
        view_name = flask.request.args['view']
        view_source = spec_loader.get_view(view_name)
        resp_body = arango_client.run_query(query_text=view_source,
                                            bind_vars=json_body,
                                            batch_size=batch_size)
        return flask.jsonify(resp_body)
    if 'cursor_id' in flask.request.args:
        # Run a query from a cursor ID
        cursor_id = flask.request.args['cursor_id']
        resp_body = arango_client.run_query(cursor_id=cursor_id)
        return flask.jsonify(resp_body)
    # No valid options were passed
    resp_body = {'error': 'Pass in a view or a cursor_id'}
    return (flask.jsonify(resp_body), 400)


@app.route('/api/schemas', methods=['GET'])
def show_schemas():
    """
    Fetch schema names and content.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_schema_names())


@app.route('/api/schemas/<name>', methods=['GET'])
def show_schema(name):
    """
    Fetch the JSON for a single schema.
    Auth: public
    """
    return flask.jsonify(spec_loader.get_schema(name))


@app.route('/api/views/<name>', methods=['GET'])
def show_view(name):
    """
    Fetch the AQL for a single view.
    Auth: public
    """
    return flask.Response(spec_loader.get_view(name), mimetype='text/plain')


@app.route('/api/update_specs', methods=['GET'])
def refresh_specs():
    """
    Manually check for updates, download spec releases, and init new collections.
    Auth: admin
    """
    auth.require_auth_token(['RE_ADMIN'])
    init_collections = 'init_collections' in flask.request.args
    release_url = flask.request.args.get('release_url')
    pull_spec.download_specs(init_collections, release_url)
    return flask.jsonify({'status': 'updated'})


@app.route('/api/documents', methods=['PUT'])
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


@app.errorhandler(json.decoder.JSONDecodeError)
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


@app.errorhandler(arango_client.ArangoServerError)
def arango_server_error(err):
    resp = {
        'error': str(err),
        'arango_message': err.resp_json['errorMessage']
    }
    return (flask.jsonify(resp), 400)


@app.errorhandler(spec_loader.SchemaNonexistent)
@app.errorhandler(spec_loader.ViewNonexistent)
def view_does_not_exist(err):
    """General error cases."""
    resp = {
        'error': str(err),
        'name': err.name
    }
    return (flask.jsonify(resp), 400)


@app.errorhandler(ValidationError)
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


@app.errorhandler(UnauthorizedAccess)
def unauthorized_access(err):
    resp = {
        'error': '403 - Unauthorized',
        'auth_url': err.auth_url,
        'auth_response': err.response
    }
    return (flask.jsonify(resp), 403)


@app.errorhandler(404)
def page_not_found(err):
    return (flask.jsonify({'error': '404 - Not found.'}), 404)


@app.errorhandler(405)
def method_not_allowed(err):
    return (flask.jsonify({'error': '405 - Method not allowed.'}), 405)


@app.errorhandler(MissingHeader)
def generic_400(err):
    return (flask.jsonify({'error': str(err)}), 400)


# Any other unhandled exceptions -> 500
@app.errorhandler(Exception)
@app.errorhandler(500)
def server_error(err):
    print('=' * 80)
    print('500 Unexpected Server Error')
    print('-' * 80)
    traceback.print_exc()
    print('=' * 80)
    resp = {'error': '500 - Unexpected server error'}
    # if os.environ.get('FLASK_DEBUG'):  TODO
    resp['error_class'] = err.__class__.__name__
    resp['error_details'] = str(err)
    return (flask.jsonify(resp), 500)


@app.after_request
def after_request(response):
    """Actions to perform on the response after the request handler finishes running."""
    print(' '.join([flask.request.method, flask.request.path, '->', response.status]))
    # Enable CORS
    response.headers['Access-Control-Allow-Origin'] = '*'
    env_allowed_headers = os.environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', 'authorization')
    response.headers['Access-Control-Allow-Headers'] = env_allowed_headers
    # Set JSON content type and response length
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Length'] = response.calculate_content_length()
    return response
