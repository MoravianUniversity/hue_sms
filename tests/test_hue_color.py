import math

from hue_color import adjust_rgb_for_hue, get_gamut, is_earth_tone, is_excluded_palette_color, is_neutral, parse_rgb_values, preview_rgb, rgb_to_hue
from rgbxy import GamutC


def test_get_gamut_defaults_to_c():
    assert get_gamut() is GamutC


def test_parse_rgb_values_handles_bytes():
    assert parse_rgb_values(b"255,42,69") == (255, 42, 69)


def test_is_excluded_palette_color():
    assert is_excluded_palette_color(0, 0, 0)
    assert is_excluded_palette_color(27, 27, 27)
    assert not is_excluded_palette_color(255, 255, 255)
    assert is_excluded_palette_color(103, 103, 103)
    assert is_excluded_palette_color(146, 112, 93)  # Beaver
    assert is_excluded_palette_color(255, 214, 178)  # Lumber
    assert is_excluded_palette_color(175, 91, 65)  # Brown
    assert not is_excluded_palette_color(255, 42, 69)  # Red
    assert not is_excluded_palette_color(255, 192, 203)  # Pink


def test_is_neutral_detects_grays():
    assert is_neutral(120, 120, 120)
    assert not is_neutral(120, 160, 120)


def test_rgb_to_hue_sets_white_saturation_to_zero():
    x, y, bri, saturation = rgb_to_hue(255, 255, 255)
    assert saturation == 0
    assert bri == 254


def test_rgb_to_hue_uses_full_brightness_for_chromatic_colors():
    _, _, bri, saturation = rgb_to_hue(118, 215, 234)
    assert bri == 254
    assert saturation == 255


def test_is_earth_tone_detects_brown():
    assert is_earth_tone(175, 89, 62)
    assert is_earth_tone(255, 214, 178)  # Lumber
    assert not is_earth_tone(255, 136, 100)  # Orange
    assert not is_earth_tone(255, 192, 203)  # Pink


def test_rgb_to_hue_keeps_pink_chromaticity():
    x, y, bri, saturation = rgb_to_hue(255, 192, 203)
    assert x > 0.38
    assert y < 0.35
    assert bri == 254
    assert saturation == 255


def test_muted_warm_tone_excludes_beaver_not_red():
    from hue_color import is_muted_warm_tone
    assert is_muted_warm_tone(146, 112, 93)
    assert not is_muted_warm_tone(255, 42, 69)


def test_preview_rgb_matches_round_trip_for_sky_blue():
    preview = preview_rgb(118, 215, 234)
    round_trip = preview_rgb(*preview)
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(preview, round_trip)))
    assert distance < 2
    _, _, bri, _ = rgb_to_hue(*preview)
    assert bri > 200


def test_adjust_rgb_for_hue_skips_black():
    assert adjust_rgb_for_hue(0, 0, 0) is None


def test_adjusted_rgb_is_reproducible_on_bulb():
    original = (0, 204, 153)
    adjusted = adjust_rgb_for_hue(*original)
    preview = preview_rgb(*adjusted)
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(adjusted, preview)))
    assert distance < 2
