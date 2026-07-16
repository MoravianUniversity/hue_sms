import os

from config import get_redis

from hue_color import is_excluded_palette_color
from name_converter import clean_name

COLORS_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_rgb(red, green, blue):
    return int(red), int(green), int(blue)


def should_include_color(name, red, green, blue):
    r, g, b = _parse_rgb(red, green, blue)
    return not is_excluded_palette_color(r, g, b)


def refresh_file(path, r):
    updated = 0
    with open(path) as colors:
        for line in colors:
            line = line.strip()
            if not line:
                continue
            name, red, green, blue = line.split(",")
            if not should_include_color(name, red, green, blue):
                continue
            key = clean_name(name)
            rgb = "{},{},{}".format(red, green, blue)
            existing = r.hget("colors", key)
            if existing is not None:
                if isinstance(existing, bytes):
                    existing = existing.decode("utf-8")
                if existing != rgb:
                    r.hset("colors", key, rgb)
                    updated += 1
                continue
            r.hset("colors", key, rgb)
            r.hset("color_totals", key, 0)
            r.incr("color_sum")
    return updated


def sync_file(path, r):
    added = 0
    with open(path) as colors:
        for line in colors:
            line = line.strip()
            if not line:
                continue
            name, red, green, blue = line.split(",")
            if not should_include_color(name, red, green, blue):
                continue
            key = clean_name(name)
            if r.hexists("colors", key):
                continue
            rgb = "{},{},{}".format(red, green, blue)
            r.hset("colors", key, rgb)
            r.hset("color_totals", key, 0)
            r.incr("color_sum")
            added += 1
    return added


def _palette_keys_from_csv():
    keys = set()
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
                if not should_include_color(name, red, green, blue):
                    continue
                keys.add(clean_name(name))
    return keys


def prune_orphaned_colors(r):
    """Remove Redis colors that are no longer in the CSV palette."""
    valid = _palette_keys_from_csv()
    valid.add("random")
    removed = 0
    for key in r.hkeys("colors"):
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        if key not in valid:
            r.hdel("colors", key)
            r.hdel("color_totals", key)
            removed += 1
    return removed


def prune_excluded_colors(r):
    removed = 0
    for key in r.hkeys("colors"):
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        if key == "random":
            continue
        rgb = r.hget("colors", key)
        if rgb is None:
            continue
        if isinstance(rgb, bytes):
            rgb = rgb.decode("utf-8")
        red, green, blue = rgb.split(",")
        if not should_include_color(key, red, green, blue):
            r.hdel("colors", key)
            r.hdel("color_totals", key)
            removed += 1
    return removed


def go(refresh=False):
    r = get_redis()
    added = 0
    updated = 0
    for filename in ("colors.csv", "extra_colors.csv"):
        path = os.path.join(COLORS_DIR, filename)
        if not os.path.exists(path):
            continue
        if refresh:
            updated += refresh_file(path, r)
        else:
            added += sync_file(path, r)
    removed = prune_excluded_colors(r)
    orphaned = prune_orphaned_colors(r)
    if refresh:
        print("Updated {} color value(s) in Redis.".format(updated))
    else:
        print("Added {} new color(s) to Redis.".format(added))
    if removed:
        print("Removed {} excluded color(s) from Redis.".format(removed))
    if orphaned:
        print("Removed {} orphaned color(s) from Redis.".format(orphaned))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync palette CSV files into Redis.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Update RGB values for colors already in Redis.",
    )
    args = parser.parse_args()
    go(refresh=args.refresh)
