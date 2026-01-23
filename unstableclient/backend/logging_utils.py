from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from .config import ensure_base_dirs
from . import db


class DBLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        now = datetime.utcnow().isoformat()
        db.execute(
            "INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)",
            (record.levelname.lower(), message, now),
        )


def setup_logging() -> None:
    paths = ensure_base_dirs()
    log_file = Path(paths["logs"]) / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
            DBLogHandler(),
        ],
    )


def fetch_recent_logs(limit: int = 200) -> List[dict]:
    rows = db.fetch_all(
        "SELECT level, message, created_at FROM logs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return list(reversed(rows))
