# SWL View

Local shortwave schedule viewer based on EiBi data.
 TCI functionality has been implements so this software can be used with Apache Labs transceivers if using Thetis, and also Expert Electrnics SunSDR transceivers (though not tested on SunSDR)

- Version: 0.2.4
- By: GW3JVB
- Copyright: © 2026

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
