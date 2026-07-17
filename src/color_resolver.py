"""Resolve SMS color input into palette matches, hex values, or errors."""

import random
from dataclasses import dataclass

from PIL import ImageColor

from display_state import advance_cycle_color, is_likely_unsupported_color_name
from fuzzyColors import getFuzzyColor
from getRedisColor import getColor
from hue_color import is_excluded_palette_color, parse_rgb_values
from name_converter import clean_name

MATCH_EXACT = "exact"
MATCH_FUZZY = "fuzzy"
MATCH_HEX = "hex"
MATCH_RANDOM = "random"
MATCH_CYCLE = "cycle"

COMMAND_EMPTY = "empty"
COMMAND_BLACK = "black"
COMMAND_OPTIONS = "options"
COMMAND_COLORS_LIST = "colors_list"
COMMAND_RANDOM_EMPTY = "random_empty"
COMMAND_CYCLE_UNAVAILABLE = "cycle_unavailable"

ERROR_UNKNOWN = "unknown"
ERROR_UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ResolvedColor:
    """A showable color ready for the bulb and kiosk."""

    color_key: str
    display_name: str
    rgb: str
    match_kind: str
    raw_input: str
    stat_key: str
    increment_stats: bool = True


@dataclass(frozen=True)
class ResolutionError:
    """Input could not be turned into a showable color."""

    reason: str
    color_key: str
    raw_input: str


@dataclass(frozen=True)
class SpecialCommand:
    """Non-color SMS commands handled before bulb control."""

    command: str
    raw_input: str


def hex_to_rgb(hexcode_color):
    try:
        red, green, blue = ImageColor.getcolor(hexcode_color, "RGB")
        return "{},{},{}".format(red, green, blue)
    except ValueError:
        return None


def get_palette_names(database):
    names = []
    for color in database.hkeys("colors"):
        if isinstance(color, bytes):
            color = color.decode("utf-8")
        if color not in ("random", "black"):
            names.append(color)
    return names


class ColorResolver:
    def __init__(
        self,
        get_palette_names_fn=None,
        get_rgb_fn=None,
        fuzzy_match_fn=None,
        advance_cycle_fn=None,
        random_choice_fn=None,
    ):
        self._get_palette_names = get_palette_names_fn or get_palette_names
        self._get_rgb = get_rgb_fn or getColor
        self._fuzzy_match = fuzzy_match_fn or getFuzzyColor
        self._advance_cycle = advance_cycle_fn or advance_cycle_color
        self._random_choice = random_choice_fn or random.choice

    def resolve(self, raw_input, database):
        raw_input = raw_input or ""
        is_hex = raw_input.startswith("#")
        color_name = clean_name(raw_input)

        if not color_name:
            return SpecialCommand(COMMAND_EMPTY, raw_input)

        if color_name == "black":
            return SpecialCommand(COMMAND_BLACK, raw_input)

        if color_name == "options":
            return SpecialCommand(COMMAND_OPTIONS, raw_input)

        if color_name == "colors list":
            return SpecialCommand(COMMAND_COLORS_LIST, raw_input)

        palette_names = self._get_palette_names(database)
        match_kind = MATCH_EXACT

        if color_name in ("next", "cycle"):
            try:
                color_name = self._advance_cycle()
            except ValueError:
                return SpecialCommand(COMMAND_CYCLE_UNAVAILABLE, raw_input)
            match_kind = MATCH_CYCLE
        elif color_name == "random":
            pickable = [name for name in palette_names if name != "random"]
            if not pickable:
                return SpecialCommand(COMMAND_RANDOM_EMPTY, raw_input)
            color_name = self._random_choice(pickable)
            match_kind = MATCH_RANDOM
        elif color_name not in palette_names:
            fuzzy_match = self._fuzzy_match(color_name)
            if fuzzy_match is not None:
                color_name = clean_name(fuzzy_match)
                match_kind = MATCH_FUZZY

        if is_hex:
            rgb_values = hex_to_rgb(raw_input)
            match_kind = MATCH_HEX
        else:
            rgb_values = self._get_rgb(color_name)

        if rgb_values is None:
            reason = (
                ERROR_UNSUPPORTED
                if is_likely_unsupported_color_name(color_name)
                else ERROR_UNKNOWN
            )
            return ResolutionError(reason, color_name, raw_input)

        red, green, blue = parse_rgb_values(rgb_values)
        if is_excluded_palette_color(red, green, blue):
            return ResolutionError(ERROR_UNSUPPORTED, color_name, raw_input)

        display_name = raw_input if is_hex else clean_name(color_name)
        stat_key = self._stat_key(color_name, match_kind, is_hex, display_name)
        increment_stats = match_kind != MATCH_HEX

        return ResolvedColor(
            color_key=clean_name(color_name),
            display_name=display_name,
            rgb=rgb_values if isinstance(rgb_values, str) else rgb_values.decode("utf-8"),
            match_kind=match_kind,
            raw_input=raw_input,
            stat_key=stat_key,
            increment_stats=increment_stats,
        )

    @staticmethod
    def _stat_key(color_name, match_kind, is_hex, display_name):
        if match_kind == MATCH_RANDOM:
            return "random"
        if is_hex:
            return display_name
        return clean_name(color_name)
