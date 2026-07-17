import pytest

from color_resolver import (
    ColorResolver,
    COMMAND_BLACK,
    COMMAND_COLORS_LIST,
    COMMAND_CYCLE_UNAVAILABLE,
    COMMAND_EMPTY,
    COMMAND_OPTIONS,
    COMMAND_RANDOM_EMPTY,
    ERROR_UNKNOWN,
    ERROR_UNSUPPORTED,
    MATCH_CYCLE,
    MATCH_EXACT,
    MATCH_FUZZY,
    MATCH_HEX,
    MATCH_RANDOM,
    ResolutionError,
    ResolvedColor,
    SpecialCommand,
    hex_to_rgb,
)

PALETTE = ["sky blue", "magenta", "goldenrod"]
RGB = {
    "sky blue": "118,215,234",
    "magenta": "255,89,173",
    "goldenrod": "255,216,105",
}


class FakeDatabase:
    def hkeys(self, name):
        if name == "colors":
            return list(PALETTE) + ["random"]
        return []


@pytest.fixture
def resolver():
    return ColorResolver(
        get_palette_names_fn=lambda _db: list(PALETTE),
        get_rgb_fn=lambda name: RGB.get(name),
        fuzzy_match_fn=lambda name: "sky blue" if name == "skyblue" else None,
        advance_cycle_fn=lambda: "magenta",
        random_choice_fn=lambda choices: "goldenrod",
    )


def test_hex_to_rgb_parses_six_digit_hex():
    assert hex_to_rgb("#FF2A45") == "255,42,69"


def test_hex_to_rgb_returns_none_for_invalid():
    assert hex_to_rgb("#GGGGGG") is None


def test_empty_input_returns_empty_command(resolver):
    result = resolver.resolve("", FakeDatabase())
    assert result == SpecialCommand(COMMAND_EMPTY, "")


def test_black_returns_black_command(resolver):
    result = resolver.resolve("black", FakeDatabase())
    assert result == SpecialCommand(COMMAND_BLACK, "black")


def test_options_returns_options_command(resolver):
    result = resolver.resolve("Options", FakeDatabase())
    assert result == SpecialCommand(COMMAND_OPTIONS, "Options")


def test_colors_list_returns_colors_list_command(resolver):
    result = resolver.resolve("Colors List", FakeDatabase())
    assert result == SpecialCommand(COMMAND_COLORS_LIST, "Colors List")


def test_exact_palette_match(resolver):
    result = resolver.resolve("Sky Blue", FakeDatabase())
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "sky blue"
    assert result.rgb == "118,215,234"
    assert result.match_kind == MATCH_EXACT
    assert result.stat_key == "sky blue"
    assert result.increment_stats is True


def test_fuzzy_match(resolver):
    result = resolver.resolve("skyblue", FakeDatabase())
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "sky blue"
    assert result.match_kind == MATCH_FUZZY


def test_hex_color(resolver):
    result = resolver.resolve("#FF2A45", FakeDatabase())
    assert isinstance(result, ResolvedColor)
    assert result.rgb == "255,42,69"
    assert result.match_kind == MATCH_HEX
    assert result.display_name == "#FF2A45"
    assert result.increment_stats is False


def test_random_picks_from_palette(resolver):
    result = resolver.resolve("random", FakeDatabase())
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "goldenrod"
    assert result.match_kind == MATCH_RANDOM
    assert result.stat_key == "random"


def test_cycle_advances(resolver):
    result = resolver.resolve("next", FakeDatabase())
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "magenta"
    assert result.match_kind == MATCH_CYCLE


def test_unknown_color(resolver):
    result = resolver.resolve("not-a-real-color", FakeDatabase())
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNKNOWN


def test_unsupported_name_heuristic(resolver):
    result = resolver.resolve("eerie black", FakeDatabase())
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNSUPPORTED


def test_excluded_hex_color(resolver):
    result = resolver.resolve("#808080", FakeDatabase())
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNSUPPORTED


def test_random_empty_palette():
    empty_resolver = ColorResolver(
        get_palette_names_fn=lambda _db: [],
        get_rgb_fn=lambda name: None,
        random_choice_fn=lambda choices: choices[0],
    )
    result = empty_resolver.resolve("random", FakeDatabase())
    assert result == SpecialCommand(COMMAND_RANDOM_EMPTY, "random")


def test_cycle_unavailable():
    failing_resolver = ColorResolver(
        get_palette_names_fn=lambda _db: list(PALETTE),
        get_rgb_fn=lambda name: RGB.get(name),
        advance_cycle_fn=lambda: (_ for _ in ()).throw(ValueError("empty")),
    )
    result = failing_resolver.resolve("cycle", FakeDatabase())
    assert result == SpecialCommand(COMMAND_CYCLE_UNAVAILABLE, "cycle")
