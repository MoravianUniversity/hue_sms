"""Redis access for color usage statistics."""

from config import get_redis

COLOR_TOTALS_KEY = "color_totals"
TOTAL_KEY = "total"


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class StatsRepository:
    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis()

    def increment(self, color_name):
        color_name = color_name.lower()
        if self.redis.hexists(COLOR_TOTALS_KEY, color_name):
            self.redis.hincrby(COLOR_TOTALS_KEY, color_name, 1)
            self.redis.incr(TOTAL_KEY, 1)

    def percent(self, color_name):
        color_name = color_name.lower()
        color_raw = self.redis.hget(COLOR_TOTALS_KEY, color_name)
        total_raw = self.redis.get(TOTAL_KEY)
        if color_raw is None or total_raw is None:
            return 0.0

        color_total = float(_decode(color_raw))
        total = float(_decode(total_raw))
        if total == 0:
            return 0.0
        return (color_total / total) * 100

    def total_choices(self):
        raw = self.redis.get(TOTAL_KEY)
        if raw is None:
            return 0
        return int(_decode(raw))

    def color_counts(self, palette_repo=None):
        """Return {color_key: count} for palette colors with count > 0."""
        if palette_repo is None:
            from palette_repository import PaletteRepository

            palette_repo = PaletteRepository(self.redis)

        counts = {}
        for key, value in self.redis.hgetall(COLOR_TOTALS_KEY).items():
            key = _decode(key)
            if palette_repo.exists(key):
                counts[key] = int(_decode(value))
        return counts
