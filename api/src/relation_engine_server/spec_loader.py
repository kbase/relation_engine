"""
Utilities for loading views, schemas, and migrations from the spec.
"""
import glob
import os
import json
import subprocess  # nosec

from . import arango_client

_spec_dir = os.environ.get('SPEC_PATH', '/spec')
_view_dir = os.path.join(_spec_dir, 'views')
_schema_dir = os.path.join(_spec_dir, 'schemas')
_vertex_dir = os.path.join(_schema_dir, 'vertices')
_edge_dir = os.path.join(_schema_dir, 'edges')


def get_schema_names():
    """Return a dict of vertex and edge base names."""
    return {
        'vertices': [
            _get_file_name(path)
            for path in _find_paths(_vertex_dir, '*.json')
        ],
        'edges': [
            _get_file_name(path)
            for path in _find_paths(_edge_dir, '*.json')
        ]
    }


def get_view_names():
    """Return an array of all view base names."""
    return [
        _get_file_name(path)
        for path in _find_paths(_view_dir, '*.aql')
    ]


def get_schema(name):
    """Get JSON content for a specific schema. Throws an error if nonexistent."""
    try:
        path = _find_paths(_schema_dir, name + '.json')[0]
    except IndexError:
        raise SchemaNonexistent(name)
    with open(path, 'r', encoding='utf8') as fd:
        return json.load(fd)


def get_view(name):
    """Get AQL content for a specific view. Throws an error if nonexistent."""
    try:
        path = _find_paths(_view_dir, name + '.aql')[0]
    except IndexError:
        raise ViewNonexistent(name)
    with open(path, 'r', encoding='utf8') as fd:
        return fd.read()


def git_pull():
    """Git pull the spec repo to get any updates."""
    # This always git-pulls no matter what. We may want to throttle or change this in the future.
    subprocess.check_output(['git', '-C', _spec_dir, 'checkout', 'master'])
    subprocess.check_output(['git', '-C', _spec_dir, 'fetch', 'origin'])
    subprocess.check_output(['git', '-C', _spec_dir, 'merge', 'origin/master'])
    # Initialize any collections
    arango_client.init_collections(get_schema_names())


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


class ViewNonexistent(Exception):
    """Requested view is not in the spec."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'View does not exist.'


class SchemaNonexistent(Exception):
    """Requested schema is not in the spec."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Schema does not exist.'
