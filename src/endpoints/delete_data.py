import logging
import boto3
from botocore.exceptions import ClientError
from base.response_creator import response_creator


logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger('delete_data')


def lambda_handler(event, context):
    path = event.get("path", "")
    uuid = path.split('/')[-1]
    ssm_client = boto3.client('ssm')
    try:
        bucket_name = ssm_client.get_parameter(Name='/s3/bucket-name')['Parameter']['Value']
        table_name = ssm_client.get_parameter(Name='/dynamo/table-name')['Parameter']['Value']
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal Systems Manager error.')

    dynamo_client = boto3.client('dynamodb')
    try:
        response = dynamo_client.get_item(
            TableName=table_name,
            Key={
                'uuid': {'S': uuid}
            }
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal DynamoDB error.')

    response = response.get('Item', {})
    status = response.get('status', {})
    if status.get('S', None) == 'processing':
        return response_creator(403, 'Data is currently being processed, '
                                     'please wait before trying to delete.')
    elif status.get('S', None) is None:
        return response_creator(404, 'No table entry found with specified UUID.')

    s3_client = boto3.client('s3')
    try:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=uuid + '.json'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            status_code = 404
            message = 'No data exists in S3 with the provided UUID.'
        else:
            status_code = 500
            message = 'Internal S3 error.'
        logger.exception(str(e))
        return response_creator(status_code, message)

    try:
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=uuid + '.json'
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal S3 error.')

    try:
        dynamo_client.update_item(
            TableName=table_name,
            Key={
                'uuid': {'S': uuid}
            },
            UpdateExpression='SET #status = :new_status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':new_status': {'S': 'deleted'}}
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal DynamoDB error.')

    return response_creator(200, {'message': 'Data successfully deleted!'})
