"""Entry point for the packaged executable."""

import sys

from valinfo.cli import main

if __name__ == "__main__":
    code = main()
    # A double-clicked console window would vanish on error, so hold it open.
    if code not in (0, 130) and sys.stdout is not None and sys.stdout.isatty():
        input("\nPress Enter to close...")
    raise SystemExit(code)
