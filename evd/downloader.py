"""Queue engine that drives the yt-dlp command line.

Each job is one URL handled by one yt-dlp process.  Progress is read back
through --progress-template, which gives machine-readable fields instead of the
human progress bar, so parsing stays robust across yt-dlp versions.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from .config import config_dir
from urllib.parse import urlsplit

SEP = "|EVD|"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

PROGRESS_TEMPLATE = SEP.join([
    "download:" + SEP + "P",
    "%(progress.status)s",
    "%(progress.downloaded_bytes)s",
    "%(progress.total_bytes)s",
    "%(progress.total_bytes_estimate)s",
    "%(progress.speed)s",
    "%(progress.eta)s",
    "%(info.playlist_index)s",
    "%(info.n_entries)s",
    "%(info.title)s",
])
PRINT_TEMPLATE = "after_move:" + SEP + "F" + SEP + "%(filepath)s"

# ------------------------------------------------------------------ options --
QUALITY = ["Best available", "2160p (4K)", "1440p", "1080p", "720p", "480p", "Audio only"]
HEIGHTS = {"2160p (4K)": 2160, "1440p": 1440, "1080p": 1080, "720p": 720, "480p": 480}
CONTAINERS = ["Auto", "mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav"]
COOKIE_SOURCES = ["None", "cookies.txt file", "chrome", "edge", "firefox",
                  "brave", "chromium", "opera", "vivaldi"]
COOKIE_FILE_CHOICE = "cookies.txt file"
PARALLEL = ["1", "2", "3", "4", "5", "6"]

# ------------------------------------------------------------------ status --
QUEUED, RUNNING, POST, DONE, ERROR, CANCELED, PAUSED, HELD = (
    "Queued", "Downloading", "Processing", "Done", "Failed", "Canceled",
    "Paused", "On hold")
MAX_AUTO_RETRIES = 2          # automatic attempts after a transient failure
ACTIVITY_LOG = config_dir() / "activity.log"
LOG_LIMIT = 2_000_000         # bytes before the log rolls over

ACTIVE = (RUNNING, POST)
FINISHED = (DONE, ERROR, CANCELED)
RESUMABLE = (PAUSED, HELD)          # stopped by the user, can carry on
PENDING = (QUEUED, PAUSED, HELD)    # not finished, not currently running
ALL_STATUSES = (QUEUED, RUNNING, POST, PAUSED, HELD, DONE, ERROR, CANCELED)

def looks_like_playlist(url: str) -> bool:
    """Whether a URL is expected to expand into several videos.

    Deliberately strict and host-aware: a loose substring test matches things
    like ".../commons/c/c8/file.ogg" and would wrongly file single downloads
    into a playlist folder.
    """
    try:
        parts = urlsplit(url.lower())
    except ValueError:
        return False
    host, path, query = parts.netloc, parts.path, parts.query

    if "list=" in query:
        return True
    if path.startswith("/playlist") or "/playlist/" in path:
        return True
    if "youtube.com" in host or "youtu.be" in host:
        if any(path.startswith(prefix) for prefix in ("/channel/", "/c/", "/user/", "/@")):
            return True
        return path.endswith(("/videos", "/streams", "/shorts"))
    if "soundcloud.com" in host:
        return "/sets/" in path
    if "bandcamp.com" in host:
        return path.startswith("/album/")
    if "vimeo.com" in host:
        return path.startswith(("/album/", "/channels/", "/showcase/"))
    return False


def work_root() -> str:
    """Local scratch space for in-progress downloads."""
    d = os.path.join(tempfile.gettempdir(), "EasyVideoDownloader", "work")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return tempfile.gettempdir()
    return d


def job_work_dir(job_id: str) -> str:
    """A private scratch directory for one job.

    Two videos can easily resolve to the same title and id, which means the
    same .part and .part-FragNN names. Sharing a directory then lets parallel
    downloads overwrite each other's fragments, which surfaces later as
    decryption or missing-file errors that have nothing to do with the video.
    """
    d = os.path.join(work_root(), job_id)
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return work_root()
    return d


def sweep_work_dirs(max_age_days: int = 7) -> None:
    """Drop scratch directories left behind by an earlier run."""
    root = work_root()
    cutoff = time.time() - max_age_days * 86400
    try:
        entries = os.listdir(root)
    except OSError:
        return
    for name in entries:
        path = os.path.join(root, name)
        try:
            if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


# Failures worth trying again by themselves: a dropped share, a truncated or
# rate-limited fragment, a server hiccup.
_TRANSIENT = (
    "errno 2", "no such file or directory", "unable to open for writing",
    "padded to 16 byte boundary", "connection reset", "connection aborted",
    "timed out", "timeout", "temporary failure", "content too short",
    "incomplete read", "network is unreachable", "http error 5",
    "http error 429", "unable to download video data", "read error",
)
# Failures that will never come good, so retrying only wastes time.
_PERMANENT = (
    "unsupported url", "is not a valid url", "video unavailable",
    "private video", "members-only", "removed by the uploader",
    "sign in to confirm", "http error 404", "no video formats found",
    "requested format is not available",
)


def is_transient(error: str) -> bool:
    text = (error or "").lower()
    if any(p in text for p in _PERMANENT):
        return False
    return any(t in text for t in _TRANSIENT)


def find_ytdlp() -> str | None:
    exe = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if exe:
        return exe
    if getattr(sys, "frozen", False):
        # in a packaged build sys.executable is this app, not an interpreter,
        # so the "python -m yt_dlp" fallback would relaunch the GUI
        return None
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW)
        return sys.executable
    except Exception:
        return None


def ytdlp_version(exe: str | None) -> str:
    if not exe:
        return "not found"
    cmd = [exe, "--version"] if not exe.endswith("python.exe") else [exe, "-m", "yt_dlp", "--version"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25,
                             creationflags=CREATE_NO_WINDOW)
        return (out.stdout or "").strip() or "unknown"
    except Exception:
        return "unknown"


def normalize_outdir(path: str) -> str:
    """Clean and validate output directory, handling Windows UNC shares safely."""
    if not path:
        return "."
    p = path.strip().strip('"').strip("'")
    if os.name == "nt":
        p = p.replace("/", "\\")
        # Ensure IP addresses or hostnames without leading slashes get full UNC formatting
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\\", p):
            p = "\\\\" + p
        # Strip trailing backslash to prevent Windows subprocess argument escaping bugs
        if len(p) > 3 and p.endswith("\\"):
            p = p.rstrip("\\")
    else:
        if len(p) > 1 and p.endswith("/"):
            p = p.rstrip("/")
    return p


def _num(value: str) -> float | None:
    if not value or value in ("NA", "None", "none"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def human_size(n: float | None) -> str:
    if not n:
        return "--"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return ("%.0f %s" if unit == "B" else "%.1f %s") % (n, unit)
        n /= 1024.0
    return "--"


def human_speed(n: float | None) -> str:
    return human_size(n) + "/s" if n else "--"


def human_eta(sec: float | None) -> str:
    if sec is None:
        return "--"
    sec = int(sec)
    if sec >= 3600:
        return "%d:%02d:%02d" % (sec // 3600, (sec % 3600) // 60, sec % 60)
    return "%d:%02d" % (sec // 60, sec % 60)


# --------------------------------------------------------------------- job --
@dataclass
class Job:
    url: str
    opts: dict
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = QUEUED
    title: str = ""
    pct: float = 0.0
    speed: float | None = None
    eta: float | None = None
    downloaded: float | None = None
    total: float | None = None
    item: int = 0
    items: int = 0
    filepath: str = ""
    files: int = 0
    error: str = ""
    stage: str = ""
    added: float = field(default_factory=time.time)
    started: float = 0.0
    ended: float = 0.0
    log: deque = field(default_factory=lambda: deque(maxlen=400))
    cancelled: bool = False
    paused: bool = False
    attempts: int = 0          # automatic retries used so far
    retry_at: float = 0.0      # not eligible to start before this time
    skipped: bool = False      # the target file was already there
    duplicate: bool = False    # another job wrote the same file
    force: bool = False        # a manual retry may replace that file
    gentle: bool = False       # retry politely after a refused request
    name: str = ""            # per-video output name, no extension

    @property
    def label(self) -> str:
        return self.title or self.name or self.url

    @property
    def is_playlist(self) -> bool:
        return self.items > 1


# ------------------------------------------------------------------ engine --
class Engine:
    """Runs jobs with a bounded number of parallel yt-dlp processes."""

    def __init__(self, on_log=None):
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self.dirty: set[str] = set()
        self.log_lines: deque = deque(maxlen=3000)
        self.running = False
        self.max_parallel = 2
        self.exe = find_ytdlp()
        self.ffmpeg = shutil.which("ffmpeg")
        self._procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()
        self._stop = False
        self._on_log = on_log
        sweep_work_dirs()
        self._thread = threading.Thread(target=self._schedule, daemon=True)
        self._thread.start()

    # -- queue management ----------------------------------------------
    def add(self, url: str, opts: dict, held: bool = False, name: str = "") -> Job:
        job = Job(url=url.strip(), opts=dict(opts), name=name.strip())
        if held:
            job.status = HELD
        with self._lock:
            self.jobs[job.id] = job
            self.order.append(job.id)
            self.dirty.add(job.id)
        return job

    def export_jobs(self, keep_done: int = 50) -> list[dict]:
        """The queue in a form that can be written to disk and read back."""
        rows = []
        done_seen = 0
        for job in reversed(self.all_jobs()):          # newest first for the cap
            if job.status == DONE:
                done_seen += 1
                if done_seen > keep_done:
                    continue
            rows.append({
                # the id names the scratch folder holding the part-downloaded
                # fragments, so keeping it is what lets a restart carry on
                # instead of fetching the whole video again
                "id": job.id,
                "url": job.url, "name": job.name, "title": job.title,
                "status": job.status, "opts": job.opts, "error": job.error,
                "filepath": job.filepath, "pct": round(job.pct, 4),
                "attempts": job.attempts, "item": job.item, "items": job.items,
                "total": job.total, "skipped": job.skipped,
            })
        rows.reverse()
        return rows

    def import_jobs(self, rows) -> int:
        """Rebuild the queue from a saved copy. Nothing starts by itself."""
        restored = 0
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            url = (row.get("url") or "").strip()
            if not url:
                continue
            opts = row.get("opts") if isinstance(row.get("opts"), dict) else {}
            job = self.add(url, opts, name=str(row.get("name") or ""))
            # put the job back under its old id so it finds the fragments it
            # had already downloaded, rather than starting the video again
            old_id = str(row.get("id") or "")
            if old_id and old_id not in self.jobs:
                with self._lock:
                    self.jobs.pop(job.id, None)
                    self.order[self.order.index(job.id)] = old_id
                    self.dirty.discard(job.id)
                    job.id = old_id
                    self.jobs[old_id] = job
                    self.dirty.add(old_id)
            status = row.get("status")
            if status in (RUNNING, POST):
                status = PAUSED        # its process died with the old session
            if status in ALL_STATUSES:
                job.status = status
            job.title = str(row.get("title") or "")
            job.error = str(row.get("error") or "")
            job.filepath = str(row.get("filepath") or "")
            job.skipped = bool(row.get("skipped"))
            try:
                job.pct = float(row.get("pct") or 0.0)
                job.attempts = int(row.get("attempts") or 0)
                job.item = int(row.get("item") or 0)
                job.items = int(row.get("items") or 0)
                job.total = float(row["total"]) if row.get("total") else None
            except (TypeError, ValueError):
                pass
            restored += 1
        return restored

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def all_jobs(self) -> list[Job]:
        with self._lock:
            return [self.jobs[i] for i in self.order if i in self.jobs]

    def take_dirty(self) -> set[str]:
        with self._lock:
            d, self.dirty = self.dirty, set()
            return d

    def touch(self, job_id: str):
        with self._lock:
            self.dirty.add(job_id)

    def start(self):
        self.running = True

    def pause(self):
        """Stop launching new jobs; jobs already downloading keep going."""
        self.running = False

    def counts(self) -> dict:
        c = {status: 0 for status in ALL_STATUSES}
        for j in self.all_jobs():
            c[j.status] = c.get(j.status, 0) + 1
        c["active"] = c[RUNNING] + c[POST]
        c["pending"] = c[QUEUED] + c[PAUSED] + c[HELD]
        c["holding"] = c[PAUSED] + c[HELD]
        c["total"] = len(self.order)
        return c

    def total_speed(self) -> float:
        return sum(j.speed or 0 for j in self.all_jobs() if j.status == RUNNING)

    def pause_job(self, job_id: str):
        """Stop a job but keep its progress: the .part file lets it carry on."""
        job = self.jobs.get(job_id)
        if not job:
            return
        with self._lock:                  # never while a launch is in flight
            if job.status in ACTIVE:
                job.paused = True
                proc = self._procs.get(job_id)
                if proc and proc.poll() is None:
                    self._kill(proc)      # _run() settles the final status
                else:
                    # still being prepared: _run sees job.paused and stops
                    job.status = PAUSED
            elif job.status == QUEUED:
                job.status = HELD         # never started, so nothing to resume
        self.touch(job_id)

    def resume_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job or job.status not in RESUMABLE:
            return
        job.paused = False
        job.cancelled = False
        job.status = QUEUED
        job.retry_at = 0.0
        job.stage = ""
        job.ended = 0.0
        self.touch(job_id)
        self.running = True

    def pause_jobs(self, job_ids):
        for jid in list(job_ids):
            self.pause_job(jid)

    def resume_jobs(self, job_ids):
        for jid in list(job_ids):
            self.resume_job(jid)

    def cancel_jobs(self, job_ids):
        for jid in list(job_ids):
            self.cancel(jid)

    def pause_all(self):
        """Stop launching new jobs and pause everything already running."""
        self.running = False
        for job in self.all_jobs():
            if job.status in ACTIVE:
                self.pause_job(job.id)

    def resume_all(self):
        """Start working the queue, releasing anything held or paused."""
        for job in self.all_jobs():
            if job.status in RESUMABLE:
                self.resume_job(job.id)
        self.running = True

    def cancel(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        with self._lock:                  # never while a launch is in flight
            job.cancelled = True
            job.paused = False
            proc = self._procs.get(job_id)
            if proc and proc.poll() is None:
                self._kill(proc)
            elif job.status not in FINISHED:
                job.status = CANCELED
                job.ended = time.time()
        self.touch(job_id)

    def cancel_all(self):
        for job in self.all_jobs():
            if job.status not in FINISHED:
                self.cancel(job.id)

    def retry(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job or job.status in ACTIVE:
            return
        job.status = QUEUED
        job.pct = 0.0
        job.error = ""
        job.stage = ""
        job.speed = job.eta = None
        job.cancelled = False
        job.paused = False
        job.attempts = 0          # a manual retry starts the count again
        job.retry_at = 0.0
        job.skipped = False
        job.force = True          # asked for again, so replace what is there
        job.gentle = True         # it failed once, so go easy this time
        job.ended = 0.0
        self.touch(job_id)

    def remove(self, job_id: str):
        self.cancel(job_id)
        with self._lock:
            self.jobs.pop(job_id, None)
            if job_id in self.order:
                self.order.remove(job_id)

    def clear_finished(self):
        with self._lock:
            for jid in list(self.order):
                if self.jobs[jid].status in FINISHED:
                    self.jobs.pop(jid, None)
                    self.order.remove(jid)

    def clear_all(self):
        self.cancel_all()
        with self._lock:
            self.jobs.clear()
            self.order.clear()

    def shutdown(self):
        self._stop = True
        self.cancel_all()

    # -- scheduling ----------------------------------------------------
    def _schedule(self):
        while not self._stop:
            try:
                if self.running:
                    with self._lock:
                        active = sum(1 for j in self.jobs.values() if j.status in ACTIVE)
                        slots = self.max_parallel - active
                        for jid in list(self.order):
                            if slots <= 0:
                                break
                            job = self.jobs.get(jid)
                            if (job and job.status == QUEUED
                                    and job.retry_at <= time.time()):
                                job.status = RUNNING
                                job.started = time.time()
                                job.stage = "connecting"
                                self.dirty.add(jid)
                                threading.Thread(target=self._run, args=(job,),
                                                 daemon=True).start()
                                slots -= 1
            except Exception as exc:  # scheduler must never die
                self._log("scheduler error: %r" % (exc,))
            time.sleep(0.12)

    def _log(self, line: str, job: Job | None = None):
        stamp = time.strftime("%H:%M:%S")
        text = "[%s] %s" % (stamp, line)
        self.log_lines.append(text)
        self._write_log(text)
        if job is not None:
            job.log.append(text)
        if self._on_log:
            self._on_log(text)

    def _write_log(self, text: str):
        """Keep yt-dlp output on disk; the window may not be open when it fails."""
        try:
            if ACTIVITY_LOG.exists() and ACTIVITY_LOG.stat().st_size > LOG_LIMIT:
                ACTIVITY_LOG.replace(ACTIVITY_LOG.with_suffix(".log.1"))
            with open(ACTIVITY_LOG, "a", encoding="utf-8", errors="replace") as fh:
                fh.write(text + "\n")
        except OSError:
            pass

    def _kill(self, proc: subprocess.Popen):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, creationflags=CREATE_NO_WINDOW)
            else:
                proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # -- process -------------------------------------------------------
    def _run(self, job: Job):
        if not self.exe:
            job.status = ERROR
            job.error = "yt-dlp was not found on PATH"
            job.ended = time.time()
            self.touch(job.id)
            return

        outdir = normalize_outdir(job.opts.get("outdir") or ".")
        try:
            os.makedirs(outdir, exist_ok=True)
        except OSError as exc:
            job.status = ERROR
            job.error = "cannot create %s: %s" % (outdir, exc)
            job.ended = time.time()
            self.touch(job.id)
            return

        args = self.build_args(job)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        # Getting this far can block for seconds when the download folder is
        # on a network share. Pausing the row during that window used to mark
        # it Paused - freeing its slot - while this thread carried on and
        # launched anyway. That download then ran untracked, the freed slot
        # started another, and the parallel limit stopped meaning anything.
        # Deciding and launching under one lock closes the window: either the
        # pause lands first and nothing starts, or the process is registered
        # and the pause can kill it.
        with self._lock:
            if job.cancelled or job.paused:
                job.status = CANCELED if job.cancelled else PAUSED
                job.ended = time.time()
                self.touch(job.id)
                return
            self._log("start: %s" % job.url, job)
            try:
                proc = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                    creationflags=CREATE_NO_WINDOW, env=env,
                    cwd=None,
                )
            except Exception as exc:
                job.status = ERROR
                job.error = str(exc)
                job.ended = time.time()
                self.touch(job.id)
                return
            self._procs[job.id] = proc
        try:
            for line in proc.stdout:
                self._parse(job, line.rstrip("\r\n"))
        except Exception as exc:
            self._log("read error: %r" % (exc,), job)
        finally:
            rc = proc.wait()
            self._procs.pop(job.id, None)

        job.ended = time.time()
        job.speed = None
        job.eta = None
        if job.paused:
            job.status = PAUSED       # keeps job.pct, so the bar shows progress
        elif job.cancelled:
            job.status = CANCELED
        elif rc == 0:
            job.status = DONE
            job.pct = 1.0
            job.stage = ""
        elif (job.attempts < MAX_AUTO_RETRIES and is_transient(job.error)
              and not job.cancelled):
            # A dropped share or a mangled fragment usually works second time,
            # so try again before bothering anyone about it.
            job.attempts += 1
            job.status = QUEUED
            job.retry_at = time.time() + 5 * job.attempts
            job.stage = "retry %d of %d" % (job.attempts, MAX_AUTO_RETRIES)
            job.gentle = True
            self._log("retrying (%d/%d) after: %s"
                      % (job.attempts, MAX_AUTO_RETRIES, job.error[:160]), job)
            job.error = ""
            self.touch(job.id)
            return
        else:
            job.status = ERROR
            if not job.error:
                job.error = "yt-dlp exited with code %d" % rc
        if job.status == DONE:
            shutil.rmtree(job_work_dir(job.id), ignore_errors=True)
            # Two jobs can land on one filename - the second move silently
            # replaces the first - so say so rather than lose a file quietly.
            if job.filepath:
                for other in self.all_jobs():
                    if (other.id != job.id and other.status == DONE
                            and other.filepath == job.filepath):
                        job.duplicate = other.duplicate = True
                        self.touch(other.id)
        self._log("%s: %s" % (job.status.lower(), job.label), job)
        self.touch(job.id)

    # -- output parsing ------------------------------------------------
    def _parse(self, job: Job, line: str):
        if not line:
            return

        if line.startswith(SEP):
            parts = line.split(SEP)
            kind = parts[1] if len(parts) > 1 else ""
            if kind == "P" and len(parts) >= 11:
                self._progress(job, parts)
                return
            if kind == "F" and len(parts) >= 3:
                job.filepath = SEP.join(parts[2:]).strip()
                job.files += 1
                job.stage = ""
                self.touch(job.id)
                self._log("saved: %s" % job.filepath, job)
                return

        self._log(line, job)

        low = line.lower()
        if line.startswith("ERROR:"):
            job.error = line[6:].strip()[:400]
        elif "[merger]" in low:
            job.stage = "merging"
            job.status = POST if job.status == RUNNING else job.status
        elif "[extractaudio]" in low:
            job.stage = "extracting audio"
            job.status = POST if job.status == RUNNING else job.status
        elif "[embedsubtitle]" in low or "[metadata]" in low or "[thumbnailsembedder]" in low:
            job.stage = "embedding"
            job.status = POST if job.status == RUNNING else job.status
        elif "[sponsorblock]" in low or "[modifychapters]" in low:
            job.stage = "sponsorblock"
            job.status = POST if job.status == RUNNING else job.status
        elif "has already been downloaded" in low:
            job.stage = ""
            job.skipped = True
            job.pct = 1.0
        elif low.startswith("[download] downloading item"):
            m = re.search(r"item (\d+) of (\d+)", low)
            if m:
                job.item, job.items = int(m.group(1)), int(m.group(2))
        self.touch(job.id)

    def _progress(self, job: Job, parts: list[str]):
        status = parts[2]
        downloaded = _num(parts[3])
        total = _num(parts[4]) or _num(parts[5])
        speed = _num(parts[6])
        eta = _num(parts[7])
        index = _num(parts[8])
        count = _num(parts[9])
        title = SEP.join(parts[10:]).strip()

        if title and title not in ("NA", "None"):
            job.title = title
        if index:
            job.item = int(index)
        if count:
            job.items = int(count)

        job.downloaded, job.total = downloaded, total
        job.speed, job.eta = speed, eta

        frac = 0.0
        if total and downloaded is not None and total > 0:
            frac = max(0.0, min(1.0, downloaded / total))
        if status == "finished":
            frac = 1.0
            job.speed = None
            job.eta = None

        if job.items > 1 and job.item:
            job.pct = max(0.0, min(1.0, ((job.item - 1) + frac) / job.items))
        else:
            job.pct = frac

        if job.status == RUNNING:
            job.stage = "" if status == "downloading" else status
        self.touch(job.id)

    # -- command line --------------------------------------------------
    def build_args(self, job: Job) -> list[str]:
        o = job.opts
        exe = self.exe or "yt-dlp"
        args = [exe]
        if exe.endswith("python.exe"):
            args += ["-m", "yt_dlp"]

        args += [
            "--ignore-config", "--no-color", "--newline", "--progress",
            "--no-simulate", "--no-quiet",
            "--progress-delta", "0.25",
            "--progress-template", PROGRESS_TEMPLATE,
            "--print", PRINT_TEMPLATE,
            "--retries", "10", "--fragment-retries", "10",
            # Ride out a share that blinks off, and back off instead of
            # hammering a server that is rate limiting us.
            "--file-access-retries", "10",
            "--retry-sleep", "file_access:exp=1:20",
            "--retry-sleep", "fragment:exp=1:30",
            "--retry-sleep", "http:exp=1:20",
        ]
        # A refused key or segment request comes back as the wrong number of
        # bytes, which surfaces as a decryption error rather than an HTTP one.
        # After such a failure, ask for one fragment at a time and space the
        # requests out instead of hammering the same host again.
        if job.gentle:
            args += ["--concurrent-fragments", "1", "--sleep-requests", "1"]
        else:
            args += ["--concurrent-fragments", "4"]

        if os.name == "nt":
            args.append("--windows-filenames")
        if self.ffmpeg:
            args += ["--ffmpeg-location", self.ffmpeg]

        outdir = normalize_outdir(o.get("outdir") or ".")
        # Fragments and .part files go to a private local directory, and only
        # the finished file is moved to the destination. That keeps parallel
        # jobs from sharing scratch filenames, and keeps a long download off a
        # network share until it is complete.
        args += ["-P", "home:" + outdir, "-P", "temp:" + job_work_dir(job.id)]
        # Never quietly replace a file that is already there; a manual retry
        # is the way to ask for that.
        args.append("--force-overwrites" if job.force else "--no-overwrites")

        template = o.get("template") or "%(title)s [%(id)s].%(ext)s"
        if job.name:
            template = name_template(job.name, numbered=bool(
                o.get("playlists") and looks_like_playlist(job.url)))
        elif o.get("playlist_folders") and o.get("playlists") and looks_like_playlist(job.url):
            template = "%(playlist_title|Playlist)s/%(playlist_index|0)03d - " + template
        args += ["-o", template]

        quality = o.get("quality", "Best available")
        if quality == "Audio only":
            args += ["-f", "bestaudio/best", "-x",
                     "--audio-format", o.get("audio_format", "mp3"),
                     "--audio-quality", "0"]
        else:
            container = o.get("container", "Auto")
            height = HEIGHTS.get(quality)
            if height and container == "mp4":
                fmt = ("bv*[ext=mp4][height<=?{h}]+ba[ext=m4a]/"
                       "bv*[height<=?{h}]+ba/b[height<=?{h}]").format(h=height)
            elif height:
                fmt = "bv*[height<=?{h}]+ba/b[height<=?{h}]".format(h=height)
            elif container == "mp4":
                fmt = "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
            else:
                fmt = "bv*+ba/b"
            args += ["-f", fmt]
            if container != "Auto":
                args += ["--merge-output-format", container]

        if o.get("subtitles"):
            args += ["--write-subs", "--write-auto-subs",
                     "--sub-langs", o.get("sub_langs") or "en.*,en", "--embed-subs"]
        if o.get("thumbnail"):
            args.append("--embed-thumbnail")
        if o.get("metadata"):
            args += ["--embed-metadata", "--embed-chapters"]
        if o.get("sponsorblock"):
            args += ["--sponsorblock-remove", "sponsor,selfpromo,interaction"]
        args.append("--yes-playlist" if o.get("playlists") else "--no-playlist")
        if o.get("archive"):
            args += ["--download-archive", os.path.join(outdir, ".evd-archive.txt")]
        rate = (o.get("rate_limit") or "").strip()
        if rate:
            args += ["-r", rate]
        # A cookies file beats reading the browser: recent Chrome encrypts its
        # cookie store so nothing else can open it, and a membership site then
        # just redirects to the login page.
        cookie_file = (o.get("cookies_file") or "").strip()
        cookies = o.get("cookies", "None")
        if cookie_file and os.path.isfile(cookie_file):
            args += ["--cookies", cookie_file]
        elif cookies and cookies != "None":
            args += ["--cookies-from-browser", cookies]

        # Sites behind Cloudflare refuse a plain request with a 403. This only
        # applies to pages handled by the generic extractor, so it changes
        # nothing for a direct media link.
        args += ["--extractor-args", "generic:impersonate"]

        args.append(job.url)
        return args


# ------------------------------------------------------------------ naming --
_ILLEGAL = '<>:"|?*'
_MEDIA_EXT = ("mp4", "mkv", "webm", "mov", "avi", "m4v", "flv",
              "mp3", "m4a", "opus", "flac", "wav", "aac", "ogg")


def sanitize_name(name: str) -> str:
    """Reduce a typed name to one safe filename component."""
    name = " ".join(name.split())                  # collapse whitespace
    name = name.replace("/", "-").replace("\\", "-")   # keep it one component
    name = "".join(ch for ch in name if ch not in _ILLEGAL and ord(ch) >= 32)
    name = name.strip(" .")
    return name[:150]


def name_template(name: str, numbered: bool = False) -> str:
    """Build a yt-dlp output template from a user-supplied name.

    A name containing yt-dlp fields is passed through, so "%(title)s (2026)"
    works as well as a literal name.  `numbered` appends the playlist index so
    a multi-video link cannot collapse onto one filename.
    """
    safe = sanitize_name(name)
    if not safe:
        return "%(title)s [%(id)s].%(ext)s"
    if "%(ext)s" in safe:
        return safe
    head, _, tail = safe.rpartition(".")
    if head and tail.lower() in _MEDIA_EXT:
        safe = head                                # do not end up with .mp4.mp4
    if numbered:
        return safe + " - %(playlist_index|0)03d.%(ext)s"
    return safe + ".%(ext)s"


# ------------------------------------------------------------------- utils --
_URL_RE = re.compile(r"https?://[^\s\"'<>|\\]+", re.I)


def parse_entries(text: str) -> list[tuple[str, str]]:
    """Read pasted text into (url, name) pairs, in order, without duplicates.

    A line may name its download by following the link with a pipe:

        https://example.com/watch?v=x | Lecture 1 - Intro

    Lines without a pipe may hold several links; `#` lines are ignored.
    """
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            match = _URL_RE.search(line)
            if not match:
                continue
            url = match.group(0).rstrip(".,);]")
            rest = line[match.end():]
            name = rest.split("|", 1)[1].strip() if "|" in rest else ""
            pairs = [(url, name)]
        else:
            pairs = [(m.rstrip(".,);]"), "") for m in _URL_RE.findall(line)]
        for pair in pairs:
            if pair not in seen:
                seen.add(pair)
                found.append(pair)
    return found


def extract_urls(text: str) -> list[str]:
    """Just the URLs from pasted text."""
    return [url for url, _ in parse_entries(text)]