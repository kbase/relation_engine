"""
Validate everything in this repo, such as syntax, structure, etc.
"""
import re
import os
import glob
import json
import jsonschema
from jsonschema.exceptions import ValidationError


def validate_json_schemas():
    """Validate the syntax of all the JSON schemas."""
    print('Validating JSON schemas..')
    names = {}
    for path in glob.iglob('schemas/**/*.json', recursive=True):
        name = os.path.basename(path)
        # Make sure collection is lower snake case
        if not re.match(r'^[a-z_]+.json$', name):
            print('Name must be lowercase, alphabetical, with underscores in ' + path)
            exit(1)
        # Check for any duplicate schema names
        if names.get(name):
            print('Duplicate schemas for name ' + name)
            exit(1)
        else:
            names[name] = True
        # Load and parse the schema data as a python dict
        with open(path, 'r') as fd:
            try:
                schema = json.load(fd)
            except Exception as err:
                print('=' * 80)
                print('Unable to parse json in ' + path)
                print(str(err))
                exit(1)
        # Make sure it can be used as a JSON schema
        try:
            jsonschema.validate({}, schema)
        except ValidationError:
            pass
        except Exception as err:
            print('=' * 80)
            print('Unable to load schema in ' + path)
            print(str(err))
            exit(1)
        # All schemas must be object types
        if schema['type'] != 'object':
            print('Schemas must be an object. Schema in %s is not an object.' % path)
            exit(1)
        required = schema.get('required', [])
        # Edges must require _from and _to while vertices must require _key
        if '/edges/' in path and ('_from' not in required or '_to' not in required):
            print('Edge schemas must require _from and _to attributes in ' + path)
            exit(1)
        elif '/vertices/' in path and '_key' not in required:
            print('Vertex schemas must require the _key attribute in ' + path)
            exit(1)
    print('..all valid.')


def validate_aql_syntax():
    """Validate the syntax of all the queries."""
    # TODO check AQL syntax. Unsure how to do this without connecting to a running arango server :/
    print('Validating AQL queries..')
    names = {}
    for path in glob.iglob('views/**/*.aql', recursive=True):
        name = os.path.basename(path)
        if names.get(name):
            print('Duplicate queries named ' + name)
            exit(1)
        else:
            names[name] = True
    print('..all valid.')


if __name__ == '__main__':
    validate_json_schemas()
    validate_aql_syntax()
