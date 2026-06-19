from unittest.mock import patch, MagicMock
from jwt import ExpiredSignatureError, InvalidTokenError
from base.authorise import lambda_handler, jwks_client


@patch.object(jwks_client, 'get_signing_key_from_jwt')
@patch('base.authorise.jwt.decode')
def test_authorise_success(mock_decode_result, mock_get_signing_key):
    mock_signing_key = MagicMock()
    mock_signing_key.key = 'mock-key'
    mock_get_signing_key.return_value = mock_signing_key
    mock_decode_result.return_value = {
        'sub': 'mock-client'
    }
    event = {'authorizationToken': 'Bearer test-token'}
    context = {}
    response = lambda_handler(event, context)
    assert response['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert response['principalId'] == 'mock-client'


def test_authorise_fail_missing_token(caplog):
    event = {}
    context = {}
    response = lambda_handler(event, context)
    assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert 'No token provided.' in caplog.text


@patch.object(jwks_client, 'get_signing_key_from_jwt')
@patch('base.authorise.jwt.decode')
def test_authorise_fail_expired_signature(mock_decode_result, mock_get_signing_key, caplog):
    mock_signing_key = MagicMock()
    mock_signing_key.key = 'mock-key'
    mock_get_signing_key.return_value = mock_signing_key
    mock_decode_result.side_effect = ExpiredSignatureError
    event = {'authorizationToken': 'Bearer test-token'}
    context = {}
    response = lambda_handler(event, context)
    assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert 'Expired token submitted.' in caplog.text


@patch.object(jwks_client, 'get_signing_key_from_jwt')
@patch('base.authorise.jwt.decode')
def test_authorise_fail_invalid_token(mock_decode_result, mock_get_signing_key, caplog):
    mock_signing_key = MagicMock()
    mock_signing_key.key = 'mock-key'
    mock_get_signing_key.return_value = mock_signing_key
    mock_decode_result.side_effect = InvalidTokenError
    event = {'authorizationToken': 'Bearer test-token'}
    context = {}
    response = lambda_handler(event, context)
    assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert 'Invalid token.' in caplog.text


@patch.object(jwks_client, 'get_signing_key_from_jwt')
@patch('base.authorise.jwt.decode')
def test_authorise_fail_generic_exception(mock_decode_result, mock_get_signing_key, caplog):
    mock_signing_key = MagicMock()
    mock_signing_key.key = 'mock-key'
    mock_get_signing_key.return_value = mock_signing_key
    mock_decode_result.side_effect = Exception('Random error.')
    event = {'authorizationToken': 'Bearer test-token'}
    context = {}
    response = lambda_handler(event, context)
    assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert 'Random error.' in caplog.text
