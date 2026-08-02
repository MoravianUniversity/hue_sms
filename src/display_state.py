import re
import time

from display_repository import DISPLAY_CHANNEL, DisplayRepository
from stats_repository import StatsRepository

RECENT_PICKS_LIMIT = 8
UNSUPPORTED_NAME_PATTERN = re.compile(
    r"\b(black|gray|grey|silver|charcoal|onyx|eerie|smoke|granite|"
    r"brown|tan|beaver|lumber|sienna|umber|sepia|mahogany|tumbleweed|"
    r"peach|apricot|almond|copper|bronze|beige|wood|dirt|earthworm|cedar|"
    r"fuzzy wuzzy|desert sand|raw sienna|burnt sienna|van dyke)\b",
    re.IGNORECASE,
)

_default_display_repo = None
_default_stats_repo = None


def _display_repo():
    global _default_display_repo
    if _default_display_repo is None:
        _default_display_repo = DisplayRepository()
    return _default_display_repo


def _stats_repo():
    global _default_stats_repo
    if _default_stats_repo is None:
        _default_stats_repo = StatsRepository()
    return _default_stats_repo


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


def is_likely_unsupported_color_name(color_name):
    return bool(UNSUPPORTED_NAME_PATTERN.search(color_name.replace("-", " ")))


def build_unsupported_state(color_name, subtitle=None):
    display_name = color_name.replace("-", " ").title()
    return {
        "color_name": display_name,
        "color_key": color_name.lower().strip(),
        "mode": "unsupported",
        "subtitle": subtitle or "Can't show on the light",
        "message": "That color can't be shown on the Hue bulb — try a brighter, more vivid color!",
        "timestamp": time.time(),
    }


def publish_unsupported_color(color_name, subtitle=None):
    publish_state(build_unsupported_state(color_name, subtitle=subtitle))


def publish_state(state):
    _display_repo().publish(state)


def get_display_state():
    return _display_repo().get_state()


def get_recent_picks():
    return _display_repo().get_recent_picks()


def get_total_choices():
    return _stats_repo().total_choices()


def advance_cycle_color():
    return _display_repo().advance_cycle()
