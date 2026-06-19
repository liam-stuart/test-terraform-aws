import logging
import os
import jwt
from jwt import PyJWKClient


logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger('authorise')

AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
API_AUDIENCE = os.environ.get('API_AUDIENCE')
ISSUER = f"https://{AUTH0_DOMAIN}/"
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)


def lambda_handler(event, context):
    resource = event.get('methodArn', '')
    token = event.get('authorizationToken', '').replace('Bearer', '').strip()
    if not token:
        logger.error('No token provided.')
        return generate_policy('unauthorised', 'Deny', resource)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=API_AUDIENCE,
            issuer=ISSUER
        )
        user_id = payload.get('sub')
        return generate_policy(user_id, 'Allow', resource)

    except jwt.ExpiredSignatureError:
        logger.error("Expired token submitted.")
    except jwt.InvalidTokenError:
        logger.error("Invalid token.")
    except Exception as e:
        logger.error(str(e))
    return generate_policy('unauthorised', 'Deny', resource)


def generate_policy(principal_id, effect, resource):
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    }
