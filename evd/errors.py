"""Crash logging.

A packaged, windowed build has nowhere to print a traceback, so anything that
goes wrong there would otherwise be invisible.  Everything unexpected is
appended to a log file next to the settings, and the path is shown to the user.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from .config import config_dir

LOG_PATH = config_dir() / "crash.log"


def log(exc_type, exc_value, exc_tb, note: str = "") -> str:
    """Append one traceback to the log; returns the log path as a string."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write("\n" + "=" * 70 + "\n")
            fh.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            fh.write("  frozen=%s\n" % bool(getattr(sys, "frozen", False)))
            if note:
                fh.write(note + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=fh)
    except OSError:
        pass
    return str(LOG_PATH)


def install(root=None) -> None:
    """Route uncaught exceptions - including Tk callback errors - to the log."""
    previous = sys.excepthook

    def hook(exc_type, exc_value, exc_tb):
        log(exc_type, exc_value, exc_tb, note="uncaught")
        previous(exc_type, exc_value, exc_tb)

    sys.excepthook = hook

    if root is not None:
        def tk_error(exc_type, exc_value, exc_tb):
            log(exc_type, exc_value, exc_tb, note="tk callback")
            traceback.print_exception(exc_type, exc_value, exc_tb)

        root.report_callback_exception = tk_error
