from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
import time

try:
    import websocket  # websocket-client
except Exception:
    websocket = None

app = Flask(__name__)

APP_VERSION = "0.2.1"
APP_AUTHOR = "GW3JVB"
APP_COPYRIGHT = "© 2026"
DEFAULT_TCI_MODE = "am"
CONFIG_FILE = (Path(__file__).parent.parent / "app" / "local_config.json").resolve()
DEFAULT_SEND_SPOT = True

DATA_FILE = (Path(__file__).parent.parent / "scraper" / "output" / "eibi_latest.json").resolve()
DAY_ORDER = ["mo", "tu", "we", "th", "fr", "sa", "su"]
DAY_LABEL = {"mo": "Mon", "tu": "Tue", "we": "Wed", "th": "Thu", "fr": "Fri", "sa": "Sat", "su": "Sun"}
ITU_TO_ISO2 = {
    "AFS": "ZA", "ALG": "DZ", "ALS": "AL", "AND": "AD", "ARG": "AR", "AUS": "AU",
    "AZE": "AZ", "AZR": "AZ", "B": "CN", "BEL": "BE", "BER": "BM", "BGD": "BD",
    "BHR": "BH", "BLR": "BY", "BOL": "BO", "BUL": "BG", "CAN": "CA", "CHL": "CL",
    "CHN": "CN", "CLM": "CO", "CLN": "LK", "COD": "CD", "COG": "CG", "CPV": "CV",
    "CUB": "CU", "CVA": "VA", "CYM": "KY", "CZE": "CZ", "D": "DE", "DNK": "DK",
    "E": "ES", "EGY": "EG", "EQA": "EC", "EST": "EE", "ETH": "ET", "F": "FR",
    "FIN": "FI", "FJI": "FJ", "FRO": "FO", "G": "GB", "GRC": "GR", "GRL": "GL",
    "GUF": "GF", "GUM": "GU", "HKG": "HK", "HND": "HN", "HNG": "HU", "HOL": "NL",
    "I": "IT", "IND": "IN", "INS": "ID", "IRL": "IE", "IRN": "IR", "ISL": "IS",
    "ISR": "IL", "J": "JP", "KAZ": "KZ", "KGZ": "KG", "KOR": "KR", "KRE": "KP",
    "KWT": "KW", "LBR": "LR", "LBY": "LY", "MAU": "MU", "MCO": "MC", "MDG": "MG",
    "MEX": "MX", "MLI": "ML", "MNG": "MN", "MRT": "MR", "MYA": "MM", "NGR": "NG",
    "NOR": "NO", "NZL": "NZ", "PAK": "PK", "PHL": "PH", "PNG": "PG", "POL": "PL",
    "POR": "PT", "PRU": "PE", "ROU": "RO", "RUS": "RU", "S": "SE", "SDN": "SD",
    "SEN": "SN", "SEY": "SC", "SLM": "SB", "SNG": "SG", "SOM": "SO", "SUI": "CH",
    "SVK": "SK", "SWZ": "SZ", "TCD": "TD", "THA": "TH", "TJK": "TJ", "TKM": "TM",
    "TRD": "TT", "TUR": "TR", "TWN": "TW", "UKR": "UA", "USA": "US", "UZB": "UZ",
    "VTN": "VN", "VUT": "VU",
}


class TCIClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ws = None
        self.host = "127.0.0.1"
        self.port = 40001
        self.last_error = ""
        self.last_command = ""

    def status(self) -> dict:
        with self._lock:
            connected = self._ws is not None
            return {
                "enabled": websocket is not None,
                "connected": connected,
                "host": self.host,
                "port": self.port,
                "last_error": self.last_error,
                "last_command": self.last_command,
            }

    def configure(self, host: str, port: int) -> None:
        with self._lock:
            self.host = host.strip() or "127.0.0.1"
            self.port = int(port)

    def connect(self) -> tuple[bool, str]:
        if websocket is None:
            return False, "websocket-client not installed"
        with self._lock:
            self._disconnect_locked()
            try:
                url = f"ws://{self.host}:{self.port}"
                self._ws = websocket.create_connection(url, timeout=2.0)
                self.last_error = ""
                return True, f"Connected to {url}"
            except Exception as exc:
                self.last_error = str(exc)
                self._ws = None
                return False, self.last_error

    def disconnect(self) -> None:
        with self._lock:
            self._disconnect_locked()

    def _disconnect_locked(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    def tune(self, frequency_khz: float, mode: str | None = None) -> tuple[bool, str]:
        # Common TCI VFO command form used by ExpertSDR/Thetis integrations.
        freq_hz = int(round(float(frequency_khz) * 1000))
        commands: list[str] = [f"vfo:0,0,{freq_hz};"]

        # TCI implementations differ slightly for mode-setting command syntax.
        mode_value = (mode or "").strip().lower()
        if mode_value:
            commands.extend(
                [
                    f"modulation:0,0,{mode_value};",
                    f"modulation:0,{mode_value};",
                    f"mode:0,0,{mode_value};",
                ]
            )

        with self._lock:
            if self._ws is None:
                self.last_error = "Not connected"
                return False, self.last_error
            try:
                sent: list[str] = []
                for cmd in commands:
                    self._ws.send(cmd)
                    sent.append(cmd)
                    # TCI servers often process commands sequentially.
                    time.sleep(0.03)
                self.last_command = " ".join(sent)
                self.last_error = ""
                return True, self.last_command
            except Exception as exc:
                self.last_error = str(exc)
                self._disconnect_locked()
                return False, self.last_error

    def send_spot(
        self,
        station: str,
        frequency_khz: float,
        mode: str = "am",
        ttl_seconds: int = 120,
    ) -> tuple[bool, str]:
        # Use station text as spot tag so Thetis can display meaningful info.
        station_tag = re.sub(r"[^A-Za-z0-9/]", "", (station or "").upper())
        station_tag = station_tag[:12]
        if not station_tag:
            station_tag = "M0SWL"
        freq_hz = int(round(float(frequency_khz) * 1000))
        commands = [f"spot:{station_tag},{freq_hz},ssb-swl[{int(ttl_seconds)}];"]

        with self._lock:
            if self._ws is None:
                self.last_error = "Not connected"
                return False, self.last_error
            try:
                sent = []
                for cmd in commands:
                    self._ws.send(cmd)
                    sent.append(cmd)
                    time.sleep(0.03)
                self.last_command = " ".join(sent)
                self.last_error = ""
                return True, self.last_command
            except Exception as exc:
                self.last_error = str(exc)
                self._disconnect_locked()
                return False, self.last_error

    def send_raw(self, command: str) -> tuple[bool, str]:
        cmd = (command or "").strip()
        if not cmd:
            return False, "Empty command"
        if not cmd.endswith(";"):
            cmd = f"{cmd};"
        with self._lock:
            if self._ws is None:
                self.last_error = "Not connected"
                return False, self.last_error
            try:
                self._ws.send(cmd)
                self.last_command = cmd
                self.last_error = ""
                return True, cmd
            except Exception as exc:
                self.last_error = str(exc)
                self._disconnect_locked()
                return False, self.last_error


TCI = TCIClient()


def _load_local_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_local_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _update_local_tci_config(host: str, port: int) -> None:
    config = _load_local_config()
    config.setdefault("tci", {})
    config["tci"]["host"] = host
    config["tci"]["port"] = int(port)
    config["tci"]["send_spot"] = bool(config["tci"].get("send_spot", DEFAULT_SEND_SPOT))
    _save_local_config(config)


def _bootstrap_tci_from_config() -> None:
    config = _load_local_config()
    tci_cfg = config.get("tci", {})
    host = str(tci_cfg.get("host", TCI.host))
    port = int(tci_cfg.get("port", TCI.port))
    TCI.configure(host, port)


_bootstrap_tci_from_config()


def _parse_hhmm(value: str) -> int | None:
    value = (value or "").strip()
    if not value.isdigit():
        return None
    value = value.zfill(4)
    hours = int(value[:2])
    minutes = int(value[2:])
    if hours == 24 and minutes == 0:
        return 1440
    if hours > 23 or minutes > 59:
        return None
    return (hours * 60) + minutes


def _format_hhmm(value: str) -> str:
    value = (value or "").strip()
    if not value.isdigit():
        return value
    value = value.zfill(4)
    return f"{value[:2]}:{value[2:]}"


def _format_time_range(time_on: str, time_off: str) -> str:
    on = _format_hhmm(time_on)
    off = _format_hhmm(time_off)
    if on and off:
        return f"{on}-{off}"
    return on or off


def _join_non_empty(left: str, right: str, separator: str = " | ") -> str:
    left = (left or "").strip()
    right = (right or "").strip()
    if left and right:
        return f"{left}{separator}{right}"
    return left or right


def _iso2_to_flag(iso2: str) -> str:
    code = (iso2 or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return "🌐"
    return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


def _flag_from_itu(itu: str) -> str:
    iso2 = ITU_TO_ISO2.get((itu or "").strip().upper(), "")
    return _iso2_to_flag(iso2) if iso2 else "🌐"


def _extract_day_set(days: str) -> set[str] | None:
    text = (days or "").strip().lower()
    if not text or "daily" in text:
        return set(DAY_ORDER)

    found_days: set[str] = set()

    for match in re.findall(r"[1-7]", text):
        found_days.add(DAY_ORDER[int(match) - 1])

    for match in re.finditer(r"(mo|tu|we|th|fr|sa|su)(?:\s*[-–]\s*(mo|tu|we|th|fr|sa|su))?", text):
        start = match.group(1)
        end = match.group(2)
        if end is None:
            found_days.add(start)
            continue
        start_idx = DAY_ORDER.index(start)
        end_idx = DAY_ORDER.index(end)
        if start_idx <= end_idx:
            found_days.update(DAY_ORDER[start_idx : end_idx + 1])
        else:
            found_days.update(DAY_ORDER[start_idx:] + DAY_ORDER[: end_idx + 1])

    return found_days if found_days else None


def _day_set_to_display(day_set: set[str], fallback: str = "") -> str:
    if not day_set:
        return fallback
    if day_set == set(DAY_ORDER):
        return "Daily"
    ordered = [d for d in DAY_ORDER if d in day_set]
    return ",".join(DAY_LABEL[d] for d in ordered)


def _entry_matches_weekday(entry: dict, weekday_idx: int) -> bool:
    code = DAY_ORDER[weekday_idx]
    if entry.get("day_set_known"):
        return code in set(entry.get("day_set", []))
    return _day_matches(str(entry.get("days_raw", "")), weekday_idx)


def _day_matches(days: str, weekday_utc: int) -> bool:
    day_set = _extract_day_set(days)
    if day_set is None:
        return True
    return DAY_ORDER[weekday_utc] in day_set


def _is_live_now(entry: dict, now_utc: datetime) -> bool:
    if not _entry_matches_weekday(entry, now_utc.weekday()):
        return False

    start = _parse_hhmm(str(entry.get("time_on", "")))
    end = _parse_hhmm(str(entry.get("time_off", "")))
    if start is None or end is None:
        return False

    now_minutes = (now_utc.hour * 60) + now_utc.minute
    if start == end:
        return True
    if start < end:
        return start <= now_minutes < end
    return now_minutes >= start or now_minutes < end


def _normalize_entry(entry: dict) -> dict:
    return {
        "frequency_khz": int(entry.get("frequency_khz", 0) or 0),
        "time_on": str(entry.get("time_on", "")).strip(),
        "time_off": str(entry.get("time_off", "")).strip(),
        "days_raw": str(entry.get("days", "")).strip(),
        "itu": str(entry.get("itu", "")).strip(),
        "station": str(entry.get("station", "")).strip(),
        "language": str(entry.get("language", "")).strip(),
        "target": str(entry.get("target", "")).strip(),
        "remarks": str(entry.get("remarks", "")).strip(),
    }


def _merge_entries(raw_entries: list[dict]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for raw in raw_entries:
        normalized = _normalize_entry(raw)
        day_set = _extract_day_set(normalized["days_raw"])
        day_identity = "__parsed__" if day_set is not None else f"__raw__:{normalized['days_raw'].lower()}"
        key = (
            normalized["frequency_khz"],
            normalized["time_on"],
            normalized["time_off"],
            normalized["itu"],
            normalized["station"],
            normalized["language"],
            normalized["target"],
            normalized["remarks"],
            day_identity,
        )
        if key not in grouped:
            grouped[key] = {
                **normalized,
                "_day_set": set(day_set) if day_set is not None else set(),
                "day_set_known": day_set is not None,
            }
        elif day_set is not None:
            grouped[key]["_day_set"].update(day_set)

    merged: list[dict] = []
    for item in grouped.values():
        day_set_known = bool(item["day_set_known"])
        day_set = item["_day_set"] if day_set_known else set()
        item["day_set"] = [d for d in DAY_ORDER if d in day_set]
        item["days"] = _day_set_to_display(day_set, item["days_raw"])
        item["flag"] = _flag_from_itu(item["itu"])
        item["time_display"] = _format_time_range(item["time_on"], item["time_off"])
        item["time_days_display"] = _join_non_empty(
            item["time_display"],
            item["days"],
        )
        item["lang_target_display"] = _join_non_empty(item["language"], item["target"])
        item.pop("_day_set", None)
        merged.append(item)

    merged.sort(
        key=lambda e: (
            _parse_hhmm(e["time_on"]) if _parse_hhmm(e["time_on"]) is not None else 10_000,
            e["time_off"],
            e["frequency_khz"],
            e["station"].lower(),
        )
    )
    return merged


def _build_columns(entries: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for entry in entries:
        key = (entry["time_on"], entry["time_off"], entry["days"])
        grouped.setdefault(key, []).append(entry)

    columns: list[dict] = []
    for (time_on, time_off, days), items in grouped.items():
        items.sort(key=lambda e: (e["frequency_khz"], e["station"].lower()))
        start_sort = _parse_hhmm(time_on)
        columns.append(
            {
                "time_on": time_on,
                "time_off": time_off,
                "days": days,
                "time_display": _format_time_range(time_on, time_off),
                "time_days_display": _join_non_empty(_format_time_range(time_on, time_off), days),
                "entries": items,
                "sort_key": (start_sort if start_sort is not None else 10_000, time_off, days),
                "is_live_now": any(bool(e.get("is_live_now")) for e in items),
            }
        )

    columns.sort(key=lambda c: c["sort_key"])
    return columns


def _build_frequency_columns(entries: list[dict]) -> list[dict]:
    grouped: dict[int, list[dict]] = {}
    for entry in entries:
        freq = int(entry["frequency_khz"])
        grouped.setdefault(freq, []).append(entry)

    columns: list[dict] = []
    for freq, items in grouped.items():
        items.sort(
            key=lambda e: (
                _parse_hhmm(e["time_on"]) if _parse_hhmm(e["time_on"]) is not None else 10_000,
                e["time_off"],
                e["station"].lower(),
            )
        )
        columns.append(
            {
                "frequency_khz": freq,
                "frequency_display": f"{freq / 1000:.3f} MHz",
                "entries": items,
                "sort_key": freq,
                "is_live_now": any(bool(e.get("is_live_now")) for e in items),
            }
        )

    columns.sort(key=lambda c: c["sort_key"])
    return columns


def _build_time_day_grid(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    slot_map: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry["time_on"], entry["time_off"])
        if key not in slot_map:
            start_sort = _parse_hhmm(entry["time_on"])
            slot_map[key] = {
                "time_on": entry["time_on"],
                "time_off": entry["time_off"],
                "display": _format_time_range(entry["time_on"], entry["time_off"]),
                "sort": start_sort if start_sort is not None else 10_000,
            }
    time_slots = sorted(slot_map.values(), key=lambda s: (s["sort"], s["time_off"]))

    rows: list[dict] = []
    for day_idx, day_code in enumerate(DAY_ORDER):
        cells: list[dict] = []
        for slot in time_slots:
            cell_entries = [
                e for e in entries
                if e["time_on"] == slot["time_on"]
                and e["time_off"] == slot["time_off"]
                and _entry_matches_weekday(e, day_idx)
            ]
            cell_entries.sort(key=lambda e: (e["frequency_khz"], e["station"].lower()))
            cells.append(
                {
                    "slot_key": f"{slot['time_on']}-{slot['time_off']}",
                    "entries": cell_entries,
                    "is_live_now": any(bool(e.get("is_live_now")) for e in cell_entries),
                }
            )
        rows.append({"day_code": day_code, "day_label": DAY_LABEL[day_code], "cells": cells})

    return time_slots, rows


def _build_freq_time_grid(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    slot_map: dict[tuple[str, str], dict] = {}
    freq_map: dict[int, dict] = {}

    for entry in entries:
        time_key = (entry["time_on"], entry["time_off"])
        if time_key not in slot_map:
            start_sort = _parse_hhmm(entry["time_on"])
            slot_map[time_key] = {
                "time_on": entry["time_on"],
                "time_off": entry["time_off"],
                "display": _format_time_range(entry["time_on"], entry["time_off"]),
                "sort": start_sort if start_sort is not None else 10_000,
            }

        freq = int(entry["frequency_khz"])
        if freq not in freq_map:
            freq_map[freq] = {"frequency_khz": freq, "display": f"{freq / 1000:.3f} MHz"}

    time_slots = sorted(slot_map.values(), key=lambda s: (s["sort"], s["time_off"]))
    freq_slots = [freq_map[k] for k in sorted(freq_map.keys())]

    rows: list[dict] = []
    for slot in time_slots:
        cells: list[dict] = []
        for freq in freq_slots:
            cell_entries = [
                e for e in entries
                if e["time_on"] == slot["time_on"]
                and e["time_off"] == slot["time_off"]
                and int(e["frequency_khz"]) == int(freq["frequency_khz"])
            ]
            cell_entries.sort(key=lambda e: (e["station"].lower(), e["days"]))
            cells.append(
                {
                    "entries": cell_entries,
                    "is_live_now": any(bool(e.get("is_live_now")) for e in cell_entries),
                }
            )
        rows.append({"time_display": slot["display"], "cells": cells})

    return freq_slots, rows


def _build_freq_time_plot(entries: list[dict]) -> dict:
    freqs = [int(e["frequency_khz"]) for e in entries if int(e["frequency_khz"]) > 0]
    min_freq = min(freqs) if freqs else 1000
    max_freq = max(freqs) if freqs else 30000
    if min_freq == max_freq:
        max_freq = min_freq + 1

    plot_w = 1500
    plot_h = 900
    left = 70
    right = 20
    top = 20
    bottom = 30
    usable_w = plot_w - left - right
    usable_h = plot_h - top - bottom

    points: list[dict] = []
    for entry in entries:
        freq = int(entry["frequency_khz"])
        start = _parse_hhmm(entry["time_on"])
        if freq <= 0 or start is None:
            continue
        x = left + ((freq - min_freq) / (max_freq - min_freq)) * usable_w
        y = top + (start / 1439) * usable_h
        points.append(
            {
                "x": round(x, 2),
                "y": round(y, 2),
                "freq_khz": freq,
                "freq_display": f"{freq / 1000:.3f} MHz",
                "station": entry["station"],
                "time_display": entry["time_days_display"],
                "lang_target": entry["lang_target_display"],
                "remarks": entry["remarks"],
                "flag": entry["flag"],
                "is_live_now": bool(entry.get("is_live_now")),
            }
        )

    return {
        "width": plot_w,
        "height": plot_h,
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "min_freq": min_freq,
        "max_freq": max_freq,
        "points": points,
    }


def _build_freq_jumps(entries: list[dict], segments: int = 10) -> list[dict]:
    freqs = sorted({int(e["frequency_khz"]) for e in entries if int(e["frequency_khz"]) > 0})
    if not freqs or segments <= 1:
        return []
    jumps: list[dict] = []
    n = len(freqs)
    for i in range(segments):
        start_idx = min(n - 1, int((i * n) / segments))
        end_idx = min(n - 1, int((((i + 1) * n) / segments) - 1))
        start = freqs[start_idx]
        end = freqs[end_idx]
        ratio = start_idx / max(1, n - 1)
        jumps.append(
            {
                "index": i + 1,
                "ratio": ratio,
                "start_khz": start,
                "start_label": f"{start / 1000:.3f} MHz",
                "label": f"{start / 1000:.3f}-{end / 1000:.3f} MHz",
            }
        )
    return jumps


@app.get("/api/tci/status")
def tci_status():
    return jsonify(TCI.status())


@app.post("/api/tci/connect")
def tci_connect():
    payload = request.get_json(silent=True) or {}
    host = str(payload.get("host", TCI.host))
    port = int(payload.get("port", TCI.port))
    send_spot = bool(payload.get("send_spot", _load_local_config().get("tci", {}).get("send_spot", DEFAULT_SEND_SPOT)))
    TCI.configure(host, port)
    config = _load_local_config()
    config.setdefault("tci", {})
    config["tci"]["host"] = TCI.host
    config["tci"]["port"] = TCI.port
    config["tci"]["send_spot"] = send_spot
    _save_local_config(config)
    ok, message = TCI.connect()
    status = TCI.status()
    status["send_spot"] = send_spot
    status["message"] = message
    return jsonify(status), (200 if ok else 400)


@app.post("/api/tci/disconnect")
def tci_disconnect():
    TCI.disconnect()
    status = TCI.status()
    status["message"] = "Disconnected"
    return jsonify(status)


@app.post("/api/tci/settings")
def tci_settings():
    payload = request.get_json(silent=True) or {}
    host = str(payload.get("host", TCI.host))
    port = int(payload.get("port", TCI.port))
    send_spot = bool(payload.get("send_spot", DEFAULT_SEND_SPOT))
    TCI.configure(host, port)
    config = _load_local_config()
    config.setdefault("tci", {})
    config["tci"]["host"] = TCI.host
    config["tci"]["port"] = TCI.port
    config["tci"]["send_spot"] = send_spot
    _save_local_config(config)
    status = TCI.status()
    status["send_spot"] = send_spot
    status["message"] = "Settings saved"
    return jsonify(status)


@app.post("/api/tci/tune")
def tci_tune():
    payload = request.get_json(silent=True) or {}
    if "frequency_khz" not in payload:
        return jsonify({"ok": False, "message": "frequency_khz required"}), 400
    try:
        frequency_khz = float(payload["frequency_khz"])
    except Exception:
        return jsonify({"ok": False, "message": "Invalid frequency_khz"}), 400

    mode = str(payload.get("mode", DEFAULT_TCI_MODE)).strip().lower()
    ok, result = TCI.tune(frequency_khz, mode=mode)
    send_spot = bool(payload.get("send_spot", DEFAULT_SEND_SPOT))
    spot_result = ""
    if ok and send_spot:
        station = str(payload.get("station", "SWL"))
        spot_ok, spot_result = TCI.send_spot(station=station, frequency_khz=frequency_khz, mode=mode, ttl_seconds=120)
        ok = ok and spot_ok

    status = TCI.status()
    return jsonify({"ok": ok, "result": result, "spot_result": spot_result, "status": status}), (200 if ok else 400)


@app.post("/api/tci/raw")
def tci_raw():
    payload = request.get_json(silent=True) or {}
    command = str(payload.get("command", ""))
    ok, result = TCI.send_raw(command)
    status = TCI.status()
    return jsonify({"ok": ok, "result": result, "status": status}), (200 if ok else 400)


@app.route("/")
def index():
    if DATA_FILE.exists():
        source = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        source = {"entries": [], "count": 0, "source_file": None, "fetched_at_utc": None}

    merged_entries = _merge_entries(source.get("entries", []))
    now_utc = datetime.now(timezone.utc)
    live_count = 0
    for entry in merged_entries:
        entry["is_live_now"] = _is_live_now(entry, now_utc)
        if entry["is_live_now"]:
            live_count += 1

    view_mode = request.args.get("view", "columns").strip().lower()
    if view_mode not in {"columns", "freqcolumns", "grid", "freqgrid"}:
        view_mode = "columns"

    time_slot_keys = {(e["time_on"], e["time_off"]) for e in merged_entries}
    freq_slot_keys = {int(e["frequency_khz"]) for e in merged_entries}

    columns: list[dict] = []
    freq_columns: list[dict] = []
    time_slots: list[dict] = []
    day_rows: list[dict] = []
    freq_plot: dict = {"width": 1500, "height": 900, "points": [], "min_freq": 0, "max_freq": 0}

    if view_mode == "columns":
        columns = _build_columns(merged_entries)
    elif view_mode == "freqcolumns":
        freq_columns = _build_frequency_columns(merged_entries)
    elif view_mode == "grid":
        time_slots, day_rows = _build_time_day_grid(merged_entries)
    elif view_mode == "freqgrid":
        freq_plot = _build_freq_time_plot(merged_entries)

    data = {
        "app_version": APP_VERSION,
        "app_author": APP_AUTHOR,
        "app_copyright": APP_COPYRIGHT,
        "source_file": source.get("source_file"),
        "fetched_at_utc": source.get("fetched_at_utc"),
        "raw_count": len(source.get("entries", [])),
        "count": len(merged_entries),
        "entries": merged_entries,
        "live_count": live_count,
        "now_utc_hhmm": now_utc.strftime("%H:%M"),
        "columns": columns,
        "column_count": len(columns) if columns else len(time_slot_keys),
        "freq_columns": freq_columns,
        "freq_column_count": len(freq_columns) if freq_columns else len(freq_slot_keys),
        "time_slots": time_slots,
        "time_slot_count": len(time_slots) if time_slots else len(time_slot_keys),
        "day_rows": day_rows,
        "freq_slot_count": len(freq_slot_keys),
        "freq_plot": freq_plot,
        "freq_jumps": _build_freq_jumps(merged_entries, segments=10),
        "view_mode": view_mode,
        "tci": TCI.status(),
        "tci_send_spot": bool(_load_local_config().get("tci", {}).get("send_spot", DEFAULT_SEND_SPOT)),
    }
    return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
