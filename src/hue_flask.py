import json
import logging
import time

from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request, jsonify

from config import configure_logging, data_file_path, get_redis
from data_writer import mostRecentColors, numOfEachColor, invalidColors
from handle_sms import SmsRequestHandler, handle_sms_request
from health_check import check_hue, check_redis
from hue_controller import HueController

configure_logging()

app = Flask(__name__)
controller = HueController()
sms_handler = SmsRequestHandler(controller=controller)
file = data_file_path()
LAST_WEBHOOK_KEY = "webhook:last"


def record_incoming_webhook(database, body, from_num):
    payload = {
        "timestamp": time.time(),
        "method": request.method,
        "path": request.path,
        "from": from_num,
        "body": body,
        "remote_addr": request.remote_addr,
    }
    database.set(LAST_WEBHOOK_KEY, json.dumps(payload))
    logging.info(
        "Incoming webhook %s %s from=%s body=%r remote=%s",
        request.method,
        request.path,
        from_num,
        body,
        request.remote_addr,
    )


def get_last_webhook(database):
    raw = database.get(LAST_WEBHOOK_KEY)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def twiml_response(message):
    response = MessagingResponse()
    response.message(message)
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/", methods=["POST", "GET"])
@app.route("/sms", methods=["POST", "GET"])
def set_color():
    database = get_redis()
    phone_number = request.values.get("From", None)
    body = request.values.get("Body", "") or ""
    record_incoming_webhook(database, body, phone_number)
    message = handle_sms_request(body, phone_number, handler=sms_handler)
    return twiml_response(message)


@app.route("/health", methods=["GET"])
def health():
    database = get_redis()
    status = {
        "redis": check_redis(),
        "hue": check_hue(controller),
        "last_webhook": get_last_webhook(database),
    }
    status["ok"] = status["redis"] and status["hue"]
    code = 200 if status["ok"] else 503
    return jsonify(status), code


@app.route("/recents", methods=["GET"])
def get_most_recent():
    return mostRecentColors(file)


@app.route("/number", methods=["GET"])
def get_num_of_each():
    return numOfEachColor(file)


@app.route("/invalids", methods=["GET"])
def get_invalids():
    return invalidColors(file)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    logging.info("Server has been stopped")
