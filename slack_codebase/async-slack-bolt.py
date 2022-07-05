import os
import asyncio
import boto3
import logging
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logging.basicConfig(level=logging.DEBUG)


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Slackacktable')

app = AsyncApp(token=os.environ.get['SLACK_BOT_TOKEN'])


async def post_message_to_slack():  # alert severity and description
    response = await app.client.chat_postMessage(channel="#testbot2",
                                                 text="Alert Raised!",
                                                 attachments=[
                                               {
                                                   "text": "An alert was raised in Coralogix, do you acknowledge ?",
                                                   "fallback": "",
                                                   "callback_id": "message_response",
                                                   "color": "#3AA3E3",
                                                   "attachment_type": "default",
                                                   "actions": [
                                                       {
                                                           "name": "Yes",
                                                           "text": "Yes",
                                                           "type": "button",
                                                           "value": "yes"
                                                       },
                                                       {
                                                           "name": "No",
                                                           "text": "No",
                                                           "type": "button",
                                                           "value": "no"
                                                       }
                                                   ]}
                                           ]
                                           )
    return response


@app.action("message_response")
async def handle_some_action(ack, body, logger, say):
    await ack()
    user = body['user']
    await say(f"Thanks <@{user['name']}>!")
    logger.info(body['message_ts'])
    print(body['message_ts'])
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
    app.client.chat_update(channel=body['channel']['id'], ts=body['message_ts'], text='Alert acknowledged!',
                           attachments=[])


async def main():
    response = await post_message_to_slack()
    print("This is response = {}".format(response['ts']))
    table.put_item(Item={'timestamp': response['ts'], 'current_status': 'awaiting response'})
    await AsyncSocketModeHandler(app, os.environ.get['SLACK_APP_TOKEN']).start_async()


if __name__ == "__main__":
    asyncio.run(main())




