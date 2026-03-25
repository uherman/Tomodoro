"""macOS display brightness control via private DisplayServices framework."""
from __future__ import annotations

import ctypes
import ctypes.util

_lib = None


def _load() -> ctypes.CDLL:
    global _lib
    if _lib is None:
        _lib = ctypes.cdll.LoadLibrary(
            "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
        )
        cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
        cg.CGMainDisplayID.restype = ctypes.c_uint32
        _lib._main_display = cg.CGMainDisplayID()
    return _lib


def get_brightness() -> float:
    """Return current brightness as a float 0.0 – 1.0."""
    try:
        lib = _load()
        val = ctypes.c_float()
        lib.DisplayServicesGetBrightness(lib._main_display, ctypes.byref(val))
        return val.value
    except Exception:
        return 1.0


def set_brightness(value: float) -> None:
    """Set display brightness (0.0 – 1.0)."""
    try:
        lib = _load()
        lib.DisplayServicesSetBrightness(lib._main_display, ctypes.c_float(value))
    except Exception:
        pass
