from hue_sms.infrastructure.palette_repository import PaletteRepository

_palette = PaletteRepository()


def getColor(colorName):
    return _palette.get_rgb(colorName)
