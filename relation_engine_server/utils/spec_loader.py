"""
Utilities for loading stored queries, collections, and migrations from the spec.
"""
import glob
import json
import os
import re
import yaml

from relation_engine_server.utils.config import get_config

_CONF = get_config()

_schema_types = {
    # singular version of schema_type names
    'singular': ['collection', 'dataset', 'data_source', 'stored_query', 'view'],
    # plural version of schema_type names
    'plural': ['collections', 'datasets', 'data_sources', 'stored_queries', 'views']
}

_VALID_SCHEMA_TYPES = _schema_types['singular'] + _schema_types['plural']


def _switch_schema_type_name(schema_type, to_form):
    """switch a schema_type name to the `to_form` version, ensuring that the schema exists first"""

    # this schema type does not exist
    if schema_type not in _VALID_SCHEMA_TYPES:
        raise SchemaNonexistent(schema_type)

    if schema_type in _schema_types[to_form]:
        return schema_type

    from_form = 'singular' if to_form == 'plural' else 'plural'
    ix = _schema_types[from_form].index(schema_type)
    return _schema_types[to_form][ix]


def pluralise_schema_type(schema_type):
    """ensure a schema_type is in the plural form"""
    return _switch_schema_type_name(schema_type, 'plural')


def singularise_schema_type(schema_type):
    """ensure a schema_type is in the singular form"""
    return _switch_schema_type_name(schema_type, 'singular')


def get_names(schema_type):
    """
    get a list of all schemas of the specified schema_type

    Throws a SchemaNonexistent error if the schema_type does not exist.
    """

    # ensure that the name is in the plural form
    schema_search_type = pluralise_schema_type(schema_type)

    yaml_paths = _find_paths(_CONF['spec_paths'][schema_search_type], '*.yaml')
    json_paths = _find_paths(_CONF['spec_paths'][schema_search_type], '*.json')

    names = [_get_file_name(path) for path in sorted(yaml_paths + json_paths)]

    return names


def get_schema(schema_type, name, path_only=False):
    """
    Get content or file path for a named schema of specified schema_type.
    If path_only is true, the file path is returned; if not, the file contents are returned.

    Throws a SchemaNonexistent error if the named schema does not exist.
    """

    schema_search_type = pluralise_schema_type(schema_type)

    yaml_paths = _find_paths(_CONF['spec_paths'][schema_search_type], f'{name}.yaml')
    json_paths = _find_paths(_CONF['spec_paths'][schema_search_type], f'{name}.json')
    # ensure we're using the canonical path and that all paths are unique
    # we are only interested in paths that are in the designated spec repo
    repo_path = os.path.abspath(_CONF['spec_paths']['repo'])
    all_paths = [p for p in set(os.path.abspath(path) for path in yaml_paths + json_paths) if repo_path in p]

    if len(all_paths) == 0:
        raise SchemaNonexistent(singularise_schema_type(schema_type), name)

    # ignore duplicates or multiple results, just go with the first one
    path = all_paths[0]
    if path_only:
        return path

    with open(path) as fd:
        if path.endswith('.json'):
            contents = json.load(fd)
        else:
            contents = yaml.safe_load(fd)

        if schema_search_type == 'data_sources' and 'logo_path' in contents:
            # Append the logo root url to be the ui-assets server url with the correct environment
            base_logo_url = re.sub(r'\/services\/?', '/ui-assets', _CONF['kbase_endpoint'])
            contents['logo_url'] = base_logo_url + contents['logo_path']
            del contents['logo_path']

        return contents


def get_collection_names():
    """Return a dict of vertex and edge base names."""
    return get_names('collections')


def get_data_source_names():
    """Return an array of all the data source names."""
    return get_names('data_sources')


def get_stored_query_names():
    """Return an array of all stored queries base names."""
    return get_names('stored_queries')


def get_view_names():
    """Return an array of all stored queries base names."""
    return get_names('views')


def get_collection(name, path_only=False):
    """Get YAML content (or file path) for a specific collection. Throws an error if nonexistent."""
    return get_schema('collection', name, path_only)


def get_schema_for_doc(doc_id, path_only=False):
    """Get the schema for a particular document by its full ID."""
    (coll_name, _) = doc_id.split('/')
    return get_schema('collection', coll_name, path_only)


def get_data_source(name, path_only=False):
    """Get YAML content (or file path) for a data source. Throws an error if it does not exist."""
    return get_schema('data_source', name, path_only)


def get_stored_query(name, path_only=False):
    """Get AQL content or file path for a specific stored query. Throws an error if nonexistent."""
    return get_schema('stored_query', name, path_only)


def get_view(name, path_only=False):
    """Get AQL content or file path for a specific stored query. Throws an error if nonexistent."""
    return get_schema('view', name, path_only)


def _find_paths(dir_path, file_pattern):
    """
    Return all file paths from a filename pattern, starting from a parent
    directory and looking in all subdirectories.
    """
    pattern = os.path.join(dir_path, '**', file_pattern)
    return glob.glob(pattern, recursive=True)


def _get_file_name(path):
    """
    Get the file base name without extension from a file path.
    """
    return os.path.splitext(os.path.basename(path))[0]


class SchemaNonexistent(Exception):
    """Requested schema or schema type is not in the spec"""

    def __init__(self, schema_type, name=None):
        self.schema_type = schema_type
        self.name = name

    def __str__(self):
        schema_type = self.schema_type.capitalize().replace("_", " ")
        if self.name is None:
            return f"{schema_type} does not exist."

        return f"{schema_type} '{self.name}' does not exist."
