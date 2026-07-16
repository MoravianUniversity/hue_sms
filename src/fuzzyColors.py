from thefuzz import fuzz, process

from config import get_redis
import redis


def _load_color_names():
    client = get_redis()
    try:
        names = []
        for color in client.hkeys("colors"):
            if isinstance(color, bytes):
                color = color.decode("utf-8")
            if color not in ("random", "black"):
                names.append(color)
        return names
    except redis.RedisError:
        return []


def getFuzzyColor(color_name):
    colors_list = _load_color_names()
    if not colors_list:
        return None
    fuzzy_match = process.extractOne(
        color_name.title(), colors_list, scorer=fuzz.token_sort_ratio
    )
    fuzz_color, percent_match = fuzzy_match[0], fuzzy_match[1]
    if percent_match >= 85:
        return fuzz_color
    return None
