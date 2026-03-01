from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
import threading
import time

try:
    import websocket  # websocket-client
except Exception:
    websocket = None

DEFAULT_TCI_MODE = "am"
DEFAULT_SEND_SPOT = True
DEFAULT_TCI_PROFILE = "thetis"
DEFAULT_USE_SWL_TIMED_SPOT = True
DEFAULT_PERSISTENT_SWL_SPOT = False
VALID_TCI_PROFILES = {"thetis", "expert"}
CONFIG_FILE = (Path(__file__).parent / "local_config.json").resolve()


class TCIClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ws = None
        self.host = "127.0.0.1"
        self.port = 40001
        self.last_error = ""
        self.last_command = ""
        self.muted = False
        self.profile = DEFAULT_TCI_PROFILE

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
                "muted": self.muted,
                "profile": self.profile,
            }

    def configure(self, host: str, port: int, profile: str | None = None) -> None:
        with self._lock:
            self.host = host.strip() or "127.0.0.1"
            self.port = int(port)
            if profile is not None:
                profile_value = str(profile).strip().lower()
                self.profile = profile_value if profile_value in VALID_TCI_PROFILES else DEFAULT_TCI_PROFILE

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
        freq_hz = int(round(float(frequency_khz) * 1000))
        commands: list[str] = [f"vfo:0,0,{freq_hz};"]

        mode_value = (mode or "").strip().lower()
        if mode_value:
            if self.profile == "thetis":
                # Keep Thetis mode set minimal but send both common variants.
                # Some builds accept one form and ignore the other.
                commands.extend(
                    [
                        f"modulation:0,0,{mode_value};",
                        f"modulation:0,{mode_value};",
                    ]
                )
            else:
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
        use_swl_timed_spot: bool = True,
        persistent_swl_spot: bool = False,
    ) -> tuple[bool, str]:
        station_tag = re.sub(r"[^A-Za-z0-9/]", "", (station or "").upper())
        station_tag = station_tag[:12]
        if not station_tag:
            station_tag = "M0SWL"

        freq_hz = int(round(float(frequency_khz) * 1000))
        mode_raw = (mode or "").strip().lower()
        mode_map = {
            "am": "am",
            "fm": "fm",
            "lsb": "lsb",
            "usb": "usb",
            "ssb": "ssb",
            "cw": "cw",
        }
        spot_mode = mode_map.get(mode_raw, "ssb")
        ttl_value = 0 if persistent_swl_spot else max(1, int(ttl_seconds))
        # Thetis builds now carry SWL TTL via JSON tags (IsSWL / SWLSecondsToLive),
        # so mode should remain plain (without -swl[n] suffix).
        spot_mode_token = spot_mode.upper()
        utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "spotter": "SWL_View",
            "comment": f"SWL schedule {mode_raw or 'am'}",
            "heading": 0,
            "continent": "",
            "country": "",
            "utctime": utc_now,
            "TextColor": "#FF00FF00",
            "IsSWL": bool(use_swl_timed_spot),
            "SWLSecondsToLive": ttl_value if use_swl_timed_spot else 0,
        }
        payload_json = json.dumps(payload, separators=(",", ":"))
        if self.profile == "expert":
            text_value = f"SWL schedule {mode_raw or 'am'}"
            text_value = text_value.replace(",", " ").replace(";", " ").strip() or "SWL_View"
            argb = "16711680"
            commands = [f"SPOT:{station_tag},{spot_mode.upper()},{freq_hz},{argb},{text_value};"]
        else:
            commands = [f"SPOT:{station_tag},{spot_mode_token},{freq_hz},20381,[json]{payload_json};"]

        with self._lock:
            if self._ws is None:
                self.last_error = "Not connected"
                return False, self.last_error
            try:
                sent: list[str] = []
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

    def set_mute(self, muted: bool) -> tuple[bool, str]:
        value = 1 if muted else 0
        bool_token = "true" if muted else "false"
        commands = [
            f"mute:{value};",
            f"mute:0,{value};",
            f"mute:{bool_token};",
            f"mute:0,{bool_token};",
            f"audio_mute:{value};",
            f"audio_mute:0,{value};",
            f"rx_mute:{value};",
            f"rx_mute:0,{value};",
        ]
        with self._lock:
            if self._ws is None:
                self.last_error = "Not connected"
                return False, self.last_error
            try:
                sent: list[str] = []
                for cmd in commands:
                    self._ws.send(cmd)
                    sent.append(cmd)
                    time.sleep(0.02)
                self.muted = bool(muted)
                self.last_command = " ".join(sent)
                self.last_error = ""
                return True, self.last_command
            except Exception as exc:
                self.last_error = str(exc)
                self._disconnect_locked()
                return False, self.last_error


TCI = TCIClient()


def load_local_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_local_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def save_tci_settings(host: str, port: int, send_spot: bool, profile: str = DEFAULT_TCI_PROFILE) -> None:
    config = load_local_config()
    config.setdefault("tci", {})
    profile_value = str(profile).strip().lower()
    config["tci"]["host"] = host
    config["tci"]["port"] = int(port)
    config["tci"]["send_spot"] = bool(send_spot)
    config["tci"]["profile"] = profile_value if profile_value in VALID_TCI_PROFILES else DEFAULT_TCI_PROFILE
    save_local_config(config)


def save_tci_spot_behavior(use_swl_timed_spot: bool, persistent_swl_spot: bool) -> None:
    config = load_local_config()
    config.setdefault("tci", {})
    config["tci"]["use_swl_timed_spot"] = bool(use_swl_timed_spot)
    config["tci"]["persistent_swl_spot"] = bool(persistent_swl_spot)
    save_local_config(config)


def get_send_spot() -> bool:
    return bool(load_local_config().get("tci", {}).get("send_spot", DEFAULT_SEND_SPOT))


def get_tci_profile() -> str:
    profile_value = str(load_local_config().get("tci", {}).get("profile", DEFAULT_TCI_PROFILE)).strip().lower()
    return profile_value if profile_value in VALID_TCI_PROFILES else DEFAULT_TCI_PROFILE


def get_use_swl_timed_spot() -> bool:
    return bool(load_local_config().get("tci", {}).get("use_swl_timed_spot", DEFAULT_USE_SWL_TIMED_SPOT))


def get_persistent_swl_spot() -> bool:
    return bool(load_local_config().get("tci", {}).get("persistent_swl_spot", DEFAULT_PERSISTENT_SWL_SPOT))


def bootstrap_tci_from_config() -> None:
    config = load_local_config()
    tci_cfg = config.get("tci", {})
    host = str(tci_cfg.get("host", TCI.host))
    port = int(tci_cfg.get("port", TCI.port))
    profile = str(tci_cfg.get("profile", DEFAULT_TCI_PROFILE))
    TCI.configure(host, port, profile=profile)
