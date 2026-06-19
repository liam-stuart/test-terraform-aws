from jsonschema.exceptions import ValidationError
from jsonschema import validate, Draft202012Validator


def validate_data(data, schema):
    try:
        validate(data, schema, Draft202012Validator)
    except ValidationError as e:
        raise e
