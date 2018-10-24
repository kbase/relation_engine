import os
import json
import jsonschema


def get_schema_names():
    current_dir = os.path.dirname(__file__)
    schema_names = []
    for file_name in os.listdir(current_dir):
        (basename, ext) = os.path.splitext(file_name)
        if ext == '.json':
            schema_names.append(basename)
    return schema_names


def get_schema_as_dict(schema_name):
    """Parse a schema into a python dictionary."""
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, schema_name + '.json')
    if not os.path.isfile(file_path):
        raise SchemaNonexistent(schema_name)
    with open(file_path, 'r') as fd:
        return json.loads(fd.read())


def validate_data_against_schema(schema, data):
    """Given a parsed JSON schema and some python data, validate the data structure against the schema."""
    jsonschema.validate(data, schema)


class SchemaNonexistent(Exception):
    """Schema that we tried to fetch by name does not exist."""

    def __init__(self, schema_name):
        self.schema_name = schema_name

    def __str__(self):
        return 'Schema does not exist %s. Available schemas are: %s' % (self.schema_name, str(get_schema_names()))
