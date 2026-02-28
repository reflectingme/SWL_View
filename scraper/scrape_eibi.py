from __future__ import annotations
import csv
import io
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import requests
import urllib3

BASE = "http://eibispace.de/dx/"
CANDIDATES = ["sked-b25.csv", "sked-a25.csv", "sked-b24.csv", "sked-a24.csv"]

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class Entry:
    frequency_khz: int
    time_on: str
    time_off: str
    days: str
    itu: str
    station: str
    language: str
    target: str
    remarks: str

def fetch(url: str) -> bytes:
    # Keep verify=False so redirects to HTTPS do not fail on cert mismatch.
    r = requests.get(url, timeout=30, headers={"User-Agent": "SWL-View/1.0"}, verify=False)
    r.raise_for_status()
    return r.content

def download_latest() -> tuple[str, bytes]:
    last_err = None
    for name in CANDIDATES:
        try:
            data = fetch(BASE + name)
            if b";" in data[:500]:
                return name, data
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError("Could not download EiBi schedule.") from last_err

def parse_semicolon_csv(raw: bytes) -> list[Entry]:
    text = raw.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    entries: list[Entry] = []

    for row in reader:
        if not row or all(not c.strip() for c in row):
            continue

        freq_idx = None
        for i, cell in enumerate(row):
            s = cell.strip()
            if s.isdigit():
                v = int(s)
                if 1000 <= v <= 30000:
                    freq_idx = i
                    break
        if freq_idx is None:
            continue

        freq = int(row[freq_idx].strip())

        time_range = row[freq_idx + 1].strip() if freq_idx + 1 < len(row) else ""
        time_on, time_off = "", ""
        m = re.match(r"^\s*(\d{3,4})\s*-\s*(\d{3,4})\s*$", time_range)
        if m:
            time_on, time_off = m.group(1), m.group(2)

        days = row[freq_idx + 2].strip() if freq_idx + 2 < len(row) else ""
        itu = row[freq_idx + 3].strip() if freq_idx + 3 < len(row) else ""
        station = row[freq_idx + 4].strip() if freq_idx + 4 < len(row) else ""
        language = row[freq_idx + 5].strip() if freq_idx + 5 < len(row) else ""
        target = row[freq_idx + 6].strip() if freq_idx + 6 < len(row) else ""
        remarks = " | ".join(c.strip() for c in row[freq_idx + 7:]).strip()

        entries.append(
            Entry(
                frequency_khz=freq,
                time_on=time_on,
                time_off=time_off,
                days=days,
                itu=itu,
                station=station,
                language=language,
                target=target,
                remarks=remarks,
            )
        )

    return entries

def main():
    filename, raw = download_latest()
    entries = parse_semicolon_csv(raw)

    payload = {
        "source_file": filename,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "entries": [asdict(e) for e in entries],
    }

    out_path = OUT_DIR / "eibi_latest.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {out_path}")

if __name__ == "__main__":
    main()
