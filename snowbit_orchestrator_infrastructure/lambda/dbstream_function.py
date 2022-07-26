import json
import requests
import boto3
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, User

secrets_client = boto3.client('secretsmanager')

zendesk_resp = secrets_client.get_secret_value(
    SecretId='ZendeskSecrets2'
)

zendesk_secrets = json.loads(zendesk_resp['SecretString'])

credentials = {'token': zendesk_secrets['token'], 'email': zendesk_secrets['email'],
               'subdomain': zendesk_secrets['subdomain']}


zenpy_client = Zenpy(**credentials)

def handler(event, context):
    try:
        for record in event['Records']:
            if record['eventName'] == 'INSERT':
                handle_insert(record)
            elif record['eventName'] == 'REMOVE':
                handle_remove(record)
    except Exception as e:
        print(e)
        

def handle_insert(record):
    print('HANDLING INSERT EVENT')
    newImage = record['dynamodb']['NewImage']
    timestamp = newImage['timestamp']['S']
    print('New ticket added with Id = {}'.format(timestamp))
    
def handle_remove(record):
    print('HANDLING REMOVE EVENT')
    oldImage = record['dynamodb']['OldImage']
    print(record['dynamodb'])
    timestamp = oldImage['timestamp']['S']
    current_status = oldImage['current_status']['S']
    if current_status == "awaiting response":
        user = credentials['email'] + '/token'
        headers = {'content-type': 'application/json'}
        url = 'https://antstackhelp.zendesk.com/api/v2/ticket_fields'
        data = requests.get(
            url,
            auth=(user, credentials['token']),
            headers=headers
        ).json()['ticket_fields']

        ticket = zenpy_client.tickets(id=oldImage['zen_ticket_id']['N'])

        for i in data:
            if i['title'] == 'slack_action':
                ticket.custom_fields.append(CustomField(id=i['id'], value="not_acknowledged"))

        zenpy_client.tickets.update(ticket)
        print("This ticket with timestamp {} has not been acknowledged despite meeting its TTL".format(timestamp))
        # update slack_action in zendesk to no action - expired from here!
    print('Deleted = {}'.format(oldImage['timestamp']['S']))



