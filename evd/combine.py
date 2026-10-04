"""Join finished videos into one file.

A course arrives as forty lessons; some people want forty files, some want
one long video they can scrub through, and many want a file per section. This
joins whatever it is given, in order, with a chapter marker at the start of
each original, so the joined file can still be navigated lesson by lesson in
any player that shows chapters.

Lessons from one course are nearly always encoded identically, and then the
join is a straight copy: fast, and not one pixel changes. When the pieces do
not match - different sizes or formats - copying would produce a broken file,
so they are re-encoded to match the first, which is slow and says so up
front. The originals are never touched.
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
from dataclasses import dataclass, field

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".ts")

_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO = re.compile(r"Stream #\S+.*?Video:\s*(\w+).*?(\d{2,5})x(\d{2,5})")
_FPS = re.compile(r"Video:.*?(\d+(?:\.\d+)?) fps")
_AUDIO = re.compile(r"Stream #\S+.*?Audio:\s*(\w+).*?(\d{4,6}) Hz,\s*([\w.() ]+?)[,\n]")
_NUMBERED = re.compile(r"^(\d{1,3}(?:\.\d{1,3})?)[_ .-]")
_NATURAL = re.compile(r"(\d+)")


@dataclass
class Info:
    path: str
    duration: float = 0.0
    vcodec: str = ""
    width: int = 0
    height: int = 0
    acodec: str = ""
    rate: str = ""
    layout: str = ""
    fps: str = ""

    @property
    def shape(self) -> tuple:
        """What has to match for the pieces to be joined without re-encoding."""
        return (self.vcodec, self.width, self.height, self.acodec, self.rate, self.layout)


@dataclass
class Group:
    """One output file and the videos that go into it, in order."""
    files: list[str]
    output: str
    infos: list[Info] = field(default_factory=list)

    @property
    def copy(self) -> bool:
        """True when every piece matches, so the join is a lossless copy."""
        return bool(self.infos) and len({i.shape for i in self.infos}) == 1

    @property
    def duration(self) -> float:
        return sum(i.duration for i in self.infos)


# ------------------------------------------------------------------- probe --
_MAJOR: dict[str, int] = {}


def ffmpeg_major(ffmpeg: str) -> int:
    """ffmpeg's major version, read once per executable."""
    if ffmpeg not in _MAJOR:
        try:
            out = subprocess.run([ffmpeg, "-hide_banner", "-version"], capture_output=True,
                                 text=True, timeout=20, creationflags=CREATE_NO_WINDOW).stdout
            m = re.search(r"version\s+n?(\d+)\.", out)
            _MAJOR[ffmpeg] = int(m.group(1)) if m else 7
        except Exception:
            _MAJOR[ffmpeg] = 7
    return _MAJOR[ffmpeg]


def probe(ffmpeg: str, path: str) -> Info:
    """Read length, size and formats from ffmpeg's own description of a file.

    ffmpeg, not ffprobe: only ffmpeg ships with the app, and "ffmpeg -i" prints
    everything needed here before it complains that no output was given.
    """
    info = Info(path=path)
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-i", path],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=60,
                             creationflags=CREATE_NO_WINDOW).stderr
    except Exception:
        return info
    m = _DURATION.search(out)
    if m:
        info.duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = _VIDEO.search(out)
    if m:
        info.vcodec, info.width, info.height = m.group(1), int(m.group(2)), int(m.group(3))
    m = _FPS.search(out)
    if m:
        info.fps = m.group(1)
    m = _AUDIO.search(out)
    if m:
        info.acodec, info.rate, info.layout = m.group(1), m.group(2), m.group(3).strip()
    return info


# -------------------------------------------------------------------- plan --
def natural_key(path: str):
    """"1.02" before "1.10", and "2.01" after both - the order a course runs in."""
    name = os.path.basename(path).lower()
    return [int(part) if part.isdigit() else part for part in _NATURAL.split(name)]


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXT


def _free(path: str) -> str:
    """The path, or "name (2).ext" and so on if something is already there."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s (%d)%s" % (stem, n, ext)):
        n += 1
    return "%s (%d)%s" % (stem, n, ext)


def output_for(files: list[str], whole_folder: bool) -> str:
    """Where the joined file goes, and what it is called.

    Beside the first piece. A whole folder becomes "<Folder> - Complete"; a
    hand-picked run of numbered lessons is named for its range,
    "<Folder> (1.03-1.15)", so two different picks from one course do not
    collide; anything else is "<Folder> - Joined".
    """
    folder = os.path.dirname(files[0])
    title = os.path.basename(folder.rstrip("\\/")) or "Joined"
    exts = {os.path.splitext(f)[1].lower() for f in files}
    ext = exts.pop() if len(exts) == 1 else ".mkv"
    if ext not in (".mp4", ".mkv", ".webm", ".mov"):
        ext = ".mkv"            # a container that will hold whatever was copied in
    if whole_folder:
        name = "%s - Complete" % title
    else:
        first = _NUMBERED.match(os.path.basename(files[0]))
        last = _NUMBERED.match(os.path.basename(files[-1]))
        name = ("%s (%s-%s)" % (title, first.group(1), last.group(1))
                if first and last else "%s - Joined" % title)
    return _free(os.path.join(folder, name + ext))


def plan_ticked(paths: list[str]) -> list[Group]:
    """Exactly the ticked videos, in the order they sit in the queue."""
    files = [p for p in paths if is_video(p) and os.path.isfile(p)]
    if len(files) < 2:
        return []
    return [Group(files=files, output=output_for(files, whole_folder=False))]


def plan_by_folder(paths: list[str]) -> list[Group]:
    """One file per folder - which, set up one folder per course, is one per course.

    Ordered by name, since the numbered names sort into course order. A folder
    with a single video has nothing to join and is left out.
    """
    by_folder: dict[str, list[str]] = {}
    for p in paths:
        if is_video(p) and os.path.isfile(p):
            by_folder.setdefault(os.path.dirname(p), []).append(p)
    groups = []
    for folder in sorted(by_folder):
        files = sorted(set(by_folder[folder]), key=natural_key)
        if len(files) >= 2:
            groups.append(Group(files=files, output=output_for(files, whole_folder=True)))
    return groups


# -------------------------------------------------------------------- join --
def _chapter_title(path: str) -> str:
    """"1.03_SwitchingYourBrushLibrary" as "1.03 Switching Your Brush Library"."""
    stem = os.path.splitext(os.path.basename(path))[0]
    number = _NUMBERED.match(stem)
    rest = stem[number.end():] if number else stem
    rest = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", rest).replace("_", " ").strip()
    return ("%s %s" % (number.group(1), rest)).strip() if number else rest


def _write_lists(group: Group, work: str) -> tuple[str, str]:
    """The concat list, and a metadata file carrying one chapter per piece."""
    listing = os.path.join(work, "files.txt")
    with open(listing, "w", encoding="utf-8") as fh:
        for path in group.files:
            # the concat format quotes with ' and escapes a ' as '\''
            fh.write("file '%s'\n" % path.replace("\\", "/").replace("'", "'\\''"))
    meta = os.path.join(work, "chapters.txt")
    with open(meta, "w", encoding="utf-8") as fh:
        fh.write(";FFMETADATA1\n")
        start = 0
        for info in group.infos:
            end = start + max(1, int(round(info.duration * 1000)))
            title = _chapter_title(info.path)
            for ch in ("\\", "=", ";", "#"):
                title = title.replace(ch, "\\" + ch)
            fh.write("[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n"
                     % (start, end, title))
            start = end
    return listing, meta


def command(ffmpeg: str, group: Group, listing: str, meta: str, out: str,
            work: str = "") -> list[str]:
    """The ffmpeg command for one join.

    Matching pieces go through the concat demuxer with a stream copy: fast,
    and not one pixel changes. Pieces that differ go through the concat
    filter instead, which decodes each one on its own and brings it to a
    common size, frame rate and sample rate before joining. The demuxer
    cannot do that safely - with mixed audio rates it misplaced the sound by
    a second in testing - while the filter keeps every segment in step.
    """
    head = [ffmpeg, "-hide_banner", "-nostats", "-y"]
    tail = (["-movflags", "+faststart"] if out.lower().endswith((".mp4", ".mov")) else [])
    tail += ["-progress", "pipe:1", out]

    if group.copy:
        return head + ["-f", "concat", "-safe", "0", "-i", listing,
                       "-i", meta, "-map_metadata", "1", "-map_chapters", "1",
                       "-map", "0:v:0?", "-map", "0:a:0?", "-c", "copy"] + tail

    first = group.infos[0]
    w = max(2, first.width - first.width % 2)
    h = max(2, first.height - first.height % 2)
    fps = first.fps or "30"
    rate = first.rate or "48000"

    inputs: list[str] = []
    for info in group.infos:
        inputs += ["-i", info.path]
    # a piece with no sound gets silence of its own length, so the join does
    # not slide every later lesson's audio out of step
    silent: dict[int, int] = {}
    for n, info in enumerate(group.infos):
        if not info.acodec:
            silent[n] = len(group.infos) + len(silent)
            inputs += ["-f", "lavfi", "-t", "%.3f" % max(0.1, info.duration),
                       "-i", "anullsrc=r=%s:cl=stereo" % rate]
    meta_index = len(group.infos) + len(silent)
    inputs += ["-i", meta]

    parts, pairs = [], []
    for n in range(len(group.infos)):
        # letterboxed rather than stretched, so one odd lesson does not
        # distort the rest
        parts.append("[%d:v:0]scale=%d:%d:force_original_aspect_ratio=decrease,"
                     "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=%s,format=yuv420p[v%d]"
                     % (n, w, h, w, h, fps, n))
        source = "%d:a:0" % silent.get(n, n)
        parts.append("[%s]aresample=%s,aformat=channel_layouts=stereo[a%d]"
                     % (source, rate, n))
        pairs.append("[v%d][a%d]" % (n, n))
    parts.append("%sconcat=n=%d:v=1:a=1[v][a]" % ("".join(pairs), len(group.infos)))
    graph = ";\n".join(parts)

    # a course of forty lessons makes a long filter, so it goes in a file
    # rather than onto a command line Windows would truncate
    script = os.path.join(work or os.path.dirname(meta), "filter.txt")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(graph)

    # ffmpeg 7 replaced -filter_complex_script with "-/filter_complex <file>",
    # and 9 removed the old spelling; the bundled build could be either
    load = (["-/filter_complex", script] if ffmpeg_major(ffmpeg) >= 7
            else ["-filter_complex_script", script])
    return head + inputs + load + [
        "-map", "[v]", "-map", "[a]",
        "-map_metadata", str(meta_index), "-map_chapters", str(meta_index),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k"] + tail


class Joiner:
    """Runs joins one after another on a thread, reporting as it goes.

    The window reads `status` on its own timer rather than being called from
    this thread, because Tk must only ever be touched from the thread that
    owns it.
    """

    def __init__(self, ffmpeg: str, on_log=None):
        self.ffmpeg = ffmpeg
        self.on_log = on_log or (lambda line: None)
        self.status = ""
        self.done: list[str] = []
        self.failed: list[str] = []
        self.running = False
        self._proc: subprocess.Popen | None = None
        self._stop = False

    def start(self, groups: list[Group]):
        self.running, self._stop = True, False
        self.done, self.failed = [], []
        self._thread = threading.Thread(target=self._run, args=(groups,), daemon=True)
        self._thread.start()

    def stop_and_wait(self, seconds: float = 8.0):
        """Stop, and give the half-written file a chance to be removed.

        Used when the window closes: the join runs on a background thread
        that dies with the app, and without a moment to tidy up it would
        leave a partial ".joining-" file in the course folder.
        """
        self.stop()
        thread = getattr(self, "_thread", None)
        if thread and thread.is_alive():
            thread.join(seconds)

    def stop(self):
        self._stop = True
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass

    def _run(self, groups: list[Group]):
        try:
            for n, group in enumerate(groups, 1):
                if self._stop:
                    break
                self._join(group, n, len(groups))
        finally:
            self.running = False
            self._proc = None

    def _join(self, group: Group, n: int, of: int):
        name = os.path.basename(group.output)
        prefix = ("%d of %d: " % (n, of)) if of > 1 else ""
        self.status = "%sreading %d videos" % (prefix, len(group.files))
        if not group.infos:
            group.infos = [probe(self.ffmpeg, f) for f in group.files]
        total = group.duration or 1.0
        folder = os.path.dirname(group.output)
        partial = os.path.join(folder, ".joining-" + name)
        work = os.path.join(folder, ".joining-" + os.path.splitext(name)[0] + "-lists")
        os.makedirs(work, exist_ok=True)
        try:
            listing, meta = _write_lists(group, work)
            args = command(self.ffmpeg, group, listing, meta, partial, work)
            self.on_log("join: %s <- %d videos (%s)" % (
                name, len(group.files), "copy" if group.copy else "re-encode"))
            self._proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
            err_tail: list[str] = []
            threading.Thread(target=lambda: err_tail.extend(
                self._proc.stderr.read().splitlines()[-8:]), daemon=True).start()
            for line in self._proc.stdout:
                if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1_000_000
                    except ValueError:
                        continue
                    self.status = "%sjoining %s - %d%%" % (
                        prefix, name, min(99, int(100 * seconds / total)))
            rc = self._proc.wait()
            if self._stop:
                raise RuntimeError("stopped")
            if rc != 0 or not os.path.isfile(partial):
                raise RuntimeError("ffmpeg exited with %s: %s" % (rc, " | ".join(err_tail)[-300:]))
            os.replace(partial, group.output)
            self.done.append(group.output)
            self.status = "%sjoined %s" % (prefix, name)
            self.on_log("joined: %s" % group.output)
        except Exception as exc:
            self.failed.append(name)
            self.status = "%scould not join %s" % (prefix, name)
            self.on_log("join failed: %s - %s" % (name, exc))
            try:
                os.remove(partial)
            except OSError:
                pass
        finally:
            for leftover in ("files.txt", "chapters.txt", "filter.txt"):
                try:
                    os.remove(os.path.join(work, leftover))
                except OSError:
                    pass
            try:
                os.rmdir(work)
            except OSError:
                pass
