"""Redis-backed log of successful SMS color events."""

import json
import time
from datetime import datetime

from hue_sms.config import get_redis
from hue_sms.infrastructure.palette_repository import PaletteRepository

EVENTS_KEY = "events:log"
FIRST_SEEN_KEY = "stats:first_seen"
DEFAULT_EVENT_LIMIT = 5000


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class EventRepository:
    def __init__(self, redis_client=None, palette_repo=None, max_events=None):
        self.redis = redis_client or get_redis()
        self.palette = palette_repo or PaletteRepository(self.redis)
        self.max_events = max_events or DEFAULT_EVENT_LIMIT

    def append(self, from_number, color_key, message):
        timestamp = time.time()
        if not self.redis.exists(FIRST_SEEN_KEY):
            self.redis.set(
                FIRST_SEEN_KEY,
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
            )
        payload = json.dumps(
            {
                "timestamp": timestamp,
                "from": from_number or "",
                "color": color_key,
                "message": message,
            }
        )
        self.redis.lpush(EVENTS_KEY, payload)
        if self.max_events:
            self.redis.ltrim(EVENTS_KEY, 0, self.max_events - 1)

    def first_event_date(self):
        raw = self.redis.get(FIRST_SEEN_KEY)
        if raw is not None:
            return _decode(raw)

        oldest = self.redis.lindex(EVENTS_KEY, -1)
        if oldest is None:
            return ""
        event = json.loads(_decode(oldest))
        return datetime.fromtimestamp(float(event["timestamp"])).strftime("%Y-%m-%d")

    def recent_events(self, limit=10):
        events = []
        for raw in self.redis.lrange(EVENTS_KEY, 0, limit - 1):
            events.append(json.loads(_decode(raw)))
        return events

    def recent_color_names(self, limit=5):
        return [event["color"] for event in self.recent_events(limit=limit)]

    def invalid_color_names(self):
        invalid = []
        seen = set()
        for raw in self.redis.lrange(EVENTS_KEY, 0, -1):
            event = json.loads(_decode(raw))
            color_key = event["color"]
            if color_key in seen:
                continue
            seen.add(color_key)
            if not self.palette.exists(color_key):
                invalid.append(color_key)
        return invalid

    def responses_table_rows(self, limit=10):
        """Rows for plotlydash: Time, Last 4 Digits, Color."""
        rows = {"Time": [], "Last 4 Digits": [], "Color": []}
        for event in self.recent_events(limit=limit):
            ts = datetime.fromtimestamp(float(event["timestamp"]))
            rows["Time"].append(ts.strftime("%Y-%m-%d %I:%M %p"))
            phone = str(event.get("from") or "")
            suffix = phone[-4:] if len(phone) >= 4 else phone
            rows["Last 4 Digits"].append("###-###-{}".format(suffix))
            rows["Color"].append(str(event["color"]).replace("-", " ").title())
        return rows

    def import_from_csv(self, csv_path):
        """One-time migration: load CSV rows into Redis if the event log is empty."""
        if self.redis.llen(EVENTS_KEY) > 0:
            return 0

        rows = []
        try:
            import csv

            with open(csv_path, newline="") as handle:
                for row in csv.reader(handle):
                    if len(row) < 4:
                        continue
                    timestamp_raw, from_number, color_key, message = row[0], row[1], row[2], row[3]
                    timestamp_raw = timestamp_raw.strip('"')
                    try:
                        timestamp = datetime.fromisoformat(timestamp_raw).timestamp()
                    except ValueError:
                        timestamp = datetime.strptime(
                            timestamp_raw[:19], "%Y-%m-%d %H:%M:%S"
                        ).timestamp()
                    rows.append(
                        {
                            "timestamp": timestamp,
                            "from": from_number,
                            "color": color_key,
                            "message": message,
                            "date": timestamp_raw[:10],
                        }
                    )
        except FileNotFoundError:
            return 0

        if not rows:
            return 0

        self.redis.set(FIRST_SEEN_KEY, rows[0]["date"])
        for row in reversed(rows):
            payload = json.dumps(
                {
                    "timestamp": row["timestamp"],
                    "from": row["from"],
                    "color": row["color"],
                    "message": row["message"],
                }
            )
            self.redis.lpush(EVENTS_KEY, payload)

        if self.max_events and len(rows) > self.max_events:
            self.redis.ltrim(EVENTS_KEY, 0, self.max_events - 1)
        return len(rows)
