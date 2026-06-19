import logging
import json
import uuid
import boto3
from botocore.exceptions import ClientError
from jsonschema.exceptions import ValidationError
from base.response_creator import response_creator
from base.validate import validate_data


logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger('post_data')


def lambda_handler(event, context):
    data = event.get("body", None)
    if not data:
        return response_creator(400, 'Please provide some data to upload to S3.')

    try:
        data = json.loads(data)
    except Exception as e:
        logger.exception(str(e))
        return response_creator(400, 'Invalid JSON in request body.')
    with open('schema/schema.json', 'r') as f:
        schema = json.load(f)
    try:
        validate_data(data, schema)
    except ValidationError as e:
        logger.exception(str(e))
        return response_creator(400, 'Provided body does not match the JSON schema.')

    client_uuid = str(uuid.uuid4())
    ssm_client = boto3.client('ssm')
    try:
        bucket_name = ssm_client.get_parameter(Name='/s3/bucket-name')['Parameter']['Value']
        table_name = ssm_client.get_parameter(Name='/dynamo/table-name')['Parameter']['Value']
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal Systems Manager error.')
    s3_client = boto3.client('s3')
    dynamo_client = boto3.client('dynamodb')
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=client_uuid + '.json',
            Body=json.dumps(data)
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal S3 error.')

    try:
        dynamo_client.put_item(
            TableName=table_name,
            Item={
                'uuid': {'S': client_uuid},
                'status': {'S': 'processing'}
            }
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal DynamoDB error.')

    return response_creator(201, {'message': 'Data successfully uploaded!', 'uuid': client_uuid})
