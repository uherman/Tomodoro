"""macOS keyboard backlight control via CoreBrightness private framework."""
from __future__ import annotations

import ctypes
import ctypes.util

_client = None
_kbd_id: int | None = None


def _load() -> tuple:
    """Initialise the ObjC KeyboardBrightnessClient singleton."""
    global _client, _kbd_id
    if _client is not None:
        return _client, _kbd_id

    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    ctypes.cdll.LoadLibrary(
        "/System/Library/PrivateFrameworks/CoreBrightness.framework/CoreBrightness"
    )

    cls = objc.objc_getClass(b"KeyboardBrightnessClient")
    inst = objc.objc_msgSend(cls, objc.sel_registerName(b"alloc"))
    inst = objc.objc_msgSend(inst, objc.sel_registerName(b"init"))

    ids = objc.objc_msgSend(inst, objc.sel_registerName(b"copyKeyboardBacklightIDs"))

    objc.objc_msgSend.restype = ctypes.c_uint64
    count = objc.objc_msgSend(ids, objc.sel_registerName(b"count"))
    if count == 0:
        raise RuntimeError("No keyboard backlight found")

    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64]
    kbd_obj = objc.objc_msgSend(ids, objc.sel_registerName(b"objectAtIndex:"), 0)

    objc.objc_msgSend.restype = ctypes.c_int64
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kbd_int = objc.objc_msgSend(kbd_obj, objc.sel_registerName(b"longLongValue"))

    # Build typed function pointers for float-returning / float-accepting calls
    _get_fn = ctypes.CFUNCTYPE(
        ctypes.c_float, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64
    )(("objc_msgSend", objc))
    _set_fn = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_int64
    )(("objc_msgSend", objc))

    _client = (inst, objc, _get_fn, _set_fn)
    _kbd_id = kbd_int
    return _client, _kbd_id


def get_keyboard_brightness() -> float:
    """Return current keyboard backlight brightness (0.0 – 1.0)."""
    try:
        (inst, objc, get_fn, _), kbd_id = _load()
        sel = objc.sel_registerName(b"brightnessForKeyboard:")
        return get_fn(inst, sel, kbd_id)
    except Exception:
        return 0.0


def set_keyboard_brightness(value: float) -> None:
    """Set keyboard backlight brightness (0.0 – 1.0)."""
    try:
        (inst, objc, _, set_fn), kbd_id = _load()
        sel = objc.sel_registerName(b"setBrightness:forKeyboard:")
        set_fn(inst, sel, value, kbd_id)
    except Exception:
        pass
