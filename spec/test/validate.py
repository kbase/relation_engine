"""
Validate everything in this repo, such as syntax, structure, etc.
"""
import os
import glob
import yaml
import jsonschema
from jsonschema.exceptions import ValidationError

# JSON schema for vertex and edge collection schemas found in /schema
schema_schema = {
    "type": "object",
    "required": ["name", "type", "schema"],
    "properties": {
        "name": {
            'title': 'Collection name',
            "type": "string",
            "format": r'^[a-z_]+$'
        },
        'type': {
            'type': 'string',
            'enum': ['vertex', 'edge']
        },
        'schema': {'type': 'object'}
    }
}


def validate_json_schemas():
    """Validate the syntax of all the JSON schemas."""
    print('Validating JSON schemas..')
    names = {}  # type: dict
    for path in glob.iglob('schemas/**/*.yaml', recursive=True):
        name = os.path.basename(path)
        print(f'  validating {name}..')
        with open(path) as fd:
            data = yaml.safe_load(fd)
        jsonschema.validate(data, schema_schema)
        # Check for any duplicate schema names
        if names.get(name):
            print('Duplicate schemas for name ' + name)
            exit(1)
        else:
            names[name] = True
        # Make sure it can be used as a JSON schema
        try:
            jsonschema.validate({}, data['schema'])
        except ValidationError:
            pass
        except Exception as err:
            print('=' * 80)
            print('Unable to load schema in ' + path)
            print(str(err))
            exit(1)
        # All schemas must be object types
        if data['schema']['type'] != 'object':
            print('Schemas must be an object. Schema in %s is not an object.' % path)
            exit(1)
        required = data['schema'].get('required', [])
        # Edges must require _from and _to while vertices must require _key
        if data['type'] == 'edge' and ('_from' not in required or '_to' not in required):
            print('Edge schemas must require _from and _to attributes in ' + path)
            exit(1)
        elif data['type'] == 'vertex' and '_key' not in required:
            print('Vertex schemas must require the _key attribute in ' + path)
            exit(1)
        print(f'✓ {name} is valid.')
    print('..all valid.')


def validate_aql_syntax():
    """Validate the syntax of all the queries."""
    # TODO check AQL syntax. Unsure how to do this without connecting to a running arango server :/
    print('Validating AQL queries..')
    names = {}  # type: dict
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
