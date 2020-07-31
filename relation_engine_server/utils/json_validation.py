"""
JSON Schema validation

See the docs on adding default values: https://python-jsonschema.readthedocs.io/en/stable/faq/

Example usage:

    schema = {'properties': {'foo': {'default': 'bar'}}}
    obj = {}
    Validator(schema).validate(obj)
    assert obj == {'foo': 'bar'}
"""
from jsonschema import validators, Draft7Validator, FormatChecker
import yaml
import json


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])
        for error in validate_properties(validator, properties, instance, schema):
            yield error
    return validators.extend(validator_class, {"properties": set_defaults})


Validator = extend_with_default(Draft7Validator)


def run_validator(schema=None, schema_file=None, data=None, data_file=None, validate_at=None):

    if schema is None and schema_file is None:
        raise ValueError("Please supply either a schema or a schema file path")

    if data is None and data_file is None:
        raise ValueError("Please supply either a data structure or a data file path")

    # data to validate
    if data_file:
        data = _load_json_schema(data_file)

    # schema to validate against
    if schema_file:
        schema = _load_json_schema(schema_file)

    if validate_at:
        schema = schema[validate_at[0]]

    Validator(schema, format_checker=FormatChecker()).validate(data)

    return data


def _load_json_schema(file):
    """ Loads the given schema file """

    with open(file) as fd:
        if file.endswith('.yaml') or file.endswith('.yml'):
            return yaml.safe_load(fd)

        if file.endswith('.json'):
            return json.load(fd)

        raise TypeError('Unknown file type encountered: ' + file)
