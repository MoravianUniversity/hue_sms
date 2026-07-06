"""Convert sRGB palette values to Philips Hue xy + brightness."""

import colorsys

from rgbxy import Converter, GamutA, GamutB, GamutC

GAMUTS = {
    "A": GamutA,
    "B": GamutB,
    "C": GamutC,
}

DEFAULT_GAMUT = "C"
NEUTRAL_THRESHOLD = 30
MIN_CHROMATIC_CHANNEL = 70
FULL_BRIGHTNESS = 254


def get_gamut(name=None):
    key = (name or DEFAULT_GAMUT).upper()
    if key not in GAMUTS:
        raise ValueError("Unknown hue gamut {!r}. Use one of: A, B, C.".format(name))
    return GAMUTS[key]


def is_neutral(r, g, b, threshold=NEUTRAL_THRESHOLD):
    return max(r, g, b) - min(r, g, b) <= threshold


def is_excluded_palette_color(r, g, b):
    """Colors that cannot be reproduced well on a Hue bulb."""
    if (r, g, b) == (0, 0, 0):
        return True
    if max(r, g, b) >= 250 and is_neutral(r, g, b):
        return False
    if is_neutral(r, g, b):
        return True
    return is_muted_warm_tone(r, g, b)


def is_muted_warm_tone(r, g, b):
    """Browns, tans, and warm pastels that skew pink or salmon on Hue bulbs."""
    if is_neutral(r, g, b):
        return False
    hue, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if not (0.02 <= hue <= 0.12) or saturation < 0.12:
        return False
    if saturation <= 0.45:
        return True
    if saturation <= 0.70 and value < 0.90:
        return True
    return False


def parse_rgb_values(rgb_values):
    if isinstance(rgb_values, bytes):
        rgb_values = rgb_values.decode("utf-8")
    return tuple(int(v) for v in rgb_values.split(","))


def is_earth_tone(r, g, b):
    """Warm browns and tans (same band as muted_warm_tone; kept for brightness tuning)."""
    return is_muted_warm_tone(r, g, b)


def _tune_earth_tone_rgb(r, g, b):
    """Shift warm browns toward yellow and reduce saturation for Hue bulbs."""
    hue, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    hue = min(hue + 0.02, 0.11)
    saturation = min(saturation * 0.75, 0.55)
    red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
    return (
        min(255, int(round(red * 255))),
        min(255, int(round(green * 255))),
        min(255, int(round(blue * 255))),
    )


def _earth_tone_brightness(r, g, b):
    peak = max(r, g, b)
    _, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    bri = max(1, round(peak / 255.0 * FULL_BRIGHTNESS))
    if value >= 0.85 and saturation <= 0.42:
        bri = max(1, round(bri * 0.72))
    return bri


def _earth_tone_hue_settings(r, g, b, gamut=GamutC):
    converter = Converter(gamut)
    tuned = _tune_earth_tone_rgb(r, g, b)
    x, y = converter.rgb_to_xy(*tuned)
    bri = _earth_tone_brightness(*tuned)
    return tuned, x, y, bri


def _uses_scaled_brightness(r, g, b):
    return is_neutral(r, g, b) or is_earth_tone(r, g, b)


def _brightness_from_rgb(r, g, b):
    peak = max(r, g, b)
    if peak == 0:
        return 1
    return max(1, round(peak / 255.0 * FULL_BRIGHTNESS))


def _boost_dark_chromatic(r, g, b, minimum=MIN_CHROMATIC_CHANNEL):
    peak = max(r, g, b)
    if peak == 0 or peak >= minimum or is_neutral(r, g, b):
        return r, g, b
    scale = minimum / float(peak)
    return (
        min(255, int(round(r * scale))),
        min(255, int(round(g * scale))),
        min(255, int(round(b * scale))),
    )


def rgb_to_hue(r, g, b, gamut=GamutC):
    """Return xy chromaticity, Hue brightness (1-254), and saturation for the bulb."""
    converter = Converter(gamut)
    if (r, g, b) == (255, 255, 255):
        x, y = converter.rgb_to_xy(r, g, b)
        return x, y, FULL_BRIGHTNESS, 0

    if _uses_scaled_brightness(r, g, b):
        if is_earth_tone(r, g, b):
            _, x, y, bri = _earth_tone_hue_settings(r, g, b, gamut=gamut)
            return x, y, bri, 255
        x, y = converter.rgb_to_xy(r, g, b)
        return x, y, _brightness_from_rgb(r, g, b), 255

    x, y = converter.rgb_to_xy(r, g, b)
    return x, y, FULL_BRIGHTNESS, 255


def preview_rgb(r, g, b, gamut=GamutC):
    """Return the RGB color the bulb should look like at the chosen brightness."""
    if (r, g, b) == (0, 0, 0):
        return (0, 0, 0)
    if (r, g, b) == (255, 255, 255) or is_neutral(r, g, b):
        return (r, g, b)
    if is_earth_tone(r, g, b):
        converter = Converter(gamut)
        _, x, y, bri = _earth_tone_hue_settings(r, g, b, gamut=gamut)
        return converter.color.get_rgb_from_xy_and_brightness(x, y, bri / FULL_BRIGHTNESS)

    converter = Converter(gamut)
    x, y, bri, _ = rgb_to_hue(r, g, b, gamut=gamut)
    return converter.color.get_rgb_from_xy_and_brightness(x, y, bri / FULL_BRIGHTNESS)


def adjust_rgb_for_hue(r, g, b, gamut=GamutC):
    """Map a palette RGB value to the closest reproducible color for kiosk + bulb."""
    if (r, g, b) == (0, 0, 0):
        return None

    converter = Converter(gamut)
    r, g, b = _boost_dark_chromatic(r, g, b)
    x, y = converter.rgb_to_xy(r, g, b)

    if is_neutral(r, g, b):
        return (r, g, b)

    if is_earth_tone(r, g, b):
        converter = Converter(gamut)
        _, x, y, bri = _earth_tone_hue_settings(r, g, b, gamut=gamut)
        preview = converter.color.get_rgb_from_xy_and_brightness(x, y, bri / FULL_BRIGHTNESS)
        target_peak = max(r, g, b)
        preview_peak = max(preview)
        if preview_peak > target_peak:
            scale = target_peak / float(preview_peak)
            preview = tuple(min(255, int(round(channel * scale))) for channel in preview)
        return preview

    return converter.color.get_rgb_from_xy_and_brightness(x, y, 1.0)
