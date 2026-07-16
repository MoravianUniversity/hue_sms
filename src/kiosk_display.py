import io
import json
import os
import re

import qrcode
from flask import Flask, Response, jsonify, render_template, send_file

from config import (
    DEFAULT_HUE_HEALTH_URL,
    DEFAULT_SMS_PHONE,
    data_file_path,
    get_redis,
    settings,
)
from display_state import DISPLAY_CHANNEL, get_display_state, get_recent_picks, get_total_choices
from health_check import check_redis, fetch_hue_flask_health
from palette import load_palette

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
DATA_FILE = data_file_path()


def _phone_digits(phone):
    return re.sub(r"\D", "", phone)


def _sms_uri(phone):
    digits = _phone_digits(phone)
    if len(digits) == 10:
        digits = "1" + digits
    return "sms:+{}".format(digits)


def enrich_state(state, include_recent=False):
    if state is None:
        state = {"mode": "current", "rgb": [15, 15, 26]}
    state = dict(state)
    state["total_choices"] = get_total_choices()
    if include_recent or state.get("mode") == "spotlight":
        state["recent"] = get_recent_picks(DATA_FILE)
    return state


@app.route("/")
def kiosk():
    phone = getattr(settings, "sms_phone_display", DEFAULT_SMS_PHONE)
    return render_template("kiosk.html", phone=phone)


@app.route("/api/state")
def api_state():
    return jsonify(enrich_state(get_display_state(), include_recent=True))


@app.route("/api/stats")
def api_stats():
    return jsonify({"total_choices": get_total_choices()})


@app.route("/api/recent")
def api_recent():
    return jsonify({"recent": get_recent_picks(DATA_FILE)})


@app.route("/api/health")
def api_health():
    hue_url = getattr(settings, "hue_health_url", DEFAULT_HUE_HEALTH_URL)
    remote = fetch_hue_flask_health(hue_url) or {}
    status = {
        "redis": check_redis(),
        "hue": remote.get("hue", False),
        "sms_server": remote.get("ok", False),
    }
    status["ok"] = status["redis"] and status["hue"] and status["sms_server"]
    code = 200 if status["ok"] else 503
    return jsonify(status), code


@app.route("/api/palette")
def api_palette():
    palette = load_palette()
    return jsonify({
        "count": len(palette),
        "colors": palette,
    })


@app.route("/api/qr")
def api_qr():
    phone = getattr(settings, "sms_phone_display", DEFAULT_SMS_PHONE)
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(_sms_uri(phone))
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


@app.route("/events")
def events():
    def stream():
        r = get_redis(decode_responses=True)
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(DISPLAY_CHANNEL)

        yield "data: {}\n\n".format(json.dumps(enrich_state(get_display_state(), include_recent=True)))

        for message in pubsub.listen():
            if message["type"] == "message":
                state = json.loads(message["data"])
                yield "data: {}\n\n".format(json.dumps(enrich_state(state)))

    return Response(stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
