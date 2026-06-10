#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolutor de fuentes portable para el carrusel y el reel.
Busca Poppins en: ./fonts -> sistema -> la descarga de Google Fonts.
Si todo falla, cae a DejaVu (incluida con matplotlib). Asi funciona
igual en tu PC, en el sandbox o en GitHub Actions.
"""
import os
import urllib.request
from PIL import ImageFont

_LOCAL = "fonts"
_SYS = "/usr/share/fonts/truetype/google-fonts"
_BASE = "https://github.com/google/fonts/raw/main/ofl/poppins/"
_cache = {}

F_BOLD = "Poppins-Bold.ttf"
F_MED = "Poppins-Medium.ttf"
F_REG = "Poppins-Regular.ttf"
F_LIGHT = "Poppins-Light.ttf"


def _resolve(fname):
    for base in (_LOCAL, _SYS):
        p = os.path.join(base, fname)
        if os.path.exists(p):
            return p
    # descargar a ./fonts
    try:
        os.makedirs(_LOCAL, exist_ok=True)
        p = os.path.join(_LOCAL, fname)
        req = urllib.request.Request(_BASE + fname, headers={"User-Agent": "font-fetch"})
        data = urllib.request.urlopen(req, timeout=30).read()
        with open(p, "wb") as f:
            f.write(data)
        return p
    except Exception:
        pass
    # fallback DejaVu (viene con matplotlib)
    try:
        import matplotlib
        d = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        alt = "DejaVuSans-Bold.ttf" if "Bold" in fname else "DejaVuSans.ttf"
        return os.path.join(d, alt)
    except Exception:
        return None


def font(fname, size):
    key = (fname, size)
    if key not in _cache:
        path = _resolve(fname)
        _cache[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    return _cache[key]
