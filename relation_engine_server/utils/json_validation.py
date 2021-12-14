"""
JSON Schema validation

See the docs on adding default values: https://python-jsonschema.readthedocs.io/en/stable/faq/

Example usage:

    schema = {'properties': {'foo': {'default': 'bar'}}}
    obj = {}
    Validator(schema).validate(obj)
    assert obj == {'foo': 'bar'}
"""
from jsonschema import validators, Draft7Validator, FormatChecker, RefResolver
from jsonschema.exceptions import ValidationError
from jsonpointer import resolve_pointer
import yaml
import json
import requests


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


def get_schema_validator(schema=None, schema_file=None, validate_at=""):
    """
    Get a validator for the supplied schema

    :param schema:      (dict)    the schema as a data structure
    :param schema_file: (string)  path to the schema file (json or yaml format)

    :param validate_at: (string)  where in the data structure the schema to validate against
                                  is located, in JSON pointer syntax
                                  defaults to the root of the schema object if not set

    only one of `schema` and `schema_file` should be supplied

    :return:
    validator  (Validator)  jsonschema validator instance

    """

    if (
        schema == schema_file
        and schema is None
        or schema is not None
        and schema_file is not None
    ):
        raise ValueError("Please supply either a schema or a schema file path")

    # schema to validate against
    if schema is None:
        schema = _load_json_schema(schema_file)

    # get the appropriate location in the schema
    validation_schema = resolve_pointer(schema, validate_at)

    if schema_file:
        resolver = RefResolver(schema_file, schema)
    else:
        resolver = RefResolver.from_schema(schema)

    return Validator(
        validation_schema, format_checker=FormatChecker(), resolver=resolver
    )


def run_validator(
    schema=None,
    schema_file=None,
    validate_at="",
    data=None,
    data_file=None,
    nicer_errors=False,
):
    """
    Validate data against a schema, filling in defaults if appropriate

    :param schema:      (dict)    the schema as a data structure
    :param schema_file: (string)  path to the schema file (json or yaml format)

    :param validate_at: (string)  where in the data structure the schema to validate against
                                  is located, in JSON pointer syntax
                                  defaults to the root of the schema object if not set

    :param data:        (*)       data to validate
    :param data_file:   (string)  path to file containing data (json or yaml format)


    only one of `schema` and `schema_file` should be supplied

    only one of `data` and `data_file` should be supplied

    :return:
    data                (*)       validated data

    """

    validator = get_schema_validator(schema, schema_file, validate_at)

    if data is None and data_file is None or data is not None and data_file is not None:
        raise ValueError("Please supply either a data structure or a data file path")

    # data to validate
    if data is None:
        data = _load_json_schema(data_file)

    if validator.is_valid(data):
        return data

    if not nicer_errors:
        # this will throw a ValidationError
        validator.validate(data)

    err_msg = "".join(
        e.message + "\n" for e in sorted(validator.iter_errors(data), key=str)
    )

    raise ValidationError(err_msg)


def _load_json_schema(file):
    """Loads the given schema file"""

    with open(file) as fd:
        if file.endswith(".yaml") or file.endswith(".yml"):
            return yaml.safe_load(fd)

        if file.endswith(".json"):
            return json.load(fd)

        raise TypeError("Unknown file type encountered: " + file)

