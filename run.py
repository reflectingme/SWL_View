#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd))
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SWL View: scrape EiBi data, then start the Flask app."
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Start the Flask app without running scraper/scrape_eibi.py first.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    py = sys.executable

    if not args.skip_scrape:
        print("Running EiBi scraper...")
        code = run_cmd([py, "scraper/scrape_eibi.py"], root)
        if code != 0:
            return code

    print("Starting Flask app on http://127.0.0.1:5000 ...")
    return run_cmd([py, "app/main.py"], root)


if __name__ == "__main__":
    raise SystemExit(main())
