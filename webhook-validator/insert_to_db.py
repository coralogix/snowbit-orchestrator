import boto3
import time
import toml

logs = boto3.client('logs')
client = boto3.client('ssm')

ssm_response = client.get_parameter(
    Name='webhook_db_name',
    WithDecryption=False
)

tbl_webhook_table_name = ssm_response['Parameter']['Value']

LOG_GROUP = 'InfratestcdkStack-SOLogGroupB340DE11-L6YUkaEBVOcI'
# should refer to cloudwatch created cdk using !Ref
LOG_STREAM = 'SOlogStream'

input_file = "output.toml"


with open(input_file, "r") as toml_file:
    toml_data_dict = toml.load(toml_file)


class InserttoDb:
    def __init__(self, process_json):
        self.clean_json = process_json
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(tbl_webhook_table_name)

    def insertjson_todb(self):
        self.table.put_item(Item=self.clean_json)
        response = logs.describe_log_streams(
            logGroupName=LOG_GROUP,
            orderBy='LogStreamName',
            descending=False,
            limit=50
        )
        timestamp = int(round(time.time() * 1000))

        response = logs.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': toml_data_dict['database_opr']['insertion_success']
                    .format(self.clean_json['alert_id'], self.clean_json['account_id'],
                                time.strftime('%Y-%m-%d %H:%M:%S'))
                },
            ],
            sequenceToken=str(response['logStreams'][0]['uploadSequenceToken'])
        )
