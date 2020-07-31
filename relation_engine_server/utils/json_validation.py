"""
JSON Schema validation

See the docs on adding default values: https://python-jsonschema.readthedocs.io/en/stable/faq/

Example usage:

    schema = {'properties': {'foo': {'default': 'bar'}}}
    obj = {}
    Validator(schema).validate(obj)
    assert obj == {'foo': 'bar'}
"""
from jsonschema import validators, Draft7Validator


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
