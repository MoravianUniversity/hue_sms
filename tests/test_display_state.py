from display_state import (
    advance_cycle_color,
    build_state,
    build_unsupported_state,
    get_recent_picks,
    is_likely_unsupported_color_name,
    publish_state,
    publish_unsupported_color,
)

TEST_COLORS = ["sky blue", "magenta", "goldenrod"]
SORTED_COLORS = sorted(TEST_COLORS)


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.lists = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = str(value)

    def hkeys(self, name):
        if name == "colors":
            return list(TEST_COLORS)
        return []

    def hget(self, name, key):
        if name == "colors":
            return {
                "sky blue": "118,215,234",
                "magenta": "255,89,173",
                "goldenrod": "255,216,105",
            }.get(key)
        return None

    def publish(self, channel, payload):
        pass

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
        return items[start:end + 1]


def test_advance_cycle_color_rotates(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("display_state.get_redis", lambda decode_responses=True: fake)

    first = advance_cycle_color()
    second = advance_cycle_color()

    assert first == SORTED_COLORS[0]
    assert second == SORTED_COLORS[1]


def test_build_unsupported_state():
    state = build_unsupported_state("eerie black")
    assert state["mode"] == "unsupported"
    assert state["color_name"] == "Eerie Black"
    assert "message" in state


def test_is_likely_unsupported_color_name():
    assert is_likely_unsupported_color_name("gray")
    assert is_likely_unsupported_color_name("eerie black")
    assert is_likely_unsupported_color_name("beaver")
    assert is_likely_unsupported_color_name("lumber")
    assert not is_likely_unsupported_color_name("white")
    assert not is_likely_unsupported_color_name("pink")
    assert not is_likely_unsupported_color_name("sky blue")


def test_spotlight_records_recent_pick(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("display_state.get_redis", lambda decode_responses=True: fake)

    publish_state(build_state("sky blue", "118,215,234", mode="spotlight"))
    picks = get_recent_picks()

    assert len(picks) == 1
    assert picks[0]["color"] == "Sky Blue"
    assert picks[0]["rgb"] == [118, 215, 234]


def test_unsupported_state_is_not_recorded_as_recent(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("display_state.get_redis", lambda decode_responses=True: fake)

    publish_unsupported_color("gray")
    picks = get_recent_picks()

    assert picks == []
