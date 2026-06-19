from unittest.mock import patch
import boto3
from boto3 import client as original_boto3_client
import json
from endpoints.update_data import lambda_handler


def create_boto_client_side_effect(mock_map, original_client):
    def side_effect(service_name, *args, **kwargs):
        if service_name in mock_map:
            return mock_map[service_name]
        return original_client(service_name, *args, **kwargs)
    return side_effect


def test_update_data_works(fake_aws):
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    event = {
        "path": "some-path/processed-uuid",
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 200
    assert response['body'] == json.dumps({"message": "Data successfully updated!"})
    s3_upload = s3_client.get_object(
        Bucket='test-bucket',
        Key='processed-uuid.json'
    )
    dynamo_entry = dynamo_client.get_item(
        TableName='test-table',
        Key={"uuid": {"S": "processed-uuid"}}
    )
    uploaded_data = json.loads(s3_upload['Body'].read())
    assert uploaded_data == update_data
    assert dynamo_entry['Item']['status']['S'] == 'processing'


def test_update_data_fails_no_data(fake_aws):
    event = {
        "path": "some-path/processed-uuid",
        "body": None
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Please provide some data to update the existing UUID."})


def test_update_data_fails_bad_data(fake_aws):
    event = {
        "path": "some-path/processed-uuid",
        "body": 'bad-data'
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Invalid JSON in request body."})


def test_update_data_fails_schema_validation(fake_aws):
    update_data = {
        "name": "Laim",
        "age": 92
    }
    event = {
        "path": "some-path/processed-uuid",
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Provided body does not match the JSON schema."})


def test_update_data_fails_during_processing(fake_aws):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    event = {
        "path": "some-path/processing-uuid",
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 403
    assert response['body'] == json.dumps({"message": "Data is currently being processed, "
                                                      "please wait before trying to update."})


def test_update_data_fails_bad_uuid(fake_aws):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    event = {
        "path": "some-path/bad-uuid",
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 404
    assert response['body'] == json.dumps({"message": "No table entry found with specified UUID."})


def test_update_data_fails_missing_s3(fake_aws):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    event = {
        "path": "some-path/nos3-uuid",
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 404
    assert response['body'] == json.dumps({"message": "No data exists in S3 with the provided UUID."})


@patch('endpoints.update_data.boto3.client')
def test_update_data_fails_ssm_error(mock_boto_client, fake_aws, aws_stub):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    ssm_client, stubber = aws_stub('ssm')
    mock_boto_client.return_value = ssm_client
    stubber.add_client_error('get_parameter',
                             expected_params={'Name': '/s3/bucket-name'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'path': 'some-path/processed-uuid',
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal Systems Manager error."})


@patch('endpoints.update_data.boto3.client')
def test_update_data_fails_s3_head_error(mock_boto_client, fake_aws, aws_stub):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_client_error('head_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processed-uuid.json'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'path': 'some-path/processed-uuid',
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.update_data.boto3.client')
def test_update_data_fails_s3_put_error(mock_boto_client, fake_aws, aws_stub):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_response('head_object',
                         expected_params={'Bucket': 'test-bucket',
                                          'Key': 'processed-uuid.json'},
                         service_response={'ContentLength': 123,
                                           'ContentType': 'application/json'}
                         )
    stubber.add_client_error('put_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processed-uuid.json',
                                              'Body': json.dumps(update_data)},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'path': 'some-path/processed-uuid',
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.update_data.boto3.client')
def test_update_data_fails_dynamodb_get_error(mock_boto_client, fake_aws, aws_stub):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    dynamo_client, stubber = aws_stub('dynamodb')
    mock_services = {'dynamodb': dynamo_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_client_error('get_item',
                             expected_params={'TableName': 'test-table',
                                              'Key': {'uuid': {'S': 'processed-uuid'}}
                                              },
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'path': 'some-path/processed-uuid',
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})


@patch('endpoints.update_data.boto3.client')
def test_update_data_fails_dynamodb_update_error(mock_boto_client, fake_aws, aws_stub):
    update_data = {
        "name": "Laim",
        "age": 92,
        "height": 432
    }
    dynamo_client, stubber = aws_stub('dynamodb')
    mock_services = {'dynamodb': dynamo_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_response('get_item',
                         expected_params={'TableName': 'test-table',
                                          'Key': {'uuid': {'S': 'processed-uuid'}}},
                         service_response={'Item': {'uuid': {'S': 'processed-uuid'},
                                           'status': {'S': 'processed'}}}
                         )
    stubber.add_client_error('update_item',
                             expected_params={'TableName': 'test-table',
                                              'Key': {'uuid': {'S': 'processed-uuid'}},
                                              'UpdateExpression': 'SET #status = :new_status',
                                              'ExpressionAttributeNames': {'#status': 'status'},
                                              'ExpressionAttributeValues': {':new_status': {'S': 'processing'}}},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'path': 'some-path/processed-uuid',
        "body": json.dumps(update_data)
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})
