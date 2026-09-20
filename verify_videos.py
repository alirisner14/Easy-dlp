"""Is every downloaded video actually playable, or just present?

A download cut off mid-write leaves a file of a plausible size that stops
early or will not open at all. Size alone cannot tell you; asking ffprobe
can, because it has to read the file's index to answer.

    python verify_videos.py [download folder]
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evd import paths

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
outdir = paths.download_dir()
print("checking %s\n" % outdir, flush=True)

names = sorted(n for n in os.listdir(outdir)
               if n.lower().endswith((".mp4", ".mkv", ".webm", ".m4a", ".mp3")))
print("%d media files\n" % len(names), flush=True)

bad, short, ok = [], [], 0
for name in names:
    path = os.path.join(outdir, name)
    size_mb = os.path.getsize(path) / 1024 / 1024
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size", "-of", "json", path],
            capture_output=True, text=True, timeout=180,
            creationflags=CREATE_NO_WINDOW)
        info = json.loads(out.stdout or "{}").get("format", {})
        seconds = float(info.get("duration") or 0)
        problem = (out.stderr or "").strip().splitlines()
    except Exception as exc:
        print("  %-52s %7.0f MB  UNREADABLE (%s)" % (name[:52], size_mb,
                                                     exc.__class__.__name__), flush=True)
        bad.append(name)
        continue

    if not seconds:
        print("  %-52s %7.0f MB  BROKEN - no duration" % (name[:52], size_mb), flush=True)
        bad.append(name)
    elif problem:
        print("  %-52s %7.0f MB  %5.1f min  WARNINGS: %s"
              % (name[:52], size_mb, seconds / 60, problem[0][:40]), flush=True)
        short.append(name)
    else:
        # Size against length says nothing: a flat illustration compresses far
        # smaller than a busy one, and guessing from bitrate cries wolf. What
        # does settle it is decoding the last few seconds - a file that was cut
        # off cannot play its own ending.
        try:
            tail = subprocess.run(
                ["ffmpeg", "-v", "error", "-sseof", "-8", "-i", path, "-f", "null", "-"],
                capture_output=True, text=True, timeout=300,
                creationflags=CREATE_NO_WINDOW)
            complaint = (tail.stderr or "").strip().splitlines()
        except Exception as exc:
            complaint = ["could not check: %s" % exc.__class__.__name__]
        if complaint:
            print("  %-52s %7.0f MB  %5.1f min  CUT SHORT: %s"
                  % (name[:52], size_mb, seconds / 60, complaint[0][:38]), flush=True)
            short.append(name)
        else:
            print("  %-52s %7.0f MB  %5.1f min  plays to the end"
                  % (name[:52], size_mb, seconds / 60), flush=True)
            ok += 1

print("\n%d play to the end, %d cut short, %d broken"
      % (ok, len(short), len(bad)), flush=True)
for group, label in ((bad, "BROKEN"), (short, "CUT SHORT")):
    for name in group:
        print("  %s  %s" % (label, name), flush=True)
