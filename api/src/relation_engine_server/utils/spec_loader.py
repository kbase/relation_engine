"""
Utilities for loading views, schemas, and migrations from the spec.
"""
import glob
import os
import json

from .config import get_config


def get_schema_names():
    """Return a dict of vertex and edge base names."""
    config = get_config()
    return {
        'vertices': [
            _get_file_name(path)
            for path in _find_paths(config['spec_paths']['vertices'], '*.json')
        ],
        'edges': [
            _get_file_name(path)
            for path in _find_paths(config['spec_paths']['edges'], '*.json')
        ]
    }


def get_view_names():
    """Return an array of all view base names."""
    config = get_config()
    return [
        _get_file_name(path)
        for path in _find_paths(config['spec_paths']['views'], '*.aql')
    ]


def get_schema(name):
    """Get JSON content for a specific schema. Throws an error if nonexistent."""
    config = get_config()
    try:
        path = _find_paths(config['spec_paths']['schemas'], name + '.json')[0]
    except IndexError:
        raise SchemaNonexistent(name)
    with open(path, 'r', encoding='utf8') as fd:
        return json.load(fd)


def get_view(name):
    """Get AQL content for a specific view. Throws an error if nonexistent."""
    config = get_config()
    try:
        path = _find_paths(config['spec_paths']['views'], name + '.aql')[0]
    except IndexError:
        raise ViewNonexistent(name)
    with open(path, 'r', encoding='utf8') as fd:
        return fd.read()


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
