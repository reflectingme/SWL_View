#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate
python scraper/scrape_eibi.py
python app/main.py
