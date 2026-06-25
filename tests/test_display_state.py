from display_state import advance_cycle_color, build_state, get_recent_picks, publish_state

TEST_COLORS = ["sky blue", "magenta", "goldenrod"]


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

    assert first == TEST_COLORS[0]
    assert second == TEST_COLORS[1]


def test_spotlight_records_recent_pick(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("display_state.get_redis", lambda decode_responses=True: fake)

    publish_state(build_state("sky blue", "118,215,234", mode="spotlight"))
    picks = get_recent_picks()

    assert len(picks) == 1
    assert picks[0]["color"] == "Sky Blue"
    assert picks[0]["rgb"] == [118, 215, 234]
