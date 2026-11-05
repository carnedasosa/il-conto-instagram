#!/usr/bin/env python3
"""Converte le copertine PNG in JPEG per l'API di Instagram (che non accetta PNG).

Uso (dalla radice di il-conto-instagram):
  python pubblicazione/png2jpg.py percorso/copertina.png [altri.png ...]
Scrive in pubblicazione/jpg/. Serve Pillow: pip install pillow
(Le copertine degli episodi sono già JPEG: carica.py le copia da sé e converte solo se trova un PNG.)
"""
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
files = [Path(a) for a in sys.argv[1:]]
if not files:
    sys.exit("Indica almeno un file PNG.")
out = HERE / "jpg"
out.mkdir(exist_ok=True)
for f in files:
    dest = out / (f.stem + ".jpg")
    Image.open(f).convert("RGB").save(dest, "JPEG", quality=92, optimize=True, progressive=True)
    print(f"ok  {dest.relative_to(HERE.parent)}")
