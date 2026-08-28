#!/usr/bin/env python3
"""Generate the animated miner contribution graph.

    python3 generate_miner.py --user Efti-Hasan          # needs GITHUB_TOKEN
    python3 generate_miner.py --demo                     # offline preview
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
from pathlib import Path

from miner import contributions, render, route


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a GitHub contribution calendar as an animated mine."
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""),
        help="GitHub login to read contributions for",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="token with read access to the user's contributions",
    )
    parser.add_argument("--out", default="github-miner.svg", help="dark theme output path")
    parser.add_argument(
        "--out-light", default="github-miner-light.svg", help="light theme output path"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="use synthetic contributions instead of calling the API",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)

    if args.demo:
        calendar = contributions.demo()
        login = args.user or "demo"
    else:
        if not args.user:
            print("error: --user is required (or set GITHUB_REPOSITORY_OWNER)", file=sys.stderr)
            return 2
        if not args.token:
            print("error: --token is required (or set GITHUB_TOKEN)", file=sys.stderr)
            return 2
        try:
            calendar = contributions.fetch(args.user, args.token)
        except (urllib.error.URLError, RuntimeError, OSError) as error:
            print(f"error: could not read contributions: {error}", file=sys.stderr)
            return 1
        login = args.user

    plan = route.build(calendar)
    timing = render.Timing(steps=len(plan))

    outputs = ((args.out, "dark"), (args.out_light, "light"))
    for path, theme in outputs:
        if not path:
            continue
        svg = render.render(calendar, plan, render.PALETTES[theme], login=login)
        Path(path).write_text(svg, encoding="utf-8")
        print(f"{path}: {len(svg) / 1024:.1f} KiB ({theme})")

    print(
        f"{calendar.total:,} contributions, {len(calendar.ore)} ore squares, "
        f"{len(plan)} steps, {timing.total:.1f}s loop"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
