"""Redis access for the color palette."""

import redis
from thefuzz import fuzz, process

from hue_sms.config import get_redis
from hue_sms.domain.hue_color import is_excluded_palette_color
from hue_sms.domain.name_converter import clean_name

COLORS_KEY = "colors"
SKIP_NAMES = ("random", "black")
FUZZY_MATCH_THRESHOLD = 85


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class PaletteRepository:
    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis()

    def get_rgb(self, color_name):
        value = self.redis.hget(COLORS_KEY, clean_name(str(color_name)))
        return _decode(value) if value is not None else None

    def exists(self, color_name):
        return self.redis.hexists(COLORS_KEY, clean_name(str(color_name)))

    def list_names(self):
        names = []
        for color in self.redis.hkeys(COLORS_KEY):
            color = _decode(color)
            if color not in SKIP_NAMES:
                names.append(color)
        return names

    def list_showable_names(self):
        return sorted(
            name
            for name in self.list_names()
            if not self._is_excluded(name)
        )

    def fuzzy_match(self, color_name):
        names = self.list_names()
        if not names:
            return None
        try:
            match = process.extractOne(
                color_name.title(), names, scorer=fuzz.token_sort_ratio
            )
        except redis.RedisError:
            return None
        if match is None:
            return None
        matched_name, score = match[0], match[1]
        if score >= FUZZY_MATCH_THRESHOLD:
            return matched_name
        return None

    def all_colors(self):
        """Return name → rgb mapping for kiosk palette API."""
        try:
            colors = self.redis.hgetall(COLORS_KEY)
        except redis.RedisError:
            return {}
        if not colors:
            return {}
        decoded = {}
        for name, rgb in colors.items():
            decoded[_decode(name)] = _decode(rgb)
        return decoded

    def _is_excluded(self, name):
        rgb = self.get_rgb(name)
        if rgb is None:
            return True
        red, green, blue = (int(v) for v in rgb.split(","))
        return is_excluded_palette_color(red, green, blue)
