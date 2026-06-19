from unittest.mock import patch
import boto3
from boto3 import client as original_boto3_client
import json
from endpoints.post_data import lambda_handler


def create_boto_client_side_effect(mock_map, original_client):
    def side_effect(service_name, *args, **kwargs):
        if service_name in mock_map:
            return mock_map[service_name]
        return original_client(service_name, *args, **kwargs)
    return side_effect


@patch('endpoints.post_data.uuid.uuid4')
def test_post_data_works(mock_uuid, fake_aws):
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    mock_uuid.return_value = 'test-uuid'
    posted_data = {
        "name": 'Liam',
        "age": 29,
        "height": 171
    }
    event = {"body": json.dumps(posted_data)}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 201
    assert response['body'] == json.dumps({"message": "Data successfully uploaded!",
                                           "uuid": "test-uuid"})
    s3_upload = s3_client.get_object(
        Bucket='test-bucket',
        Key='test-uuid.json'
    )
    dynamo_entry = dynamo_client.get_item(
        TableName='test-table',
        Key={"uuid": {"S": "test-uuid"}}
    )
    uploaded_data = json.loads(s3_upload['Body'].read())
    assert uploaded_data == posted_data
    assert dynamo_entry['Item']['status']['S'] == 'processing'


def test_post_data_fails_no_data():
    event = {"body": None}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Please provide some data to upload to S3."})


def test_post_data_fails_invalid_json():
    event = {"body": 'my-data-here'}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Invalid JSON in request body."})


def test_post_data_fails_schema_validation():
    posted_data = {
        "name": 'Liam',
        "age": 29
    }
    event = {"body": json.dumps(posted_data)}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 400
    assert response['body'] == json.dumps({"message": "Provided body does not match the JSON schema."})


@patch('endpoints.post_data.boto3.client')
def test_post_data_fails_ssm_error(mock_boto_client, fake_aws, aws_stub):
    ssm_client, stubber = aws_stub('ssm')
    mock_boto_client.return_value = ssm_client
    stubber.add_client_error('get_parameter',
                             expected_params={'Name': '/s3/bucket-name'},
                             service_error_code='ClientError',
                             http_status_code=500)
    posted_data = {
        "name": 'Liam',
        "age": 29,
        "height": 171
    }
    event = {"body": json.dumps(posted_data)}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal Systems Manager error."})


@patch('endpoints.post_data.uuid.uuid4')
@patch('endpoints.post_data.boto3.client')
def test_post_data_fails_s3_error(mock_boto_client, mock_uuid, fake_aws, aws_stub):
    s3_client, stubber = aws_stub('s3')
    mock_services = {'s3': s3_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    mock_uuid.return_value = 'test-uuid'
    posted_data = {
        "name": 'Liam',
        "age": 29,
        "height": 171
    }
    stubber.add_client_error('put_object',
                             expected_params={'Bucket': 'test-bucket',
                                              'Key': 'test-uuid.json',
                                              'Body': json.dumps(posted_data)},
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {"body": json.dumps(posted_data)}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal S3 error."})


@patch('endpoints.post_data.uuid.uuid4')
@patch('endpoints.post_data.boto3.client')
def test_post_data_fails_dynamodb_error(mock_boto_client, mock_uuid, fake_aws, aws_stub):
    dynamo_client, stubber = aws_stub('dynamodb')
    mock_services = {'dynamodb': dynamo_client}
    mock_boto_client.side_effect = create_boto_client_side_effect(
        mock_map=mock_services,
        original_client=original_boto3_client
    )
    mock_uuid.return_value = 'test-uuid'
    posted_data = {
        "name": 'Liam',
        "age": 29,
        "height": 171
    }
    stubber.add_client_error('put_item',
                             expected_params={'TableName': 'test-table',
                                              'Item': {'uuid': {'S': 'test-uuid'},
                                                       'status': {'S': 'processing'}
                                                       }
                                              },
                             service_error_code='ClientError',
                             http_status_code=500)
    event = {"body": json.dumps(posted_data)}
    context = {}
    response = lambda_handler(event, context)
    assert response['statusCode'] == 500
    assert response['body'] == json.dumps({"message": "Internal DynamoDB error."})
