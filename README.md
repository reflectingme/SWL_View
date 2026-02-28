# SWL View

Local shortwave schedule viewer based on EiBi data.

- Version: 0.2.1
- By: GW3JVB
- Copyright: © 2026

## Features

- EiBi CSV scrape over HTTP (`http://eibispace.de/dx/`) with JSON output.
- Flask UI with multiple views:
  - Time columns
  - Frequency columns
  - Time x Day grid
  - Frequency x Time scatter view
- Live-now highlighting/filtering and top detail panel.
- TCI client panel (IP/port connect + click station card to tune VFO).
- Optional Thetis spot send on click (`Send spot` toggle in TCI panel).
- Local config persistence in `app/local_config.json` (TCI host/port).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scraper/requirements.txt
pip install flask websocket-client
```

## Run

```bash
./run.sh
```

Then open `http://127.0.0.1:5000/`.

## TCI Quick Test (Thetis)

1. Start Thetis and enable its TCI server.
2. In SWL View, enter Thetis TCI `IP` and `Port` in the top `TCI` panel.
3. Click `Connect`.
4. Click any station card to send a tune command to TCI (`vfo:0,0,<freq_hz>;`).
5. Check the TCI status badge/tooltip for success or error text.
