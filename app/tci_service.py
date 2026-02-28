from __future__ import annotations

import json
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
CONFIG_FILE = (Path(__file__).parent / "local_config.json").resolve()


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
        freq_hz = int(round(float(frequency_khz) * 1000))
        commands: list[str] = [f"vfo:0,0,{freq_hz};"]

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


def save_tci_settings(host: str, port: int, send_spot: bool) -> None:
    config = load_local_config()
    config.setdefault("tci", {})
    config["tci"]["host"] = host
    config["tci"]["port"] = int(port)
    config["tci"]["send_spot"] = bool(send_spot)
    save_local_config(config)


def get_send_spot() -> bool:
    return bool(load_local_config().get("tci", {}).get("send_spot", DEFAULT_SEND_SPOT))


def bootstrap_tci_from_config() -> None:
    config = load_local_config()
    tci_cfg = config.get("tci", {})
    host = str(tci_cfg.get("host", TCI.host))
    port = int(tci_cfg.get("port", TCI.port))
    TCI.configure(host, port)

