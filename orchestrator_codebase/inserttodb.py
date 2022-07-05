import boto3


class InserttoDb:
    def __init__(self, process_json):
        self.clean_json = process_json
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('CoralogixAlertTable')

    def localize(self):
        self.table.put_item(Item=self.clean_json)
