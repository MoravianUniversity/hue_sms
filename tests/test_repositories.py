from palette_repository import PaletteRepository
from stats_repository import StatsRepository
from webhook_repository import WebhookRepository


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.values = {}

    def hget(self, name, key):
        return self.hashes.get(name, {}).get(key)

    def hkeys(self, name):
        return list(self.hashes.get(name, {}).keys())

    def hexists(self, name, key):
        return key in self.hashes.get(name, {})

    def hincrby(self, name, key, amount):
        bucket = self.hashes.setdefault(name, {})
        bucket[key] = str(int(bucket.get(key, 0)) + amount)

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def incr(self, key, amount=1):
        self.values[key] = str(int(self.values.get(key, 0)) + amount)


def test_palette_get_rgb_and_list_names():
    redis = FakeRedis()
    redis.hashes["colors"] = {
        "sky blue": "118,215,234",
        "random": "0,0,0",
    }
    repo = PaletteRepository(redis)

    assert repo.get_rgb("Sky Blue") == "118,215,234"
    assert repo.list_names() == ["sky blue"]


def test_palette_fuzzy_match():
    redis = FakeRedis()
    redis.hashes["colors"] = {
        "sky blue": "118,215,234",
        "magenta": "255,89,173",
    }
    repo = PaletteRepository(redis)

    assert repo.fuzzy_match("skyblue") == "sky blue"


def test_stats_increment_and_percent():
    redis = FakeRedis()
    redis.hashes["color_totals"] = {"sky blue": "2"}
    redis.values["total"] = "4"
    repo = StatsRepository(redis)

    repo.increment("magenta")
    assert redis.hashes["color_totals"]["magenta"] == "1"
    assert redis.values["total"] == "5"
    assert repo.percent("sky blue") == 50.0


def test_webhook_record_and_get_last():
    redis = FakeRedis()
    repo = WebhookRepository(redis)

    repo.record({"body": "red", "from": "+1"})
    assert repo.get_last() == {"body": "red", "from": "+1"}
