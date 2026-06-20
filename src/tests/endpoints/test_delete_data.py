from unittest.mock import patch
import boto3
import pytest
from boto3 import client as original_boto3_client
from botocore.exceptions import ClientError
import json
from endpoints.delete_data import lambda_handler


def create_boto_client_side_effect(mock_map, original_client):
    def side_effect(service_name, *args, **kwargs):
        if service_name in mock_map:
            return mock_map[service_name]
        return original_client(service_name, *args, **kwargs)
    return side_effect


def test_delete_data_works(fake_aws):
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    event = {"path": "some-path/processed-uuid"}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 200
    assert response['body'] == json.dumps({"message": "Data successfully deleted!"})
    with pytest.raises(ClientError) as e:
        s3_client.head_object(
            Bucket='test-bucket',
            Key='processed-uuid.json'
        )
    assert 'Not Found' in str(e.value)
    dynamo_item = dynamo_client.get_item(
        TableName='test-table',
        Key={'uuid': {'S': 'processed-uuid'}}
    )['Item']
    assert dynamo_item['status']['S'] == 'deleted'


def test_delete_data_fails_during_processing(fake_aws):
    event = {'path': 'some-path/processing-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 403
    assert response['body'] == json.dumps({"message": "Data is currently being processed, "
                                           "please wait before trying to delete."})


def test_delete_data_fails_already_deleted(fake_aws):
    event = {'path': 'some-path/deleted-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 404
    assert response['body'] == json.dumps({"message": "Data for the specified UUID has already been deleted."})


def test_delete_data_fails_bad_uuid(fake_aws):
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


@patch('endpoints.delete_data.boto3.client')
def test_delete_data_fails_ssm_error(mock_boto_client, fake_aws, aws_stub):
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


@patch('endpoints.delete_data.boto3.client')
def test_delete_data_fails_s3_head_error(mock_boto_client, fake_aws, aws_stub):
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
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.delete_data.boto3.client')
def test_delete_data_fails_s3_delete_error(mock_boto_client, fake_aws, aws_stub):
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
    stubber.add_client_error('delete_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processed-uuid.json'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.delete_data.boto3.client')
def test_delete_data_fails_dynamodb_get_error(mock_boto_client, fake_aws, aws_stub):
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


@patch('endpoints.delete_data.boto3.client')
def test_delete_data_fails_dynamodb_delete_error(mock_boto_client, fake_aws, aws_stub):
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
                                              'ExpressionAttributeValues': {':new_status': {'S': 'deleted'}}},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {'path': 'some-path/processed-uuid'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})
