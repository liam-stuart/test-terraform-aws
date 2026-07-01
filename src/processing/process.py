import logging
import json
import boto3
from botocore.exceptions import ClientError
from base.response_creator import response_creator


logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger('process_data')


def lambda_handler(event, context):
    record = event['Records'][0]['dynamodb']['NewImage']
    uuid = record['uuid']['S']
    ssm_client = boto3.client('ssm')
    try:
        bucket_name = ssm_client.get_parameter(Name='/s3/bucket-name')['Parameter']['Value']
        table_name = ssm_client.get_parameter(Name='/dynamo/table-name')['Parameter']['Value']
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal Systems Manager error.')

    s3_client = boto3.client('s3')
    try:
        data = s3_client.get_object(
            Bucket=bucket_name,
            Key=uuid + '.json'
        )
    except Exception as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal S3 error.')

    data = json.loads(data['Body'].read())
    old_name = data['name']
    new_name = old_name.upper()
    data['name'] = new_name
    height = data['height']
    inches = height / 2.54
    feet = int(inches // 12)
    res_inches = round(inches % 12, 2)
    format_height = f'{feet}ft, {res_inches}in'
    data['height'] = format_height

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=uuid + '.json',
            Body=json.dumps(data)
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal S3 error.')

    dynamo_client = boto3.client('dynamodb')
    try:
        dynamo_client.update_item(
            TableName=table_name,
            Key={
                'uuid': {'S': uuid}
            },
            UpdateExpression='SET #status = :new_status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':new_status': {'S': 'processed'}}
        )
    except ClientError as e:
        logger.exception(str(e))
        return response_creator(500, 'Internal DynamoDB error.')

    message = f'Data for UUID {uuid} successfully processed!'
    logger.info(message)
    return response_creator(200, {'message': message})
