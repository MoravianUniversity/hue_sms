"""Redis access for kiosk display state and pub/sub."""

import json
import time

from config import get_redis
from palette_repository import PaletteRepository

DISPLAY_STATE_KEY = "display:state"
DISPLAY_CHANNEL = "display:updates"
CYCLE_INDEX_KEY = "display:cycle_index"
RECENT_PICKS_KEY = "display:recent_picks"
RECENT_PICKS_LIMIT = 8


class DisplayRepository:
    def __init__(self, redis_client=None, palette_repo=None):
        self.redis = redis_client or get_redis()
        self.palette = palette_repo or PaletteRepository(self.redis)

    def publish(self, state):
        if state.get("mode") == "spotlight":
            self._record_recent_pick(state)
        payload = json.dumps(state)
        self.redis.set(DISPLAY_STATE_KEY, payload)
        self.redis.publish(DISPLAY_CHANNEL, payload)

    def get_state(self):
        payload = self.redis.get(DISPLAY_STATE_KEY)
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return json.loads(payload)

    def get_recent_picks(self, csv_fallback=None):
        if csv_fallback and self.redis.llen(RECENT_PICKS_KEY) == 0:
            self._hydrate_recent_from_csv(csv_fallback)

        picks = []
        for raw in self.redis.lrange(RECENT_PICKS_KEY, 0, RECENT_PICKS_LIMIT - 1):
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            pick = json.loads(raw)
            pick["ago"] = _format_ago(pick["timestamp"])
            picks.append(pick)
        return picks

    def advance_cycle(self):
        names = self.palette.list_showable_names()
        if not names:
            raise ValueError("No colors available in Redis")
        idx = int(self.redis.get(CYCLE_INDEX_KEY) or 0)
        color_name = names[idx % len(names)]
        self.redis.set(CYCLE_INDEX_KEY, (idx + 1) % len(names))
        return color_name

    def _record_recent_pick(self, state):
        pick = {
            "color": state["color_name"],
            "key": state.get("color_key", state["color_name"].lower()),
            "rgb": state["rgb"],
            "hex": state.get("hex"),
            "timestamp": state["timestamp"],
        }
        self.redis.lpush(RECENT_PICKS_KEY, json.dumps(pick))
        self.redis.ltrim(RECENT_PICKS_KEY, 0, RECENT_PICKS_LIMIT - 1)

    def _hydrate_recent_from_csv(self, csv_path):
        from data_writer import recent_picks as picks_from_csv
        from display_state import rgb_string_to_hex

        rows = list(reversed(picks_from_csv(csv_path, RECENT_PICKS_LIMIT)))
        if not rows:
            return
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
            self.redis.rpush(RECENT_PICKS_KEY, json.dumps(pick))


def _format_ago(timestamp):
    seconds = time.time() - float(timestamp)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "{}m ago".format(int(seconds // 60))
    if seconds < 86400:
        return "{}h ago".format(int(seconds // 3600))
    return "{}d ago".format(int(seconds // 86400))
