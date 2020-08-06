"""
Utilities for loading stored queries, collections, and migrations from the spec.
"""
import glob
import os
import yaml

from relation_engine_server.utils.config import get_config

_CONF = get_config()


def get_collection_names():
    """Return a dict of vertex and edge base names."""
    names = []  # type: list
    for path in _find_paths(_CONF['spec_paths']['collections'], '*.yaml'):
        names.append(_get_file_name(path))
    return names


def get_stored_query_names():
    """Return an array of all stored queries base names."""
    names = []  # type: list
    for path in _find_paths(_CONF['spec_paths']['stored_queries'], '*.yaml'):
        names.append(_get_file_name(path))
    return names


def get_collection(name):
    """Get YAML content for a specific collection. Throws an error if nonexistent."""
    try:
        path = _find_paths(_CONF['spec_paths']['collections'], name + '.yaml')[0]
    except IndexError:
        raise CollectionNonexistent(name)
    with open(path) as fd:
        return yaml.safe_load(fd)


def get_schema_for_doc(doc_id):
    """Get the schema for a particular document by its full ID."""
    (coll_name, _) = doc_id.split('/')
    ret = get_collection(coll_name)
    return ret


def get_stored_query(name):
    """Get AQL content for a specific stored query. Throws an error if nonexistent."""
    try:
        path = _find_paths(_CONF['spec_paths']['stored_queries'], name + '.yaml')[0]
    except IndexError:
        raise StoredQueryNonexistent(name)
    with open(path) as fd:
        return yaml.safe_load(fd)


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


class CollectionNonexistent(Exception):
    """Requested collection is not in the spec."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Collection does not exist.'


class StoredQueryNonexistent(Exception):
    """Requested stored query is not in the spec."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Stored query does not exist.'
