"""Meal Keeper as a desktop application: the app in its own window, no browser or terminal.

Run it from this folder with:  .\\.venv\\Scripts\\python desktop.py
or build "Meal Keeper.exe" (see README.md).
"""
import os
import threading

import webview
from werkzeug.serving import make_server

from app import app, prepare_database


def main():
    prepare_database()
    app.config["SECRET_KEY"] = os.urandom(24)

    # The pages are served only to this computer, on whichever port is free.
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    webview.settings["ALLOW_DOWNLOADS"] = True  # the CSV shopping list
    webview.create_window(
        "Meal Keeper", f"http://127.0.0.1:{server.server_port}/",
        width=1100, height=800, min_size=(480, 480),
    )
    webview.start()  # returns when the window is closed
    server.shutdown()


if __name__ == "__main__":
    main()
