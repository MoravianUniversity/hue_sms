import os

from config import get_redis
import redis

from hue_color import is_excluded_palette_color
from name_converter import clean_name

COLORS_DIR = os.path.dirname(os.path.abspath(__file__))


def _format_entry(name, rgb_string):
    r, g, b = (int(v) for v in rgb_string.split(","))
    display = name.replace("-", " ").title()
    return {
        "name": display,
        "key": name,
        "rgb": [r, g, b],
        "hex": "#{:02x}{:02x}{:02x}".format(r, g, b),
    }


def load_palette_from_csv():
    palette = []
    seen = set()
    for filename in ("colors.csv", "extra_colors.csv"):
        path = os.path.join(COLORS_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path) as colors:
            for line in colors:
                line = line.strip()
                if not line:
                    continue
                name, red, green, blue = line.split(",")
                r, g, b = int(red), int(green), int(blue)
                if is_excluded_palette_color(r, g, b):
                    continue
                key = clean_name(name)
                if key in seen:
                    continue
                seen.add(key)
                palette.append(_format_entry(key, "{},{},{}".format(red, green, blue)))
    palette.sort(key=lambda entry: entry["name"])
    return palette


def load_palette():
    try:
        r = get_redis(decode_responses=True)
        colors = r.hgetall("colors")
        if colors:
            palette = []
            for name, rgb in colors.items():
                if name == "random":
                    continue
                r, g, b = (int(v) for v in rgb.split(","))
                if is_excluded_palette_color(r, g, b):
                    continue
                palette.append(_format_entry(name, rgb))
            palette.sort(key=lambda entry: entry["name"])
            return palette
    except redis.RedisError:
        pass
    return load_palette_from_csv()
