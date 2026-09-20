"""Persistent user settings."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "EasyVideoDownloader"


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_FILE = config_dir() / "settings.json"


def batches_dir() -> Path:
    """Where each queued batch is kept, one file per batch."""
    d = config_dir() / "batches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_download_dir() -> str:
    for candidate in (Path.home() / "Videos", Path.home() / "Downloads", Path.home()):
        if candidate.exists():
            return str(candidate / "EasyVideoDownloader") if candidate.name != "EasyVideoDownloader" else str(candidate)
    return str(Path.home())


DEFAULTS: dict = {
    "outdir": default_download_dir(),
    "quality": "Best available",
    "container": "Auto",
    "audio_format": "mp3",
    "parallel": "2",
    "cookies": "None",
    "cookies_file": "",
    "rate_limit": "",
    "template": "%(title)s [%(id)s].%(ext)s",
    "subtitles": False,
    "sub_langs": "en.*,en",
    "thumbnail": True,
    "metadata": True,
    "sponsorblock": False,
    "playlists": True,
    "archive": False,
    "playlist_folders": True,
    "advanced_open": False,
    "staged": [],           # [[file name, url], ...] not yet downloaded
    "window": "",
}


QUEUE_FILE = config_dir() / "queue.json"


def load_queue() -> list:
    """The queue as it was when the app last saved it."""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as fh:
            rows = json.load(fh)
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def save_queue(rows: list) -> None:
    try:
        with open(QUEUE_FILE, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
    except (OSError, TypeError):
        pass


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return data


def save(data: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump({k: data.get(k, v) for k, v in DEFAULTS.items()}, fh, indent=2)
    except OSError:
        pass
