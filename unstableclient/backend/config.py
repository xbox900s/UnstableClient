from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

CONFIG_VERSION = 1


def get_base_dir() -> Path:
    home = Path.home()
    return home / ".unstableclient"


def ensure_base_dirs() -> Dict[str, Path]:
    base = get_base_dir()
    paths = {
        "base": base,
        "config": base / "config",
        "cache": base / "cache",
        "exports": base / "exports",
        "logs": base / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def get_config_path() -> Path:
    paths = ensure_base_dirs()
    return paths["config"] / "config.json"


def default_paths() -> Dict[str, str]:
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")) / "ModrinthApp"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "ModrinthApp"
    else:
        base = home / ".modrinth"
    return {
        "app_path": str(base),
        "profiles_path": str(base / "profiles"),
    }


def load_config() -> Dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_config(payload: Dict[str, Any]) -> None:
    config_path = get_config_path()
    data = {"version": CONFIG_VERSION, **payload}
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp_path, config_path)
