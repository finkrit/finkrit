# finkrit
"""
The finkrit umbrella: the ``finkrit`` command and, when packaged, the bundle
that ships finagent, finkritserver, and the web app on top of finkritintel.

Run from a source checkout, the sub-packages live under packages/ and
services/api/, so they go on the import path here. Installed from a wheel they
are real siblings in site-packages and these inserts are harmless no-ops.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _sub in (_ROOT / "packages", _ROOT / "services" / "api"):
    if _sub.is_dir() and str(_sub) not in sys.path:
        sys.path.insert(0, str(_sub))
