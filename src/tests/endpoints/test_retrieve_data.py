from unittest.mock import patch
import boto3
from boto3 import client as original_boto3_client
import json
from endpoints.retrieve_data import lambda_handler


def create_boto_client_side_effect(mock_map, original_client):
    def side_effect(service_name, *args, **kwargs):
        if service_name in mock_map:
            return mock_map[service_name]
        return original_client(service_name, *args, **kwargs)
    return side_effect


def test_retrieve_data_works(fake_aws):
    fake_data = {
        "name": "test-name",
        "age": 42,
        "height": 111
    }
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    s3_client.put_object(Bucket='test-bucket',
                         Key='processed-uuid.json',
                         Body=json.dumps(fake_data))
    dynamo_client.put_item(
        TableName='test-table',
        Item={
            'uuid': {'S': 'processed-uuid'},
            'status': {'S': 'processed'}
        }
    )
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 200
    assert response['body'] == json.dumps(fake_data)


def test_retrieve_data_fails_during_processing(fake_aws):
    event = {'path': 'some-path/processing-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 403
    assert response['body'] == json.dumps({"message": "Data is currently being processed, "
                                           "please wait before trying to retrieve."})


def test_retrieve_data_fails_bad_uuid(fake_aws):
    event = {'path': 'some-path/bad-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 404
    assert response['body'] == json.dumps({"message": "No table entry found with specified UUID."})


def test_retrieve_data_fails_missing_s3(fake_aws):
    event = {'path': 'some-path/nos3-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 404
    assert response['body'] == json.dumps({"message": "No data exists in S3 with the provided UUID."})


@patch('endpoints.retrieve_data.boto3.client')
def test_retrieve_data_fails_ssm_error(mock_boto_client, fake_aws, aws_stub):
    ssm_client, stubber = aws_stub('ssm')
    mock_boto_client.return_value = ssm_client
    stubber.add_client_error('get_parameter',
                             expected_params={'Name': '/s3/bucket-name'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal Systems Manager error."})


@patch('endpoints.retrieve_data.boto3.client')
def test_retrieve_data_fails_s3_error(mock_boto_client, fake_aws, aws_stub):
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_client_error('get_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processed-uuid.json'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.retrieve_data.boto3.client')
def test_retrieve_data_fails_dynamodb_error(mock_boto_client, fake_aws, aws_stub):
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
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})
