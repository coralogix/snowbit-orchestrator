import slack_bolt
from slack_bolt import App, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

import boto3
import logging
import os
logging.basicConfig(level=logging.DEBUG)


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Slackacktable')

app = App(token=os.environ.get['SLACK_BOT_TOKEN'])


def post_message_to_slack():
    response = app.client.chat_postMessage(channel="#testbot2",
                                           text="socket test",
                                           attachments=[
                                               {
                                                   "text": "Select Yes/No",
                                                   "fallback": "",
                                                   "callback_id": "message_response",
                                                   "color": "#3AA3E3",
                                                   "attachment_type": "default",
                                                   "actions": [
                                                       {
                                                           "name": "yes",
                                                           "text": "yes",
                                                           "type": "button",
                                                           "value": "yes"
                                                       },
                                                       {
                                                           "name": "no",
                                                           "text": "no",
                                                           "type": "button",
                                                           "value": "no"
                                                       }
                                                   ]}
                                           ]
                                           )
    return response


@app.action("message_response")
def handle_some_action(ack, body, logger, say):
    print("**BEGIN HERE**")
    ack()
    user = body['user']
    say(f"Thanks <@{user['name']}>!")
    logger.info(body['message_ts'])
    print(body)
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
    app.client.chat_delete(channel=body['channel']['id'], ts=body['message_ts'])


if __name__ == "__main__":
    response = post_message_to_slack()
    print("This is the timestamp = {}".format(response['ts']))
    table.put_item(Item={'timestamp': response['ts'], 'current_status': 'awaiting response'})

    SocketModeHandler(app, os.environ.get['SLACK_APP_TOKEN']).start()



