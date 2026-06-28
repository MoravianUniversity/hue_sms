import math

from hue_color import adjust_rgb_for_hue, get_gamut, is_neutral, preview_rgb, rgb_to_hue
from rgbxy import GamutC


def test_get_gamut_defaults_to_c():
    assert get_gamut() is GamutC


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


def test_rgb_to_hue_scales_neutral_brightness():
    _, _, bri, _ = rgb_to_hue(103, 103, 103)
    assert bri == 103


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
