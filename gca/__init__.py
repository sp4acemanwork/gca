"""gca - terminal algebra drill trainer tuned for combinatorics coursework."""

from __future__ import annotations

import argparse
import random
import sys
from typing import Sequence

from gca.app import GcaApp

__version__ = "0.1.0"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gca",
        description="Terminal algebra drill trainer tuned for combinatorics coursework.",
    )
    parser.add_argument("--seed", type=int, default=None, help="seed the session RNG")
    parser.add_argument("--version", action="version", version=f"gca {__version__}")
    args = parser.parse_args(argv)

    app = GcaApp(seed=args.seed)
    try:
        app.run()
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
