"""Easy Video Downloader - a glass-themed desktop front end for yt-dlp.

Run with:  python app.py
"""
from __future__ import annotations

import sys
import tkinter.messagebox as mb
from evd import errors
from evd.ui import App


def main() -> int:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Pillow is required:  pip install pillow", file=sys.stderr)
        return 2

    app = App()
    errors.install(app.root)
    if not app.engine.exe:
        mb.showwarning(
            "yt-dlp not found",
            "yt-dlp is not on your PATH.\n\n"
            "Install it with one of:\n"
            "    winget install yt-dlp.yt-dlp\n"
            "    pip install -U yt-dlp\n\n"
            "The window will open, but downloads will fail until it is installed.",
            parent=app.root,
        )
    try:
        app.run()
    except Exception:
        import sys as _sys
        path = errors.log(*_sys.exc_info(), note="mainloop")
        mb.showerror("Easy Video Downloader stopped",
                     "Something went wrong. The details were written to:\n\n%s" % path)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())