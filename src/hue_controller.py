import logging

from phue import Bridge, PhueException

import name_converter
from config import configure_logging, settings
from hue_color import get_gamut, rgb_to_hue

configure_logging()

IP_address = settings.light_ip
light_number = settings.light_number
HUE_GAMUT = get_gamut(getattr(settings, "hue_gamut", "C"))


class HueController:

    def __init__(self):
        self.bridge = None
        self.light = None
        self.name_to_color = name_converter.NameConverter()

    def connect(self):
        if self.light is not None:
            return

        self.bridge = Bridge(IP_address)
        self.bridge.connect()
        logging.info("Server was successfully able to connect to the bridge")
        self.light = self.bridge.lights[light_number]

    def _apply_chromatic(self, x, y, bri, saturation, transitiontime):
        self.light.transitiontime = transitiontime
        self.light.on = True
        self.light.brightness = bri
        self.light.xy = (x, y)
        self.light.saturation = saturation

    def _apply_white(self, bri, transitiontime):
        self.bridge.set_light(self.light.light_id, {
            "on": True,
            "bri": bri,
            "sat": 0,
            "transitiontime": transitiontime,
        })

    def set_rgb(self, rgb_values, transitiontime=4):
        if type(rgb_values) != str:
            rgb_values = rgb_values.decode("utf-8")
        r, g, b = (int(v) for v in rgb_values.split(','))
        x, y, bri, saturation = rgb_to_hue(r, g, b, gamut=HUE_GAMUT)

        try:
            self.connect()
            if saturation == 0:
                self._apply_white(bri, transitiontime)
            else:
                self._apply_chromatic(x, y, bri, saturation, transitiontime)
        except (PhueException, AttributeError):
            logging.info("Hue connection lost, reconnecting")
            self.light = None
            self.bridge = None
            self.connect()
            if saturation == 0:
                self._apply_white(bri, transitiontime)
            else:
                self._apply_chromatic(x, y, bri, saturation, transitiontime)
