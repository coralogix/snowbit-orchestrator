import json
import toml
import boto3
import time


logs = boto3.client('logs')


LOG_GROUP = 'InfratestcdkStack-SOLogGroupB340DE11-L6YUkaEBVOcI'
# should refer to cloudwatch created cdk using !Ref
LOG_STREAM = 'SOlogStream'

input_file = "output.toml"

with open(input_file) as toml_file:
    toml_data_dict = toml.load(toml_file)


class WebhookHandler:
    def __init__(self, data):
        self.data = data
        # will contain JSON payload obtained from POST (without filters)

    def webhook_extractor(self):
        try:
            alert_severity = ''
            account_id = self.data['account_id']
            alert_id = self.data['uuid']
            alert_description = self.data['description']
            alert_name = self.data['name']
            for i in self.data['fields']:
                if i['key'] == "severity":
                    alert_severity = i['value']
            processed_json = {'alert_id': alert_id,
                              'account_id': account_id,
                              'alert_description': alert_description, 'alert_name': alert_name,
                              'alert_severity': alert_severity}
            return processed_json

        except KeyError as e:
            timestamp = int(round(time.time() * 1000))

            response = logs.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': toml_data_dict['validation']['key_error'].format(e)
                    }
                ]
            )

        except json.decoder.JSONDecodeError:
            timestamp = int(round(time.time() * 1000))
            response = logs.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': toml_data_dict['validation']['json_decode_error']
                    }
                ]
            )

