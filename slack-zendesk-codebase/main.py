from flask import request, Flask
from threading import Thread
from async_slack import *

app = Flask(__name__)


class Compute(Thread):
    def __init__(self, req):
        Thread.__init__(self)
        self.request = req

    def run(self):
        asyncio.run(main(self.request))


@app.route('/receiveslack', methods=["POST"])  # change naming conventions
def myfunc():
    req = request.get_json()
    thread_a = Compute(req)
    thread_a.start()
    return "Processing Slack in background", 200


# app.run(port=3000)