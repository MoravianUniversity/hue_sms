"""Convert sRGB palette values to Philips Hue xy + brightness."""

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

    if is_neutral(r, g, b):
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

    return converter.color.get_rgb_from_xy_and_brightness(x, y, 1.0)
