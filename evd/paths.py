"""Where the helper scripts should look, without any of it being hardcoded.

The download folder is whatever the app is set to, so the scripts read it from
settings rather than carrying someone's network share around in the source.
"""
from __future__ import annotations

import sys

from . import config


def download_dir(argv: list[str] | None = None) -> str:
    """The download folder: the first argument, else what the app is set to."""
    args = [a for a in (argv if argv is not None else sys.argv[1:])
            if not a.startswith("-")]
    if args:
        return args[0]
    settings = config.load()
    path = (settings.get("outdir") or "").strip()
    if not path:
        raise SystemExit("no download folder set - pass one as an argument")
    return path


def queue_file() -> str:
    return str(config.QUEUE_FILE)


def work_root() -> str:
    from . import downloader
    return downloader.work_root()
