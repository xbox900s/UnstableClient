from __future__ import annotations

import json
import logging
import os
import secrets
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_from_directory

from . import auth, db
from .config import default_paths, ensure_base_dirs, load_config, save_config
from .logging_utils import fetch_recent_logs
from .modrinth import ModrinthClient


VALID_USERNAME = re.compile(r"^[A-Za-z0-9_]{3,16}$")


class APIError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def create_app() -> Flask:
    db.init_db()
    app = Flask(__name__, static_folder=str(Path(__file__).resolve().parents[1] / "frontend"))
    modrinth = ModrinthClient()

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        return jsonify({"ok": False, "error": str(err)}), err.status

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename: str):
        assets_path = Path(__file__).resolve().parents[1] / "assets"
        return send_from_directory(assets_path, filename)

    @app.route("/frontend/<path:filename>")
    def frontend_static(filename: str):
        return send_from_directory(app.static_folder, filename)

    def get_token() -> Optional[str]:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "", 1).strip()
        return None

    def require_user() -> Dict[str, Any]:
        token = get_token()
        if not token:
            raise APIError("Missing session token", status=401)
        user = auth.get_user_by_session(token)
        if not user:
            raise APIError("Invalid session", status=401)
        if not user.get("is_active", 1):
            raise APIError("User blocked", status=403)
        auth.touch_session(token)
        return user

    def require_role(roles: set[str]) -> Dict[str, Any]:
        user = require_user()
        if user["role"] not in roles:
            raise APIError("Insufficient permissions", status=403)
        return user

    @app.route("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.route("/api/config")
    def get_config():
        config = load_config()
        ready = bool(config.get("installed"))
        return jsonify({"ok": True, "installed": ready, "config": config, "defaults": default_paths()})

    @app.route("/api/wizard/setup", methods=["POST"])
    def wizard_setup():
        data = request.json or {}
        app_path = data.get("app_path")
        profiles_path = data.get("profiles_path")
        minecraft_name = data.get("minecraft_name")
        create_shortcut = bool(data.get("create_shortcut"))
        if not app_path or not profiles_path:
            raise APIError("Missing required paths")
        if not minecraft_name or not VALID_USERNAME.match(minecraft_name):
            raise APIError("Invalid Minecraft name")
        ensure_base_dirs()
        Path(app_path).mkdir(parents=True, exist_ok=True)
        Path(profiles_path).mkdir(parents=True, exist_ok=True)
        config = {
            "installed": True,
            "app_path": app_path,
            "profiles_path": profiles_path,
            "minecraft_name": minecraft_name,
            "create_shortcut": create_shortcut,
            "theme": "glass",
        }
        save_config(config)
        if create_shortcut and sys.platform.startswith("win"):
            _create_windows_shortcut()
        logging.info("Wizard completed")
        return jsonify({"ok": True, "config": config})

    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.json or {}
        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        confirm = data.get("confirm") or ""
        if not email or "@" not in email:
            raise APIError("Invalid email")
        if not VALID_USERNAME.match(username):
            raise APIError("Invalid username")
        if len(password) < 8:
            raise APIError("Password too short")
        if password != confirm:
            raise APIError("Passwords do not match")
        existing = db.fetch_one("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
        if existing:
            raise APIError("Account already exists")
        user = auth.register_user(email, username, password)
        token = auth.create_session(user["id"])
        return jsonify({"ok": True, "user": user, "token": token})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.json or {}
        identifier = (data.get("identifier") or "").strip()
        password = data.get("password") or ""
        if not identifier or not password:
            raise APIError("Missing credentials")
        user = auth.authenticate(identifier, password)
        if not user:
            raise APIError("Invalid credentials", status=401)
        token = auth.create_session(user["id"])
        return jsonify({"ok": True, "user": user, "token": token})

    @app.route("/api/session")
    def session_info():
        user = require_user()
        return jsonify({"ok": True, "user": user})

    @app.route("/api/profile", methods=["GET", "POST"])
    def profile():
        user = require_user()
        if request.method == "GET":
            return jsonify({"ok": True, "profile": user})
        data = request.json or {}
        description = (data.get("description") or "").strip()
        if len(description) > 280:
            raise APIError("Description too long")
        db.execute("UPDATE users SET profile_description = ? WHERE id = ?", (description, user["id"]))
        return jsonify({"ok": True})

    @app.route("/api/logs")
    def logs():
        require_user()
        return jsonify({"ok": True, "logs": fetch_recent_logs()})

    @app.route("/api/modpacks")
    def modpacks():
        require_user()
        config = load_config()
        profiles_path = Path(config.get("profiles_path", ""))
        if not profiles_path.exists():
            raise APIError("Profiles path not found")
        packs = []
        for entry in profiles_path.iterdir():
            if not entry.is_dir():
                continue
            profile_path = entry / "profile.json"
            profile = {}
            if profile_path.exists():
                try:
                    profile = json.loads(profile_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    profile = {}
            mods_dir = entry / "mods"
            mod_count = 0
            if mods_dir.exists():
                mod_count = len([m for m in mods_dir.iterdir() if m.suffix.lower() == ".jar"])
            packs.append(
                {
                    "id": entry.name,
                    "name": profile.get("name", entry.name),
                    "loader": profile.get("loader", "Unknown"),
                    "mc_version": profile.get("game_version", "Unknown"),
                    "path": str(entry),
                    "mod_count": mod_count,
                }
            )
        return jsonify({"ok": True, "modpacks": packs})

    @app.route("/api/modpacks/create", methods=["POST"])
    def create_modpack():
        require_user()
        data = request.json or {}
        name = (data.get("name") or "").strip()
        loader = (data.get("loader") or "").strip()
        mc_version = (data.get("mc_version") or "").strip()
        if not name:
            raise APIError("Name required")
        config = load_config()
        profiles_path = Path(config.get("profiles_path", ""))
        if not profiles_path.exists():
            raise APIError("Profiles path not found")
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
        pack_dir = profiles_path / safe_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "mods").mkdir(exist_ok=True)
        profile_data = {
            "name": name,
            "loader": loader or "Fabric",
            "game_version": mc_version or "1.20.1",
            "created_at": datetime.utcnow().isoformat(),
        }
        profile_path = pack_dir / "profile.json"
        profile_path.write_text(json.dumps(profile_data, indent=2), encoding="utf-8")
        return jsonify({"ok": True})

    @app.route("/api/modpacks/<pack_id>")
    def modpack_detail(pack_id: str):
        require_user()
        config = load_config()
        profiles_path = Path(config.get("profiles_path", ""))
        pack_dir = profiles_path / pack_id
        if not pack_dir.exists():
            raise APIError("Modpack not found", status=404)
        mods_dir = pack_dir / "mods"
        mods = []
        if mods_dir.exists():
            for mod_file in mods_dir.iterdir():
                if mod_file.suffix.lower() != ".jar":
                    continue
                sha1 = modrinth.sha1_for_file(mod_file)
                version = modrinth.get_version_by_hash(sha1)
                mods.append(
                    {
                        "name": mod_file.stem,
                        "filename": mod_file.name,
                        "size": mod_file.stat().st_size,
                        "sha1": sha1,
                        "modrinth": version.get("project_id") if version else None,
                    }
                )
        return jsonify({"ok": True, "mods": mods})

    @app.route("/api/modpacks/<pack_id>/launch", methods=["POST"])
    def launch(pack_id: str):
        require_user()
        config = load_config()
        profiles_path = Path(config.get("profiles_path", ""))
        pack_dir = profiles_path / pack_id
        if not pack_dir.exists():
            raise APIError("Modpack not found", status=404)
        if sys.platform.startswith("win"):
            exe = _find_modrinth_windows_exe()
            if exe:
                subprocess.Popen([str(exe)])
                logging.info("Launch Modrinth: %s", exe)
                return jsonify({"ok": True, "launched": True})
        url = "https://modrinth.com/app"
        logging.warning("Modrinth launch fallback")
        return jsonify({"ok": True, "launched": False, "url": url})

    @app.route("/api/mods/search")
    def mods_search():
        require_user()
        query = request.args.get("q", "")
        loader = request.args.get("loader")
        version = request.args.get("version")
        facets = []
        if loader:
            facets.append([f"categories:{loader}"])
        if version:
            facets.append([f"versions:{version}"])
        try:
            results = modrinth.search_projects(query, facets=facets if facets else None)
        except Exception as exc:
            raise APIError(f"Modrinth error: {exc}")
        return jsonify({"ok": True, "results": results.get("hits", [])})

    @app.route("/api/mods/install", methods=["POST"])
    def mods_install():
        require_user()
        data = request.json or {}
        project_id = data.get("project_id")
        version_id = data.get("version_id")
        pack_id = data.get("pack_id")
        if not project_id or not version_id or not pack_id:
            raise APIError("Missing install data")
        config = load_config()
        profiles_path = Path(config.get("profiles_path", ""))
        pack_dir = profiles_path / pack_id / "mods"
        if not pack_dir.exists():
            raise APIError("Modpack not found")
        version = modrinth.get_version(version_id)
        file_info = next((f for f in version.get("files", []) if f.get("primary")), None)
        if not file_info:
            raise APIError("No downloadable file")
        filename = file_info["filename"]
        url = file_info["url"]
        dest_path = pack_dir / filename
        modrinth.download_file(url, dest_path)
        return jsonify({"ok": True})

    @app.route("/api/admin/users")
    def admin_users():
        require_role({"ADMIN", "MANAGER", "OWNER"})
        users = db.fetch_all("SELECT id, email, username, role, is_active, profile_description, created_at FROM users")
        return jsonify({"ok": True, "users": users})

    @app.route("/api/admin/role", methods=["POST"])
    def admin_role():
        user = require_role({"ADMIN", "MANAGER", "OWNER"})
        data = request.json or {}
        user_id = data.get("user_id")
        role = data.get("role")
        if role not in auth.ROLE_ORDER:
            raise APIError("Invalid role")
        db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        logging.info("Role updated by %s", user["id"])
        return jsonify({"ok": True})

    @app.route("/api/admin/block", methods=["POST"])
    def admin_block():
        require_role({"ADMIN", "MANAGER", "OWNER"})
        data = request.json or {}
        user_id = data.get("user_id")
        is_active = bool(data.get("is_active", True))
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
        return jsonify({"ok": True})

    @app.route("/api/admin/code", methods=["POST"])
    def admin_code():
        user = require_role({"MANAGER", "OWNER"})
        data = request.json or {}
        role = data.get("role")
        duration_days = int(data.get("duration_days", 30))
        if role not in auth.ROLE_ORDER:
            raise APIError("Invalid role")
        code = _generate_code()
        db.execute(
            "INSERT INTO codes (code, role, duration_days, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
            (code, role, duration_days, datetime.utcnow().isoformat(), user["id"]),
        )
        return jsonify({"ok": True, "code": code})

    @app.route("/api/settings/theme", methods=["POST"])
    def update_theme():
        require_user()
        data = request.json or {}
        theme = data.get("theme")
        config = load_config()
        config["theme"] = theme
        save_config(config)
        return jsonify({"ok": True})

    return app


def _find_modrinth_windows_exe() -> Optional[Path]:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "ModrinthApp" / "ModrinthApp.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Modrinth App" / "Modrinth App.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _create_windows_shortcut() -> None:
    shortcut_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    shortcut_dir.mkdir(parents=True, exist_ok=True)
    target = Path(sys.executable).resolve()
    script = Path(__file__).resolve().parents[1] / "app.py"
    shortcut_path = shortcut_dir / "UnstableClient.lnk"
    powershell = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$WScript = New-Object -ComObject WScript.Shell;"
            f"$Shortcut = $WScript.CreateShortcut('{shortcut_path}');"
            f"$Shortcut.TargetPath = '{target}';"
            f"$Shortcut.Arguments = '{script}';"
            "$Shortcut.Save();"
        ),
    ]
    subprocess.run(powershell, check=False)


def _generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    segments = []
    for _ in range(4):
        segments.append("".join(secrets.choice(alphabet) for _ in range(4)))
    return "-".join(segments)
