from flask import request, Flask
from threading import Thread
import requests
import json
import toml
from webhook_handler import WebhookHandler
from validate import Validate
from insert_to_db import InserttoDb


output_file_name = "output.toml"
with open(output_file_name, "r") as toml_file:
    toml_data_dict = toml.load(toml_file)


app = Flask(__name__)


class Compute(Thread):
    def __init__(self, req):
        Thread.__init__(self)
        self.request = req

    def run(self):
        w = WebhookHandler(self.request)
        process_json = w.webhook_extractor()
        v = Validate(process_json)
        result = v.json_validator()
        if result == "VALID":
            i = InserttoDb(process_json)
            i.insertjson_todb()
            payload = process_json
            url = toml_data_dict['url']['local_server_url']
            headers = {'Content-type': 'application/json; charset=UTF-8'}
            response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
            print(response.text)
        # asyncio.run(main(process_json))


@app.route('/data', methods=["POST"])
def myfunc():
    req = request.get_json()
    thread_a = Compute(req)
    thread_a.start()
    return "Processing in background", 200


# app.run(port=5000)