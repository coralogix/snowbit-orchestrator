import boto3
import json

client = boto3.client('secretsmanager')

# Retrieve secret value

resp = client.get_secret_value(
    SecretId='SlackSecrets'
)

slack_secrets = json.loads(resp['SecretString'])

print(slack_secrets)


# retrieve zendesk secrets

resp = client.get_secret_value(
    SecretId='ZendeskSecrets'
)

zendesk_secrets = json.loads(resp['SecretString'])

print(zendesk_secrets)