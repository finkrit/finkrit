#!/usr/bin/env python3
# Thin shim kept for the run bootstrap. Insert the repo root so the finkrit
# package imports from a source checkout.
#
# Dispatches through finkrit.cli, the same entry point the installed `finkrit`
# command uses, rather than jumping straight to the web launcher. Going direct
# meant `./run cli` handed "cli" to the web app's argument parser as a stray
# flag, so a source checkout could reach the dashboard but never the terminal
# chat. With no subcommand finkrit.cli defaults to web, so `./run` and
# `./run --dev` behave exactly as before.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finkrit.cli import main

if __name__ == "__main__":
    main()
