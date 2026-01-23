from __future__ import annotations

import logging
import os
import threading
import webbrowser

from backend.app_factory import create_app
from backend.config import ensure_base_dirs
from backend.logging_utils import setup_logging


def run_server(port: int) -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=port, threaded=True)


def main() -> None:
    ensure_base_dirs()
    setup_logging()
    port = int(os.environ.get("UNSTABLECLIENT_PORT", "5391"))
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{port}"

    try:
        import webview  # type: ignore

        window = webview.create_window("Modpacks", url)
        webview.start()
    except Exception as exc:
        logging.warning("pywebview unavailable: %s", exc)
        webbrowser.open(url)
        server_thread.join()


if __name__ == "__main__":
    main()
