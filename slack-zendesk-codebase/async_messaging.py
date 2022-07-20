import asyncio
import boto3
import logging
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from zenpy import Zenpy
import requests
import json
from zenpy.lib.api_objects import Ticket, CustomField, User
from main import *
from time import *
import time
import toml

secrets_client = boto3.client('secretsmanager')

secrets_resp = secrets_client.get_secret_value(
    SecretId='SlackSecrets'
)

slack_secrets = json.loads(secrets_resp['SecretString'])

zendesk_resp = secrets_client.get_secret_value(
    SecretId='ZendeskSecrets2'
)

zendesk_secrets = json.loads(zendesk_resp['SecretString'])


input_file = "output.toml"

with open(input_file, "r") as toml_file:
    toml_data_dict = toml.load(toml_file)


logging.basicConfig(level=logging.DEBUG)

credentials = {'token': zendesk_secrets['token'], 'email': zendesk_secrets['email'],
               'subdomain': zendesk_secrets['subdomain']}


zenpy_client = Zenpy(**credentials)

SLACK_BOT_TOKEN = slack_secrets['SLACK_BOT_TOKEN']

SLACK_APP_TOKEN = slack_secrets['SLACK_APP_TOKEN']


dynamodb = boto3.resource('dynamodb')

dynamodb_client = boto3.client('dynamodb')


table = dynamodb.Table('InfratestcdkStack-TableCD117FA1-1S0N39VCN52J9')  # should change this using !Ref

app = AsyncApp(token=SLACK_BOT_TOKEN)


async def post_message_to_slack(process_json, slack_channel_handle_name, zen_ticket_id, customer_name):
    response = await app.client.chat_postMessage(channel=slack_channel_handle_name,
                                                 text=toml_data_dict["slack_details"]["post_message_to_slack"]
                                                 ["alert_message"],
                                                 attachments=[
                                               {
                                                   "text": toml_data_dict["slack_details"]["post_message_to_slack"]
                                                   ["text"].format(process_json['alert_id'],
                                                                   process_json['alert_description'],
                                                                   process_json['account_id']),
                                                   "fallback": "",
                                                   "callback_id": "message_response",
                                                   "color": toml_data_dict["slack_details"]["post_message_to_slack"]
                                                   ["color"],
                                                   "attachment_type": "default",
                                                   "actions": [
                                                       {
                                                           "name": "Yes",
                                                           "text": "Yes",
                                                           "type": "button",
                                                           "value": zen_ticket_id
                                                       },
                                                       {
                                                           "name": "No",
                                                           "text": "No",
                                                           "type": "button",
                                                           "value": zen_ticket_id
                                                       }
                                                   ]}
                                           ]
                                           )
    return response


@app.action("message_response")
async def handle_some_action(ack, body, logger, say):
    await ack()
    user = body['user']
    # await say(f"Thanks <@{user['name']}>!")
    await say(toml_data_dict['slack_details']['thanks_for_response']['text'].format(user['name']))
    logger.info(body['message_ts'])
    await app.client.chat_update(channel=body['channel']['id'], ts=body['message_ts'], text='Alert acknowledged!',
                                 attachments=[])
    table.update_item(
        Key={
            'timestamp': body['message_ts'],
        },
        UpdateExpression="set current_status = :g, responded_with = :m",
        ExpressionAttributeValues={
            ':g': "response received",
            ':m': body['actions'][0]['name']
        },
        ReturnValues="UPDATED_NEW"
    )

    resp = dynamodb_client.get_item(
        TableName="InfratestcdkStack-TableCD117FA1-1S0N39VCN52J9",
        # should reference table created using cdk through !Ref
        Key={
            'timestamp': {'S': body['message_ts']},
        }
    )

    z_id = resp['Item']['zen_ticket_id']['N']
    user = credentials['email'] + '/token'
    headers = {'content-type': 'application/json'}
    url = 'https://antstackhelp.zendesk.com/api/v2/ticket_fields'
    data = requests.get(
        url,
        auth=(user, credentials['token']),
        headers=headers
    ).json()['ticket_fields']

    ticket = zenpy_client.tickets(id=z_id)

    for i in data:
        if i['title'] == 'slack_action':
            ticket.custom_fields.append(CustomField(id=i['id'], value=body['actions'][0]['name']))

    zenpy_client.tickets.update(ticket)


async def create_zen_ticket(process_json, customer_name, slack_channel_handle_name):
    create_ticket = zenpy_client.tickets.create(
        Ticket(subject='{} | {} | {} | {} '.format(customer_name, process_json['account_id'],
                    process_json['alert_name'], process_json['alert_severity']),
               description="You have received a message in your slack channel {}".format(slack_channel_handle_name),
               requester=User(name=customer_name),
               priority='normal'
               )
        # do we need an assignee during ticket creation? if yes , who is the assignee ?
    )
    process_json.update({"customer_name": customer_name})
    user = credentials['email'] + '/token'
    headers = {'content-type': 'application/json'}
    url = 'https://antstackhelp.zendesk.com/api/v2/ticket_fields'
    data = requests.get(
        url,
        auth=(user, credentials['token']),
        headers=headers
    ).json()['ticket_fields']

    ticket_id = create_ticket.to_dict()['audit']['ticket_id']

    ticket = zenpy_client.tickets(id=ticket_id)

    for i in data:
        if i['title'] in process_json.keys():
            ticket.custom_fields.append(CustomField(id=i['id'], value=process_json[i['title']]))

    zenpy_client.tickets.update(ticket)

    return ticket_id


async def main(process_json):
    # mapping aws_account_id with reference table to obtain slack_channel_name and customer_name
    ref_resp = dynamodb_client.get_item(
        TableName="tbl_reference_data",  # reference table aws_acc_id, cust_name, slack_channel, slack_workspace
        Key={
            'account_id': {'S': process_json['account_id']}
        }
    )
    slack_channel_handle_name = ref_resp['Item']['slack_channel_handle_name']['S']
    customer_name = ref_resp['Item']['customer_name']['S']
    zen_ticket_id = await create_zen_ticket(process_json, customer_name, slack_channel_handle_name)
    response = await post_message_to_slack(process_json, slack_channel_handle_name, zen_ticket_id, customer_name)
    if process_json['alert_severity'] == "LOW" or process_json['alert_severity'] == "MED":
        table.put_item(Item={'timestamp': response['ts'], 'current_status': 'awaiting response',
                              'zen_ticket_id': zen_ticket_id, 'ttl': int(time.time()) +
                                                            toml_data_dict['zendesk_details']['ttl_data']['low/med']})
    if process_json['alert_severity'] == "HIGH" or process_json['alert_severity'] == "CRITICAL":
        table.put_item(Item={'timestamp': response['ts'], 'current_status': 'awaiting response',
                              'zen_ticket_id': zen_ticket_id, 'ttl': int(time.time()) +
                                                    toml_data_dict['zendesk_details']['ttl_data']['high/critical']})

    await AsyncSocketModeHandler(app, SLACK_APP_TOKEN).start_async()








