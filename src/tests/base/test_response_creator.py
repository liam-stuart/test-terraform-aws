import json
import pytest
from base.response_creator import response_creator


def test_response_success():
    expected_result = {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({"message": "Success!"})
    }
    response = response_creator(200, {"message": "Success!"})
    assert response == expected_result


def test_response_failure():
    expected_result = {
        'statusCode': 400,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({"message": "Failure."})
    }
    response = response_creator(400, 'Failure.')
    assert response == expected_result


def test_response_invalid_status_code():
    with pytest.raises(ValueError):
        response_creator(100, 'Invalid status code.')
