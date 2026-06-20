import boto3
import pytest
import json
import os
from botocore.stub import Stubber
from moto import mock_aws

boto_client = boto3.client


@pytest.fixture
def fake_aws():
    with mock_aws():
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
        ssm_client = boto3.client('ssm', region_name='eu-west-1')
        ssm_client.put_parameter(
            Name='/s3/bucket-name',
            Value='test-bucket',
            Type='String'
        )
        ssm_client.put_parameter(
            Name='/dynamo/table-name',
            Value='test-table',
            Type='String'
        )
        s3_client = boto3.client('s3', region_name='eu-west-1')
        s3_client.create_bucket(Bucket='test-bucket',
                                CreateBucketConfiguration={"LocationConstraint": "eu-west-1"})
        dynamo_client = boto3.client('dynamodb', region_name='eu-west-1')
        dynamo_client.create_table(
            TableName='test-table',
            KeySchema=[{
                'AttributeName': 'uuid',
                'KeyType': 'HASH'
            }],
            AttributeDefinitions=[{
                'AttributeName': 'uuid',
                'AttributeType': 'S'
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        fake_data = {
            "name": "test-name",
            "age": 42,
            "height": 111
        }
        s3_client.put_object(Bucket='test-bucket',
                             Key='processing-uuid.json',
                             Body=json.dumps(fake_data))
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
        dynamo_client.put_item(
            TableName='test-table',
            Item={
                'uuid': {'S': 'processing-uuid'},
                'status': {'S': 'processing'}
            }
        )
        dynamo_client.put_item(
            TableName='test-table',
            Item={
                'uuid': {'S': 'nos3-uuid'},
                'status': {'S': 'processed'}
            }
        )
        dynamo_client.put_item(
            TableName='test-table',
            Item={
                'uuid': {'S': 'deleted-uuid'},
                'status': {'S': 'deleted'}
            }
        )
        yield


@pytest.fixture
def aws_stub():
    activated_stubbers = []

    def _create_stub(service_name):
        client = boto_client(service_name)
        stubber = Stubber(client)
        stubber.activate()
        activated_stubbers.append(stubber)
        return client, stubber
    yield _create_stub
    for stubber in activated_stubbers:
        stubber.deactivate()
