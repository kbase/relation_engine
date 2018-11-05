"""
Utilities for loading views, schemas, and migrations from the spec.
"""
import glob
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


def get_view_content(names):
    """Return the AQL source code for a view."""
    views = {}
    view_names = get_view_names()
    for name in names:
        if name not in view_names:
            raise ViewNonexistent(name, view_names)
        view_path = os.path.join(_spec_path, 'views', name + '.aql')
        with open(view_path, 'r') as fd:
            views[name] = fd.read()
    return views


def get_schema_dicts(names):
    """Return a particular JSON schema as a python dict."""
    schemas = {}
    schema_names = get_schema_names()
    for name in names:
        if name not in schema_names:
            raise SchemaNonexistent(name, schema_names)
        schema_path = glob.glob(os.path.join(_spec_path, 'schemas', '**', name + '.json'),
                                recursive=True)[0]
        with open(schema_path, 'r') as fd:
            schemas[name] = json.loads(fd.read())
    return schemas


def git_pull():
    """Git pull the spec repo to get any updates."""
    output = subprocess.check_output(['git', '-C', _spec_path, 'rev-list', 'HEAD..origin/master', '--count'])  # nosec
    change_count = int(output.strip())
    if change_count > 0:
        output = subprocess.check_output(['git', '-C', _spec_path, 'pull'])  # nosec
        print('git pull output', output)
    return output


def _get_file_names(dir_path, target_extension):
    """Get a list of file basenames in all subdirectory of a dir_path with a certain extension."""
    return [os.path.basename(p) for p in glob.iglob(os.path.join(dir_path, '**', '*' + target_extension), recursive=True)]


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
