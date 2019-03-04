import flask
from ..utils import arango_client, spec_loader, auth, bulk_import, pull_spec, config, parse_json
from ..exceptions import InvalidParameters


def show_views():
    """Handle /views."""
    name = flask.request.args.get('name')
    if name:
        return {'view': spec_loader.get_view(name)}
    return spec_loader.get_view_names()


def show_schemas():
    """Handle /schemas."""
    name = flask.request.args.get('name')
    if name:
        return spec_loader.get_schema(name)
    return spec_loader.get_schema_names()


def run_query():
    """
    Run a stored view as a query against the database.
    Auth:
     - only kbase re admins for ad-hoc queries
     - public for views (views will have access controls within them based on params)
    """
    json_body = parse_json.get_json_body() or {}
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
        return resp_body
    if 'view' in flask.request.args:
        # Run a query from a view name
        view_name = flask.request.args['view']
        view_source = spec_loader.get_view(view_name)
        resp_body = arango_client.run_query(query_text=view_source,
                                            bind_vars=json_body,
                                            batch_size=batch_size)
        return resp_body
    if 'cursor_id' in flask.request.args:
        # Run a query from a cursor ID
        cursor_id = flask.request.args['cursor_id']
        resp_body = arango_client.run_query(cursor_id=cursor_id)
        return resp_body
    # No valid options were passed
    raise InvalidParameters('Pass in a view or a cursor_id')


def update_specs():
    """
    Manually check for updates, download spec releases, and init new collections.
    Auth: admin
    """
    auth.require_auth_token(['RE_ADMIN'])
    init_collections = 'init_collections' in flask.request.args
    release_url = flask.request.args.get('release_url')
    pull_spec.download_specs(init_collections, release_url)
    return {'status': 'updated'}


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


def show_config():
    """Show public config data."""
    conf = config.get_config()
    return {
        'auth_url': conf['auth_url'],
        'workspace_url': conf['workspace_url'],
        'kbase_endpoint': conf['kbase_endpoint'],
        'db_url': conf['db_url'],
        'db_name': conf['db_name'],
        'spec_url': conf['spec_url']
    }


endpoints = {
    'query_results': {'handler': run_query, 'methods': {'POST'}},
    'specs/schemas': {'handler': show_schemas},
    'specs/views': {'handler': show_views},
    'config': {'handler': show_config},
    'specs': {'handler': update_specs, 'methods': {'PUT'}},
    'documents': {'handler': save_documents, 'methods': {'PUT'}}
}
