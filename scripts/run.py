#!/usr/bin/env python3
# Thin shim kept for the run bootstrap. The launcher lives in finkrit.web now.
# Insert the repo root so the finkrit package imports from a source checkout.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finkrit.web import main

if __name__ == "__main__":
    main()
