import flask
from relation_engine_server.utils import (
    arango_client,
    spec_loader,
    auth,
    bulk_import,
    pull_spec,
    config,
    parse_json
)
from relation_engine_server.utils.json_validation import run_validator
from relation_engine_server.exceptions import InvalidParameters

api_v1 = flask.Blueprint('api_v1', __name__)


@api_v1.route("/data_sources", methods=['GET'])
def list_data_sources():
    # note the custom response format is used by the frontend, so this endpoint is provided
    # in addition to the /specs/data_sources endpoint

    data_sources = spec_loader.get_names('data_sources')
    return flask.jsonify({'data_sources': data_sources})


@api_v1.route("/data_sources/<name>", methods=['GET'])
def fetch_data_source(name):

    data_source = spec_loader.get_schema('data_source', name)
    return flask.jsonify({'data_source': data_source})


@api_v1.route('/specs/data_sources', methods=['GET'])
def show_data_sources():
    """Show the current data sources loaded from the spec."""
    name = flask.request.args.get('name')
    if name:
        return flask.jsonify(spec_loader.get_schema('data_source', name))
    return flask.jsonify(spec_loader.get_names('data_sources'))


@api_v1.route('/specs/stored_queries', methods=['GET'])
def show_stored_queries():
    """Show the current stored query names loaded from the spec."""
    name = flask.request.args.get('name')
    if name:
        return flask.jsonify({'stored_query': spec_loader.get_schema('stored_query', name)})
    return flask.jsonify(spec_loader.get_names('stored_query'))


@api_v1.route('/specs/collections', methods=['GET'])
@api_v1.route('/specs/schemas', methods=['GET'])
def show_collections():
    """Show the names of the (document) collections (edges and vertices) loaded from the spec."""
    name = flask.request.args.get('name')
    doc_id = flask.request.args.get('doc_id')
    if name:
        return flask.jsonify(spec_loader.get_schema('collection', name))
    elif doc_id:
        return flask.jsonify(spec_loader.get_schema_for_doc(doc_id))
    else:
        return flask.jsonify(spec_loader.get_names('collection'))


@api_v1.route('/query_results', methods=['POST'])
def run_query():
    """
    Run a stored query as a query against the database.
    Auth:
     - only kbase re admins for ad-hoc queries
     - public stored queries (these have access controls within them based on params)
    """
    json_body = parse_json.get_json_body() or {}
    # fetch number of documents to return
    batch_size = int(flask.request.args.get('batch_size', 10000))
    full_count = flask.request.args.get('full_count', False)

    if 'query' in json_body:
        # Run an adhoc query for a sysadmin
        auth.require_auth_token(roles=['RE_ADMIN'])
        query_text = _preprocess_stored_query(json_body['query'], json_body)
        del json_body['query']
        if 'ws_ids' in query_text:
            # Fetch any authorized workspace IDs using a KBase auth token, if present
            auth_token = auth.get_auth_header()
            json_body['ws_ids'] = auth.get_workspace_ids(auth_token)

        resp_body = arango_client.run_query(query_text=query_text,
                                            bind_vars=json_body,
                                            batch_size=batch_size,
                                            full_count=full_count)
        return flask.jsonify(resp_body)

    if 'stored_query' in flask.request.args or 'view' in flask.request.args:
        # Run a query from a query name
        # Note: we are maintaining backwards compatibility here with the "view" arg.
        # "stored_query" is the more accurate name
        query_name = flask.request.args.get('stored_query') or flask.request.args.get('view')
        stored_query = spec_loader.get_stored_query(query_name)

        if 'params' in stored_query:
            # Validate the user params for the query
            stored_query_path = spec_loader.get_stored_query(query_name, path_only=True)
            run_validator(schema_file=stored_query_path, data=json_body, validate_at='/params')

        stored_query_source = _preprocess_stored_query(stored_query['query'], stored_query)
        if 'ws_ids' in stored_query_source:
            # Fetch any authorized workspace IDs using a KBase auth token, if present
            auth_token = auth.get_auth_header()
            json_body['ws_ids'] = auth.get_workspace_ids(auth_token)

        resp_body = arango_client.run_query(query_text=stored_query_source,
                                            bind_vars=json_body,
                                            batch_size=batch_size,
                                            full_count=full_count)
        return flask.jsonify(resp_body)

    if 'cursor_id' in flask.request.args:
        # Run a query from a cursor ID
        cursor_id = flask.request.args['cursor_id']
        resp_body = arango_client.run_query(cursor_id=cursor_id)
        return flask.jsonify(resp_body)
    # No valid options were passed
    raise InvalidParameters('Pass in a query name or a cursor_id')


@api_v1.route('/specs', methods=['PUT'])
def update_specs():
    """
    Manually check for updates, download spec releases, and init new collections.
    Auth: admin
    """
    auth.require_auth_token(['RE_ADMIN'])
    init_collections = 'init_collections' in flask.request.args
    release_url = flask.request.args.get('release_url')
    pull_spec.download_specs(init_collections, release_url, reset=True)
    return flask.jsonify({'status': 'updated'})


@api_v1.route('/documents', methods=['PUT'])
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
    resp = bulk_import.bulk_import(query)
    if resp.get('errors') > 0:
        return (flask.jsonify(resp), 400)
    else:
        return flask.jsonify(resp)


@api_v1.route('/config', methods=['GET'])
def show_config():
    """Show public config data."""
    conf = config.get_config()
    return flask.jsonify({
        'auth_url': conf['auth_url'],
        'workspace_url': conf['workspace_url'],
        'kbase_endpoint': conf['kbase_endpoint'],
        'db_url': conf['db_url'],
        'db_name': conf['db_name'],
        'spec_url': conf['spec_url']
    })


def _preprocess_stored_query(query_text, config):
    """Inject some default code into each stored query."""
    ws_id_text = " LET ws_ids = @ws_ids " if 'ws_ids' in query_text else ""
    return (
        config.get('query_prefix', '') +
        ws_id_text +
        query_text
    )
