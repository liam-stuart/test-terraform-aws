from base.validate import validate_data
from jsonschema import ValidationError
import json
import os
import pytest

with open('schema/schema.json', 'r') as f:
    schema = json.load(f)


def test_schema_validation():
    fixtures = os.listdir('tests/fixtures')
    for fixture in fixtures:
        if 'invalid' in fixture:
            with open(f'tests/fixtures/{fixture}', 'r') as f:
                data = json.load(f)
            with pytest.raises(ValidationError):
                validate_data(data, schema)
        else:
            with open(f'tests/fixtures/{fixture}', 'r') as f:
                data = json.load(f)
            assert validate_data(data, schema) is None
