"""Legacy entry point — prefer: python -m hue_sms.web.kiosk_display"""

from hue_sms.web.kiosk_display import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
