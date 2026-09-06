import json


def response_creator(status_code, content):
    if status_code >= 400:
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': content})
        }
    elif status_code >= 200:
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(content)
        }
    else:
        raise ValueError('Invalid status code provided to response_creator.')
