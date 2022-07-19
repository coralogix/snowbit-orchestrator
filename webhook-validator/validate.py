import enum
import boto3
import time

logs = boto3.client('logs')


LOG_GROUP = 'InfratestcdkStack-SOLogGroupB340DE11-L6YUkaEBVOcI'
# should refer to cloudwatch created cdk using !Ref
LOG_STREAM = 'SOlogStream'


class Severity(enum.Enum):
    LOW = 0
    MID = 1
    HIGH = 2


class Validate:
    def __init__(self, process_json):
        self.p_data = process_json

    def json_validator(self):
        flag = 0
        if isinstance(self.p_data['alert_id'], int) and len(str(self.p_data['alert_id'])) == 12:
            if isinstance(self.p_data['alert_description'], str) and len(self.p_data['alert_description']) >= 5:
                if isinstance(self.p_data['alert_name'], str) and len(self.p_data['alert_name']) >= 5:
                    if isinstance(self.p_data['alert_severity'], str):
                        if len(str(self.p_data['aws_account_id'])) == 12:
                            # if isinstance(self.p_data['alert_severity'], enum.EnumMeta) and
                            # (self.p_data['alert_severity']) in type(self.p_data['alertSeverity'].__name__):
                            flag = 1

        response = logs.describe_log_streams(
            logGroupName=LOG_GROUP,
            orderBy='LogStreamName',
            descending=False,
            limit=50
        )

        if flag == 1:

            timestamp = int(round(time.time() * 1000))

            resp = logs.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': "VALID JSON EXPRESSION for alert_id {} from aws_account_id at {} at time {}"
                            .format(self.p_data['alert_id'], self.p_data['aws_account_id'],
                                    time.strftime('%Y-%m-%d %H:%M:%S'))
                    },
                ],
                sequenceToken=str(response['logStreams'][0]['uploadSequenceToken'])
            )

            return "VALID"
        else:
            timestamp = int(round(time.time() * 1000))

            response = logs.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[
                    {
                        'timestamp': timestamp,
                        'message': "JSON VALIDATION ERROR for alert_id {} from aws_account_id at {}"
                        .format(self.p_data['alert_id'], self.p_data['aws_account_id'],
                                time.strftime('%Y-%m-%d %H:%M:%S'))
                    },
                ],
                sequenceToken=str(response['logStreams'][0]['uploadSequenceToken'])
            )

            return "INVALID"








