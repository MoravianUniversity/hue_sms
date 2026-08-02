"""hue_sms — SMS-controlled Philips Hue light."""

import os
import sys

# Editable install adds src/ to sys.path, which shadows the vendored rgbxy package
# (src/rgbxy/ is a namespace stub; the module lives at src/rgbxy/rgbxy/).
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_PACKAGE_DIR)
_RGBXY = os.path.join(_SRC, "rgbxy")


def _fix_rgbxy_import_path():
    normalized = [os.path.abspath(p) for p in sys.path]
    for path in (_SRC, _RGBXY):
        while path in normalized:
            idx = normalized.index(path)
            sys.path.pop(idx)
            normalized.pop(idx)
    sys.path.insert(0, _SRC)
    sys.path.insert(0, _RGBXY)


_fix_rgbxy_import_path()
