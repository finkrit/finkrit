# finkrit/cli.py
"""
The finkrit command: a thin dispatcher over the sub-tools.

    finkrit            start the web app (dashboard plus API)
    finkrit web        the same, explicit
    finkrit cli        chat with the agent in the terminal

Flags after the subcommand pass straight through, for example
``finkrit --dev`` or ``finkrit cli --file my.csv``.
"""
from __future__ import annotations

import sys

_USAGE = (
    "Usage: finkrit [web|cli] [flags]\n"
    "  finkrit            start the web app (dashboard plus API)\n"
    "  finkrit cli        chat with the agent in the terminal\n"
    "\n"
    "Flags pass through, for example finkrit --dev or finkrit cli --file my.csv"
)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else list(argv)
    command = argv[0] if argv else "web"

    if command in ("-h", "--help", "help"):
        print(_USAGE)
        return
    if command == "cli":
        from finagent.cli import main as cli_main
        cli_main(argv[1:])
        return
    if command == "web":
        from finkrit.web import main as web_main
        web_main(argv[1:])
        return

    # No subcommand, just leading flags. Default to the web app, pass all args.
    from finkrit.web import main as web_main
    web_main(argv)


if __name__ == "__main__":
    main()
