"""
Utilities for loading views, schemas, and migrations from the spec.
"""
import os
import json
import subprocess  # nosec

_spec_path = os.environ.get('SPEC_PATH', '/spec')


def get_schema_names():
    """Return a list of all schema names."""
    git_pull()
    schema_path = os.path.join(_spec_path, 'schemas')
    return _get_file_names(schema_path, '.json')


def get_view_names():
    """Return a list of all view names."""
    git_pull()
    view_path = os.path.join(_spec_path, 'views')
    return _get_file_names(view_path, '.aql')


def get_view_content(name):
    """Return the AQL source code for a view."""
    view_names = get_view_names()
    if name not in view_names:
        raise ViewNonexistent(name, view_names)
    view_path = os.path.join(_spec_path, 'views', name + '.aql')
    print('name', name)
    print('view_path', view_path)
    with open(view_path, 'r') as fd:
        return fd.read()


def get_schema_as_dict(name):
    """Return a particular JSON schema as a python dict."""
    schema_names = get_schema_names()
    if name not in schema_names:
        raise SchemaNonexistent(name, schema_names)
    schema_path = os.path.join(_spec_path, 'schemas', name + '.json')
    with open(schema_path, 'r') as fd:
        return json.loads(fd.read())


def git_pull():
    """Git pull the spec repo to get any updates."""
    output = subprocess.check_output(['git', '-C', _spec_path, 'pull'])  # nosec
    print('git pull output', output)
    return output


def _get_file_names(dir_path, target_extension):
    """Get a list of file basenames in a certain directory with a certain extension."""
    names = []
    for name in os.listdir(dir_path):
        filename, extension = os.path.splitext(name)
        if extension == target_extension:
            names.append(filename)
    return names


class ViewNonexistent(Exception):
    """Requested view is not in the spec."""

    def __init__(self, name, available):
        self.name = name
        self.available = available

    def __str__(self):
        return 'View does not exist.'


class SchemaNonexistent(Exception):
    """Requested schema is not in the spec."""

    def __init__(self, name, available):
        self.name = name
        self.available = available

    def __str__(self):
        return 'Schema does not exist.'
