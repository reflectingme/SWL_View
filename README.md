# SWL View

Local shortwave schedule viewer based on EiBi data.
 TCI functionality has been implemented so this software can be used with Apache Labs transceivers if using Thetis, and also Expert Electronics SunSDR transceivers (though this has not been tested on SunSDR transceivers)

- Version: 0.2.7
- By: GW3JVB
- Copyright: © 2026

## Tested Platforms

This software has been tested on the following platforms:
- Mac Studio (Apple M2 Max) running macOS Tahoe 26.3 - Tested - OK, TCI Status Connection confirmed

Tests todo:
- Mac Studio (Apple M2 Max) running Win11 ARM in a Virtual Machine using Parallels for Mac Pro - not yet tested

All testing carried out using Thetis v2.10.3.13 x64

## Features

- EiBi CSV scrape over HTTP (`http://eibispace.de/dx/`) with JSON output.
- Scrape metadata shown in UI (`Last scrape` in Dataset panel).
- Flask UI with multiple views:
  - Time columns
  - Frequency columns
  - Time x Day grid
  - Frequency x Time scatter view
- Live-now highlighting/filtering and top detail panels:
  - Dataset summary
  - Current Active (last clicked station)
  - On Hover (station details preview)
- View Controls card:
  - `Show Live` filter
  - View mode selector
- TCI Controls card:
  - Connect / disconnect to TCI server (WebSocket)
  - Tune by clicking station cards
  - Audio mute toggle (`Audio: ON` / `Audio: MUTED`)
  - Optional spot send (`Send spot`)
  - Raw TCI command sender (`Send Raw`)
- Local config persistence in `app/local_config.json` (TCI host/port).

## Setup (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run (macOS / Linux)

```bash
./run.sh
```

## Run (Windows)

```powershell
.\run.bat
```

Single runtime entrypoint (all platforms):
1. `python run.py` (runs scraper, then starts Flask)
2. `python run.py --skip-scrape` (start Flask only)

Wrappers:
- `run.sh` (macOS/Linux): activates `.venv` and calls `python run.py`
- `run.bat` (Windows): activates `.venv` and calls `python run.py`

Then open `http://127.0.0.1:5000/`.

## Build Release Packages

Create platform zip packages from one command:

```bash
python release/make_release_packages.py
```

This creates:
- `release/dist/SWL_View-macos-vX.Y.Z.zip`
- `release/dist/SWL_View-win11-vX.Y.Z.zip`

Each package includes the full project and a platform-specific `QUICKSTART.md`.

## Data Refresh Guidance

- EiBi schedules update by season (`Axx` / `Bxx`), so refresh your local data at least monthly.
- Also refresh immediately before use if you want the latest schedule data.
- If you are not using `run.py`/`run.sh`, run manually:
  ```bash
  python scraper/scrape_eibi.py
  python app/main.py
  ```

## TCI Quick Test (Thetis)

1. Start Thetis and enable its TCI server.
2. In SWL View, enter Thetis TCI `IP` and `Port` in the top `TCI` panel.
3. Click `Connect`.
4. Click any station card to send a tune command to TCI (`vfo:0,0,<freq_hz>;`).
5. Optionally toggle `Send spot` and/or `Audio`.
6. Check the TCI status badge/message for success or error text.

## Troubleshooting

- If UI changes are not visible after an update: hard refresh browser (`Cmd+Shift+R` on macOS).
- If TCI shows disconnected:
  - Confirm Thetis TCI server is enabled.
  - Test TCP reachability:
    ```bash
    nc -vz <TCI_IP> <TCI_PORT>
    ```
  - Test WebSocket handshake:
    ```bash
    python - <<'PY'
    import websocket
    ws = websocket.create_connection("ws://<TCI_IP>:<TCI_PORT>", timeout=3)
    print("connected")
    ws.close()
    PY
    ```
