# SWL View

Local shortwave schedule viewer based on EiBi data.
TCI support is included for Thetis and Expert Electronics SunSDR environments.

- Version: 0.2.11
- By: GW3JVB
- Copyright: © 2026

## Download The Correct Package

From the GitHub release assets:
- macOS users: `SWL_View-macos-vX.Y.Z.zip`
- Windows users: `SWL_View-win11-vX.Y.Z.zip`

## Tested Platforms

This software has been tested on the following platforms:
- Mac Studio (Apple M2 Max) running macOS Tahoe 26.3 (TCI connection confirmed)

Planned testing:
- Mac Studio (Apple M2 Max) running Win11 ARM in Parallels for Mac Pro

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
  - `TCI Profile` selector:
    - `Thetis` (default)
    - `Expert (SunSDR)`
    - If you are using a SunSDR radio, you must select `Expert (SunSDR)`.
  - Tune by clicking station cards
  - Audio mute toggle (`Audio: ON` / `Audio: MUTED`)
  - Optional spot send (`Send spot`)
  - Optional SWL timed spots (`Use SWL timed spots`) with automatic TTL from station off-time when live
  - Optional persistent SWL spots (`Persistent spots (0s)`)
  - Raw TCI command sender (`Send Raw`)
- Local config persistence in `app/local_config.json` (TCI host/port).

## Quick Setup

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run.bat
```

Then open `http://127.0.0.1:5000/`.

## Detailed Step-By-Step Setup

### macOS / Linux

1. Open Terminal and go to the project folder:
   ```bash
   cd /path/to/SWL_View
   ```
2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the app (scrape + web app):
   ```bash
   ./run.sh
   ```
6. Open browser:
   - `http://127.0.0.1:5000/`

### Windows (PowerShell)

1. Open PowerShell and go to the project folder:
   ```powershell
   cd C:\path\to\SWL_View
   ```
2. Create a virtual environment:
   ```powershell
   py -m venv .venv
   ```
3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
4. If activation is blocked, run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```
5. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
6. Start the app (scrape + web app):
   ```powershell
   .\run.bat
   ```
7. Open browser:
   - `http://127.0.0.1:5000/`

### Runtime Options

Single runtime entrypoint (all platforms):
- `python run.py` (runs scraper, then starts Flask)
- `python run.py --skip-scrape` (start Flask only)

Wrapper behavior:
- `run.sh` activates `.venv` then runs `python run.py`
- `run.bat` activates `.venv` then runs `python run.py`

## TCI Profile Selection (Important)

- For Thetis users: select `TCI Profile = Thetis`.
- For SunSDR users: select `TCI Profile = Expert (SunSDR)`.
- SunSDR users must select `Expert (SunSDR)` for spot command compatibility.
- This setting is saved in `app/local_config.json` with TCI host/port.

## TCI Quick Test (Thetis)

1. Start Thetis and enable its TCI server.
2. In SWL View TCI panel, set:
   - `Host` and `Port`
   - `TCI Profile = Thetis`
3. Click `Connect` and confirm status is `Connected`.
4. Click a station card to tune.
5. Optional: enable `Send spot` and click again.
6. Confirm results in Thetis and in SWL View status text.

## Data Refresh Guidance

- EiBi schedules update by season (`Axx` / `Bxx`).
- Refresh at least monthly.
- Refresh immediately before operating sessions if you want latest data.
- If not using `run.py`/wrappers, run manually:

```bash
python scraper/scrape_eibi.py
python app/main.py
```

## Build Release Packages

Create both platform zip packages:

```bash
python release/make_release_packages.py
```

This creates:
- `release/dist/SWL_View-macos-vX.Y.Z.zip`
- `release/dist/SWL_View-win11-vX.Y.Z.zip`

Each package includes the full project and a platform-specific `QUICKSTART.md`.

## Upgrading To A New Version

- User TCI settings are stored in `app/local_config.json` (host, port, profile, send-spot).
- To keep your settings during upgrade, preserve this file.
- Recommended upgrade steps:
  1. Back up `app/local_config.json`.
  2. Replace application files with the new version.
  3. Restore `app/local_config.json` if it was overwritten.

## Troubleshooting

- UI not updating after changes:
  - Hard refresh browser (`Cmd+Shift+R` on macOS).
- TCI disconnected:
  - Confirm radio software TCI server is enabled.
  - Confirm IP/port are correct.
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
