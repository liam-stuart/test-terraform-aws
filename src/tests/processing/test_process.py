from unittest.mock import patch
import boto3
from boto3 import client as original_boto3_client
import json
import io
from processing.process import lambda_handler


def create_boto_client_side_effect(mock_map, original_client):
    def side_effect(service_name, *args, **kwargs):
        if service_name in mock_map:
            return mock_map[service_name]
        return original_client(service_name, *args, **kwargs)
    return side_effect


def test_process_works(fake_aws):
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    event = {
        'Records': [{'dynamodb': {'NewImage': {
            "uuid": {"S": "processing-uuid"},
            "status": {"S": "processing"}
        }}}]
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 200
    assert response['body'] == json.dumps({"message": 'Data for UUID processing-uuid successfully processed!'})
    expected_result = {
        "name": "TEST-NAME",
        "age": 42,
        "height": "3ft, 7.7in"
    }
    processed_data = s3_client.get_object(
        Bucket='test-bucket',
        Key='processing-uuid.json'
    )
    data = json.loads(processed_data['Body'].read())
    assert data == expected_result
    dynamo_item = dynamo_client.get_item(
        TableName='test-table',
        Key={'uuid': {'S': 'processing-uuid'}}
    )['Item']
    assert dynamo_item['status']['S'] == 'processed'


@patch('processing.process.boto3.client')
def test_process_fails_ssm_error(mock_boto_client, fake_aws, aws_stub):
    ssm_client, stubber = aws_stub('ssm')
    mock_boto_client.return_value = ssm_client
    stubber.add_client_error('get_parameter',
                             expected_params={'Name': '/s3/bucket-name'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'Records': [{'dynamodb': {'NewImage': {
            "uuid": {"S": "processing-uuid"},
            "status": {"S": "processing"}
        }}}]
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal Systems Manager error."})


@patch('processing.process.boto3.client')
def test_process_fails_s3_get_error(mock_boto_client, fake_aws, aws_stub):
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_client_error('get_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processing-uuid.json'},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'Records': [{'dynamodb': {'NewImage': {
            "uuid": {"S": "processing-uuid"},
            "status": {"S": "processing"}
        }}}]
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('processing.process.boto3.client')
def test_process_fails_s3_put_error(mock_boto_client, fake_aws, aws_stub):
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    old_data = {
        "name": "test-name",
        "age": 42,
        "height": 111
    }
    mock_stream = io.BytesIO(json.dumps(old_data).encode('utf-8'))
    new_data = {
        "name": "TEST-NAME",
        "age": 42,
        "height": "3ft, 7.7in"
    }
    stubber.add_response('get_object',
                         expected_params={'Bucket': 'test-bucket',
                                          'Key': 'processing-uuid.json'},
                         service_response={'Body': mock_stream}
                         )
    stubber.add_client_error('put_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'processing-uuid.json',
                                              'Body': json.dumps(new_data)},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'Records': [{'dynamodb': {'NewImage': {
            "uuid": {"S": "processing-uuid"},
            "status": {"S": "processing"}
        }}}]
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('processing.process.boto3.client')
def test_process_fails_dynamodb_update_error(mock_boto_client, fake_aws, aws_stub):
    dynamo_client, stubber = aws_stub('dynamodb')
    mock_services = {'dynamodb': dynamo_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    stubber.add_client_error('update_item',
                             expected_params={'TableName': 'test-table',
                                              'Key': {'uuid': {'S': 'processing-uuid'}},
                                              'UpdateExpression': 'SET #status = :new_status',
                                              'ExpressionAttributeNames': {'#status': 'status'},
                                              'ExpressionAttributeValues': {':new_status': {'S': 'processed'}}},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {
        'Records': [{'dynamodb': {'NewImage': {
            "uuid": {"S": "processing-uuid"},
            "status": {"S": "processing"}
        }}}]
    }
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})
