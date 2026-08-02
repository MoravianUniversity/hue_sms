import pytest
from datetime import datetime

from hue_sms.infrastructure.event_repository import EVENTS_KEY, FIRST_SEEN_KEY, EventRepository
from hue_sms.infrastructure.palette_repository import PaletteRepository


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}
        self.hashes = {"colors": {"sky blue": "118,215,234", "foo": "1,2,3"}}

    def exists(self, key):
        return key in self.values

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = str(value)

    def lpush(self, key, value):
        self.lists.setdefault(key, [])
        self.lists[key].insert(0, value)

    def rpush(self, key, value):
        self.lists.setdefault(key, [])
        self.lists[key].append(value)

    def ltrim(self, key, start, end):
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end + 1]

    def llen(self, key):
        return len(self.lists.get(key, []))

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])
        if end == -1:
            end = len(items) - 1
        return items[start:end + 1]

    def lindex(self, key, index):
        items = self.lists.get(key, [])
        try:
            return items[index]
        except IndexError:
            return None

    def hget(self, name, key):
        return self.hashes.get(name, {}).get(key)

    def hkeys(self, name):
        return list(self.hashes.get(name, {}).keys())

    def hexists(self, name, key):
        return key in self.hashes.get(name, {})


def test_append_sets_first_seen_and_stores_event():
    redis = FakeRedis()
    repo = EventRepository(redis_client=redis, palette_repo=PaletteRepository(redis), max_events=100)

    repo.append("+15551234567", "sky blue", "Changed to sky blue")

    assert redis.values[FIRST_SEEN_KEY]
    assert len(redis.lists[EVENTS_KEY]) == 1
    event = repo.recent_events(limit=1)[0]
    assert event["color"] == "sky blue"
    assert event["from"] == "+15551234567"


def test_first_event_date_falls_back_to_oldest_event():
    redis = FakeRedis()
    repo = EventRepository(redis_client=redis, palette_repo=PaletteRepository(redis), max_events=100)
    ts = datetime(2024, 6, 15, 12, 0, 0).timestamp()
    redis.rpush(
        EVENTS_KEY,
        '{"timestamp": %s, "from": "", "color": "red", "message": "hi"}' % ts,
    )

    assert repo.first_event_date() == "2024-06-15"


def test_invalid_color_names():
    redis = FakeRedis()
    repo = EventRepository(redis_client=redis, palette_repo=PaletteRepository(redis), max_events=100)
    repo.append("", "bar", "unknown")

    assert repo.invalid_color_names() == ["bar"]


def test_recent_color_names():
    redis = FakeRedis()
    repo = EventRepository(redis_client=redis, palette_repo=PaletteRepository(redis), max_events=100)
    repo.append("", "sky blue", "one")
    repo.append("", "sky blue", "two")

    assert repo.recent_color_names(limit=2) == ["sky blue", "sky blue"]
