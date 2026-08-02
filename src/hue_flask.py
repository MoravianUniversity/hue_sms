import logging
import time

from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request, jsonify

from config import configure_logging, data_file_path
from event_repository import EventRepository
from handle_sms import SmsRequestHandler, handle_sms_request
from health_check import check_hue, check_redis
from hue_controller import HueController
from stats_repository import StatsRepository
from webhook_repository import WebhookRepository

configure_logging()

app = Flask(__name__)
controller = HueController()
sms_handler = SmsRequestHandler(controller=controller)
webhook_repo = WebhookRepository()
events_repo = EventRepository()
stats_repo = StatsRepository()
file = data_file_path()


def record_incoming_webhook(body, from_num):
    payload = {
        "timestamp": time.time(),
        "method": request.method,
        "path": request.path,
        "from": from_num,
        "body": body,
        "remote_addr": request.remote_addr,
    }
    webhook_repo.record(payload)
    logging.info(
        "Incoming webhook %s %s from=%s body=%r remote=%s",
        request.method,
        request.path,
        from_num,
        body,
        request.remote_addr,
    )


def twiml_response(message):
    response = MessagingResponse()
    response.message(message)
    return str(response), 200, {"Content-Type": "text/xml"}


@app.route("/", methods=["POST", "GET"])
@app.route("/sms", methods=["POST", "GET"])
def set_color():
    phone_number = request.values.get("From", None)
    body = request.values.get("Body", "") or ""
    record_incoming_webhook(body, phone_number)
    message = handle_sms_request(body, phone_number, handler=sms_handler)
    return twiml_response(message)


@app.route("/health", methods=["GET"])
def health():
    status = {
        "redis": check_redis(),
        "hue": check_hue(controller),
        "last_webhook": webhook_repo.get_last(),
    }
    status["ok"] = status["redis"] and status["hue"]
    code = 200 if status["ok"] else 503
    return jsonify(status), code


@app.route("/recents", methods=["GET"])
def get_most_recent():
    return jsonify(events_repo.recent_color_names(limit=5))


@app.route("/number", methods=["GET"])
def get_num_of_each():
    return jsonify(stats_repo.color_counts())


@app.route("/invalids", methods=["GET"])
def get_invalids():
    return jsonify(events_repo.invalid_color_names())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    logging.info("Server has been stopped")
