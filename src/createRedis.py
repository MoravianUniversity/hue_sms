import os

from config import get_redis

from hue_color import is_excluded_palette_color
from name_converter import clean_name


def go():
    db = get_redis()

    location = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    db.flushdb()

    with open(location + "/colors.csv") as colors:
        for line in colors:
            line = line.strip()
            name, red, green, blue = line.split(",")
            red, green, blue = int(red), int(green), int(blue)
            if is_excluded_palette_color(red, green, blue):
                continue

            key = clean_name(name)
            input_val = "{},{},{}".format(red, green, blue)

            db.hset("colors", key, input_val)
            db.hset("color_totals", key, 0)
            db.incr("color_sum")

    extra_path = location + "/extra_colors.csv"
    if os.path.exists(extra_path):
        with open(extra_path) as colors:
            for line in colors:
                line = line.strip()
                if not line:
                    continue
                name, red, green, blue = line.split(",")
                red, green, blue = int(red), int(green), int(blue)
                if is_excluded_palette_color(red, green, blue):
                    continue
                key = clean_name(name)
                if db.hexists("colors", key):
                    continue
                input_val = "{},{},{}".format(red, green, blue)
                db.hset("colors", key, input_val)
                db.hset("color_totals", key, 0)
                db.incr("color_sum")
    db.hset("color_totals", "random", 0)
    db.set("total", 0)


if __name__ == "__main__":
    go()
