"""Pytest bootstrap: avoid rgbxy namespace shadowing from editable src/ on sys.path."""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC = os.path.join(_ROOT, "src")
_RGBXY = os.path.join(_SRC, "rgbxy")


def _fix_import_path():
    normalized = [os.path.abspath(p) for p in sys.path]
    for path in (_SRC, _RGBXY):
        while path in normalized:
            idx = normalized.index(path)
            sys.path.pop(idx)
            normalized.pop(idx)
    sys.path.insert(0, _SRC)
    sys.path.insert(0, _RGBXY)


_fix_import_path()
