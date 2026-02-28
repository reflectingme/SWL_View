#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "release" / "dist"
APP_MAIN = ROOT / "app" / "main.py"
MACOS_QS = ROOT / "release" / "templates" / "QUICKSTART-macos.md"
WIN_QS = ROOT / "release" / "templates" / "QUICKSTART-windows.md"

EXCLUDED_PREFIXES = (
    ".git/",
    "release/dist/",
)


def read_version() -> str:
    text = APP_MAIN.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
    if not match:
        raise RuntimeError("Could not find APP_VERSION in app/main.py")
    return match.group(1)


def tracked_files() -> list[Path]:
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files"],
        text=True,
    )
    items: list[Path] = []
    for line in out.splitlines():
        rel = line.strip()
        if not rel:
            continue
        if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        items.append(ROOT / rel)
    return items


def build_zip(zip_name: str, quickstart_path: Path) -> Path:
    version = read_version()
    package_root = f"SWL_View-{zip_name}-v{version}"
    out_path = DIST / f"{package_root}.zip"
    files = tracked_files()

    DIST.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    with ZipFile(out_path, "w", compression=ZIP_DEFLATED) as zf:
        for src in files:
            rel = src.relative_to(ROOT).as_posix()
            zf.write(src, f"{package_root}/{rel}")
        zf.write(quickstart_path, f"{package_root}/QUICKSTART.md")

    return out_path


def main() -> int:
    version = read_version()
    print(f"Building release packages for SWL View v{version} ...")
    mac_zip = build_zip("macos", MACOS_QS)
    win_zip = build_zip("win11", WIN_QS)
    print(f"Created: {mac_zip}")
    print(f"Created: {win_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
