from readline import insert_text
import signal
from flask import Flask, Response, render_template, request
import logging
from validate import *
from inserttodb import *


class EndpointAction(object):

    def __init__(self, action):
        self.action = action
        self.response = Response(status=200, headers={})

    def __call__(self, *args):
        # this is being triggered everytime
        response = self.action()
        w = WebhookHandler(getattr(action, 'data'))
        process_json = w.localize()
        v = Validate(process_json)
        result = v.localize()
        if result == "VALID":
            i = InserttoDb(process_json)
            i.localize()
        if response is not None:
            return response
        else:
            return self.response


class FlaskAppWrapper(object):
    app = None

    def __init__(self, name):
        self.app = Flask(name)

    def run(self):
        self.app.run()

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, t_methods=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler), methods=t_methods)


def action():
    try:
        alert_name = request.get_json()['name']
        alert_severity = ""
        for i in request.get_json()["fields"]:
            if i["key"] == "severity":
                alert_severity = i["value"]
        action.data = {'accountId': "account_id", 'alertDescription': "desc", 'alertName': alert_name,
                    'alertSeverity': alert_severity}

        return "OK"
    except KeyError:
        # should this error be logged to cloudwatch using boto3
        pass


def returning_action():
    return render_template('index.html')


a = FlaskAppWrapper('wrap')
a.add_endpoint(endpoint='/data', endpoint_name='data', handler=action, t_methods=["POST"])

logger = logging.getLogger('werkzeug')
handler = logging.FileHandler('access.log')
logger.addHandler(handler)


class WebhookHandler:
    def __init__(self, data):
        self.data = data
        # will contain JSON payload obtained from POST (without filters)

    def localize(self):
        print('From webhook handler')
        print(self.data, flush=True)
        return self.data
        # return self.data # contains parsed JSON/dictionary (with filters)


class Validate:
    def __init__(self):
        pass


if __name__ == "__main__":
    a.run()

