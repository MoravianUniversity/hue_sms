import json
import time

import redis

DISPLAY_STATE_KEY = "display:state"
DISPLAY_CHANNEL = "display:updates"
CYCLE_INDEX_KEY = "display:cycle_index"
RECENT_PICKS_KEY = "display:recent_picks"
RECENT_PICKS_LIMIT = 8


def get_redis(decode_responses=True):
    return redis.Redis(host="localhost", port=6379, db=0, decode_responses=decode_responses)


def rgb_string_to_hex(rgb_values):
    if type(rgb_values) != str:
        rgb_values = rgb_values.decode("utf-8")
    r, g, b = (int(v) for v in rgb_values.split(","))
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def rgb_string_to_list(rgb_values):
    if type(rgb_values) != str:
        rgb_values = rgb_values.decode("utf-8")
    return [int(v) for v in rgb_values.split(",")]


def build_state(color_name, rgb_values, mode="spotlight", subtitle=None):
    display_name = color_name.replace("-", " ").title()
    state = {
        "color_name": display_name,
        "color_key": color_name.lower().strip(),
        "rgb": rgb_string_to_list(rgb_values),
        "hex": rgb_string_to_hex(rgb_values),
        "mode": mode,
        "timestamp": time.time(),
    }
    if subtitle:
        state["subtitle"] = subtitle
    return state


def _format_ago(timestamp):
    seconds = time.time() - float(timestamp)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "{}m ago".format(int(seconds // 60))
    if seconds < 86400:
        return "{}h ago".format(int(seconds // 3600))
    return "{}d ago".format(int(seconds // 86400))


def record_recent_pick(state):
    pick = {
        "color": state["color_name"],
        "key": state.get("color_key", state["color_name"].lower()),
        "rgb": state["rgb"],
        "hex": state.get("hex"),
        "timestamp": state["timestamp"],
    }
    r = get_redis()
    r.lpush(RECENT_PICKS_KEY, json.dumps(pick))
    r.ltrim(RECENT_PICKS_KEY, 0, RECENT_PICKS_LIMIT - 1)


def get_recent_picks(csv_fallback=None):
    r = get_redis()
    if csv_fallback and r.llen(RECENT_PICKS_KEY) == 0:
        _hydrate_recent_from_csv(csv_fallback)

    picks = []
    for raw in r.lrange(RECENT_PICKS_KEY, 0, RECENT_PICKS_LIMIT - 1):
        pick = json.loads(raw)
        pick["ago"] = _format_ago(pick["timestamp"])
        picks.append(pick)
    return picks


def _hydrate_recent_from_csv(csv_path):
    from data_writer import recent_picks as picks_from_csv

    rows = list(reversed(picks_from_csv(csv_path, RECENT_PICKS_LIMIT)))
    if not rows:
        return
    r = get_redis()
    for row in rows:
        pick = {
            "color": row["color"],
            "key": row["key"],
            "rgb": row.get("rgb", [15, 15, 26]),
            "hex": None,
            "timestamp": time.time(),
        }
        if pick["rgb"]:
            pick["hex"] = rgb_string_to_hex("{},{},{}".format(*pick["rgb"]))
        r.rpush(RECENT_PICKS_KEY, json.dumps(pick))


def publish_state(state):
    r = get_redis()
    if state.get("mode") == "spotlight":
        record_recent_pick(state)
    payload = json.dumps(state)
    r.set(DISPLAY_STATE_KEY, payload)
    r.publish(DISPLAY_CHANNEL, payload)


def get_display_state():
    r = get_redis()
    payload = r.get(DISPLAY_STATE_KEY)
    if payload is None:
        return None
    return json.loads(payload)


def get_total_choices():
    r = get_redis(decode_responses=False)
    total = r.get("total")
    if total is None:
        return 0
    return int(total.decode("utf-8"))


def advance_cycle_color():
    """Return the next color for the SMS 'next' command and advance the index."""
    names = _palette_color_names()
    if not names:
        raise ValueError("No colors available in Redis")
    r = get_redis()
    idx = int(r.get(CYCLE_INDEX_KEY) or 0)
    color_name = names[idx % len(names)]
    r.set(CYCLE_INDEX_KEY, (idx + 1) % len(names))
    return color_name


def _palette_color_names():
    r = get_redis()
    return sorted(
        key for key in r.hkeys("colors")
        if key not in ("random", "black")
    )
