"""Legacy entry point — prefer: python -m hue_sms.web.hue_flask"""

from hue_sms.web.hue_flask import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
