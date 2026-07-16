from config import get_redis
from name_converter import clean_name


def getColor(colorName):
    r = get_redis()
    value = r.hget("colors", clean_name(str(colorName)))
    return value
