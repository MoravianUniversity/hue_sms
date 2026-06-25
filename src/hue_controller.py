import rgbxy
from phue import Bridge, PhueException
import name_converter
from rgbxy import Converter
from name_converter import clean_name
from dynaconf import Dynaconf
import logging
from getRedisColor import getColor

logging.basicConfig(level=logging.INFO,filename="hue_log.log",
                    format="%(asctime)s:%(levelname)s:%(message)s"	)

settings = Dynaconf(settings_files=['settings.toml'])

saturation_val = 0
branch_value = 0
IP_address = settings.light_ip
light_number = settings.light_number


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

    def set_rgb(self, rgb_values, transitiontime=4):
        if type(rgb_values) != str:
            rgb_values = rgb_values.decode("utf-8")
        r, g, b = (int(v) for v in rgb_values.split(','))
        converter = Converter()
        saturation_val = 0 if r == 255 and g == 255 and b == 255 else 255
        x, y = converter.rgb_to_xy(r, g, b)

        try:
            self.light.on = True
            self.light.transitiontime = transitiontime
            self.light.xy = (x, y)
            self.light.saturation = saturation_val
        except (PhueException, AttributeError):
            logging.info("Hue connection lost, reconnecting")
            self.light = None
            self.bridge = None
            self.connect()
            self.light.on = True
            self.light.transitiontime = transitiontime
            self.light.xy = (x, y)
            self.light.saturation = saturation_val

