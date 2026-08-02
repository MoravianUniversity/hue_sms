from hue_sms.infrastructure.palette_repository import PaletteRepository

_palette = PaletteRepository()


def getFuzzyColor(color_name):
    return _palette.fuzzy_match(color_name)
