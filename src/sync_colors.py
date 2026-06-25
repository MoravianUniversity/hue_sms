import os

import redis

from name_converter import clean_name

COLORS_DIR = os.path.dirname(os.path.abspath(__file__))


def sync_file(path, r):
    added = 0
    with open(path) as colors:
        for line in colors:
            line = line.strip()
            if not line:
                continue
            name, red, green, blue = line.split(",")
            key = clean_name(name)
            if r.hexists("colors", key):
                continue
            rgb = "{},{},{}".format(red, green, blue)
            r.hset("colors", key, rgb)
            r.hset("color_totals", key, 0)
            r.incr("color_sum")
            added += 1
    return added


def go():
    r = redis.Redis(host="localhost", port=6379, db=0)
    added = 0
    for filename in ("colors.csv", "extra_colors.csv"):
        path = os.path.join(COLORS_DIR, filename)
        if os.path.exists(path):
            added += sync_file(path, r)
    print("Added {} new color(s) to Redis.".format(added))


if __name__ == "__main__":
    go()
