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


class FakePalette:
    def list_names(self):
        return list(PALETTE)

    def get_rgb(self, name):
        return RGB.get(name)

    def fuzzy_match(self, name):
        return "sky blue" if name == "skyblue" else None


class FakeDisplay:
    def advance_cycle(self):
        return "magenta"


@pytest.fixture
def resolver():
    return ColorResolver(
        palette_repo=FakePalette(),
        display_repo=FakeDisplay(),
        random_choice_fn=lambda choices: "goldenrod",
    )


def test_hex_to_rgb_parses_six_digit_hex():
    assert hex_to_rgb("#FF2A45") == "255,42,69"


def test_hex_to_rgb_returns_none_for_invalid():
    assert hex_to_rgb("#GGGGGG") is None


def test_empty_input_returns_empty_command(resolver):
    result = resolver.resolve("")
    assert result == SpecialCommand(COMMAND_EMPTY, "")


def test_black_returns_black_command(resolver):
    result = resolver.resolve("black")
    assert result == SpecialCommand(COMMAND_BLACK, "black")


def test_options_returns_options_command(resolver):
    result = resolver.resolve("Options")
    assert result == SpecialCommand(COMMAND_OPTIONS, "Options")


def test_colors_list_returns_colors_list_command(resolver):
    result = resolver.resolve("Colors List")
    assert result == SpecialCommand(COMMAND_COLORS_LIST, "Colors List")


def test_exact_palette_match(resolver):
    result = resolver.resolve("Sky Blue")
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "sky blue"
    assert result.rgb == "118,215,234"
    assert result.match_kind == MATCH_EXACT
    assert result.stat_key == "sky blue"
    assert result.increment_stats is True


def test_fuzzy_match(resolver):
    result = resolver.resolve("skyblue")
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "sky blue"
    assert result.match_kind == MATCH_FUZZY


def test_hex_color(resolver):
    result = resolver.resolve("#FF2A45")
    assert isinstance(result, ResolvedColor)
    assert result.rgb == "255,42,69"
    assert result.match_kind == MATCH_HEX
    assert result.display_name == "#FF2A45"
    assert result.increment_stats is False


def test_random_picks_from_palette(resolver):
    result = resolver.resolve("random")
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "goldenrod"
    assert result.match_kind == MATCH_RANDOM
    assert result.stat_key == "random"


def test_cycle_advances(resolver):
    result = resolver.resolve("next")
    assert isinstance(result, ResolvedColor)
    assert result.color_key == "magenta"
    assert result.match_kind == MATCH_CYCLE


def test_unknown_color(resolver):
    result = resolver.resolve("not-a-real-color")
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNKNOWN


def test_unsupported_name_heuristic(resolver):
    result = resolver.resolve("eerie black")
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNSUPPORTED


def test_excluded_hex_color(resolver):
    result = resolver.resolve("#808080")
    assert isinstance(result, ResolutionError)
    assert result.reason == ERROR_UNSUPPORTED


def test_random_empty_palette():
    empty_resolver = ColorResolver(
        palette_repo=_EmptyPalette(),
        display_repo=FakeDisplay(),
        random_choice_fn=lambda choices: choices[0],
    )
    result = empty_resolver.resolve("random")
    assert result == SpecialCommand(COMMAND_RANDOM_EMPTY, "random")


def test_cycle_unavailable():
    failing_resolver = ColorResolver(
        palette_repo=FakePalette(),
        display_repo=_FailingDisplay(),
    )
    result = failing_resolver.resolve("cycle")
    assert result == SpecialCommand(COMMAND_CYCLE_UNAVAILABLE, "cycle")


class _EmptyPalette(FakePalette):
    def list_names(self):
        return []


class _FailingDisplay:
    def advance_cycle(self):
        raise ValueError("empty")
