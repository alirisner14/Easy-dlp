"""Joining finished videos into one file, two ways.

Ticked rows are joined exactly as chosen, in queue order - for a batch that
mixes several courses, where only the person downloading knows which pieces
belong together. With nothing ticked, one click joins each folder's videos
into a file of its own, which with a folder per course is one per course.

What must hold: the order is the course's order, nothing that is not a
finished video is fed in, the joined file is as long as its pieces with the
sound in step, every piece becomes a chapter, the originals are untouched,
and stopping half way leaves nothing behind.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import combine as C, downloader as D

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


ROOT = tempfile.mkdtemp(prefix="evd-combine-")
COURSE = os.path.join(ROOT, "Watercolour Basics")
OTHER = os.path.join(ROOT, "Ink Course")
os.makedirs(COURSE)
os.makedirs(OTHER)
FFMPEG = D.find_ffmpeg()


def make(path, seconds, size="640x360", rate=44100, audio=True):
    args = [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=%s:rate=30" % size]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=%d" % rate]
    args += ["-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    args += (["-c:a", "aac", "-ac", "2"] if audio else [])
    subprocess.run(args + [path], check=True, creationflags=C.CREATE_NO_WINDOW)


def streams(path):
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True,
                         text=True, creationflags=C.CREATE_NO_WINDOW).stderr
    titles = re.findall(r"title\s*:\s*(.+)", out.split("Chapters:")[1]) if "Chapters:" in out else []
    return out, [t.strip() for t in titles]


def run(groups, stop_after=None):
    joiner = C.Joiner(FFMPEG)
    joiner.start(groups)
    started = time.time()
    while joiner.running and time.time() - started < 120:
        if stop_after and time.time() - started > stop_after:
            joiner.stop_and_wait()
        time.sleep(0.1)
    return joiner


print("1. planning: order, grouping, what is left out", flush=True)
names = ["1.10_FinalThoughts.mp4", "1.02_Brushes.mp4", "1.01_Intro.mp4", "2.01_Washes.mp4"]
paths = [os.path.join(COURSE, n) for n in names]
for p in paths:
    open(p, "wb").close()
sheet = os.path.join(COURSE, "1.02_Brushes_Worksheet.pdf")
open(sheet, "wb").close()
other = [os.path.join(OTHER, n) for n in ("1.01_Ink.mp4", "1.02_Pens.mp4")]
for p in other:
    open(p, "wb").close()
lone = os.path.join(ROOT, "Single", "1.01_Only.mp4")
os.makedirs(os.path.dirname(lone))
open(lone, "wb").close()

groups = C.plan_by_folder(paths + [sheet] + other + [lone, os.path.join(COURSE, "gone.mp4")])
by_name = {os.path.basename(os.path.dirname(g.output)): g for g in groups}
ok(len(groups) == 2, "one file per folder with something to join (%d)" % len(groups))
ok([os.path.basename(f) for f in by_name["Watercolour Basics"].files]
   == ["1.01_Intro.mp4", "1.02_Brushes.mp4", "1.10_FinalThoughts.mp4", "2.01_Washes.mp4"],
   "in course order - 1.02 before 1.10, whatever order they finished in")
ok(sheet not in by_name["Watercolour Basics"].files, "a worksheet is not fed in as video")
ok("Single" not in by_name, "a folder with one video has nothing to join")
ok(os.path.basename(by_name["Watercolour Basics"].output) == "Watercolour Basics - Complete.mp4",
   "the whole course is named for its folder")

ticked = C.plan_ticked([paths[1], paths[2], sheet])
ok(len(ticked) == 1 and ticked[0].files == [paths[1], paths[2]],
   "ticked rows keep the order they were chosen in, and drop the worksheet")
ok(os.path.basename(ticked[0].output) == "Watercolour Basics (1.02-1.01).mp4",
   "a hand-picked run is named for its range, so two picks never collide")
ok(C.plan_ticked([paths[0]]) == [], "one video is not a join")

open(os.path.join(COURSE, "Watercolour Basics - Complete.mp4"), "wb").close()
again = C.plan_by_folder(paths)
ok(os.path.basename(again[0].output) == "Watercolour Basics - Complete (2).mp4",
   "an earlier join is never overwritten")
ok(C._chapter_title("1.03_SwitchingYourBrushLibrary.mp4") == "1.03 Switching Your Brush Library",
   "chapter titles are readable")
shutil.rmtree(ROOT)

if not FFMPEG:
    print("     no ffmpeg - skipping the real joins", flush=True)
else:
    os.makedirs(COURSE)
    print("2. matching lessons: a lossless copy", flush=True)
    a, b, c = (os.path.join(COURSE, n) for n in ("1.01_Intro.mp4", "1.02_Brushes.mp4",
                                                  "1.03_Washes.mp4"))
    make(a, 3), make(b, 4), make(c, 2)
    before = {p: os.path.getsize(p) for p in (a, b, c)}
    groups = C.plan_ticked([a, b, c])
    j = run(groups)
    ok(len(j.done) == 1, "joined (%s)" % (j.failed or "ok"))
    ok(groups[0].copy, "and it was a copy, not a re-encode")
    out, titles = streams(j.done[0])
    m = re.search(r"Duration: 00:00:(\d+\.\d+)", out)
    ok(m and abs(float(m.group(1)) - 9) < 0.2, "as long as its pieces (%s s)" % (m and m.group(1)))
    ok(titles == ["1.01 Intro", "1.02 Brushes", "1.03 Washes"], "one chapter per lesson %s" % titles)
    ok({p: os.path.getsize(p) for p in (a, b, c)} == before, "the originals are untouched")

    print("3. pieces that differ: brought to match, sound kept in step", flush=True)
    odd = os.path.join(COURSE, "2.01_Odd One's Out.mp4")
    mute = os.path.join(COURSE, "2.02_Silent.mp4")
    make(odd, 2, size="1280x720", rate=48000)
    make(mute, 2, audio=False)
    groups = C.plan_ticked([a, b, c, odd, mute])
    j = run(groups)
    ok(len(j.done) == 1, "joined (%s)" % (j.failed or "ok"))
    ok(not groups[0].copy, "re-encoded, since a copy would have been broken")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=codec_type,duration,width,height", "-of", "csv=p=0",
                            j.done[0]], capture_output=True, text=True).stdout.split()
    video = [s for s in probe if s.startswith("video")]
    audio = [s for s in probe if s.startswith("audio")]
    ok(video and video[0].startswith("video,640,360"), "sized to the first lesson (%s)" % video)
    vd = float(video[0].split(",")[-1]) if video else 0
    ad = float(audio[0].split(",")[-1]) if audio else 0
    ok(abs(vd - 13) < 0.2 and abs(ad - 13) < 0.2,
       "picture and sound both run 13 s - the odd audio rate did not drift (%.2f / %.2f)" % (vd, ad))
    _out, titles = streams(j.done[0])
    ok(len(titles) == 5 and titles[3] == "2.01 Odd One's Out",
       "an apostrophe in a name survives, and the silent lesson is a chapter too")

    print("4. stopping half way leaves nothing behind", flush=True)
    long_a, long_b = (os.path.join(COURSE, n) for n in ("3.01_Long.mp4", "3.02_Long.mp4"))
    make(long_a, 60, size="1280x720", rate=48000)
    make(long_b, 60)
    groups = C.plan_ticked([long_a, long_b])
    j = run(groups, stop_after=1.0)
    leftovers = [f for f in os.listdir(COURSE) if f.startswith(".joining-")]
    ok(not j.done, "nothing was claimed as finished")
    ok(not leftovers, "no partial file or scratch folder left (%s)" % leftovers)
    ok(not os.path.exists(groups[0].output), "and no half-made output under the real name")
    shutil.rmtree(ROOT)

print("5. audio joins the same way, never mixed with video", flush=True)
os.makedirs(COURSE, exist_ok=True)
mixed = [os.path.join(COURSE, n) for n in
         ("1.01_Intro.mp4", "1.01_Intro.mp3", "1.02_Talk.mp4", "1.02_Talk.mp3", "notes.pdf")]
for p in mixed:
    open(p, "wb").close()
groups = C.plan_ticked(mixed)
kinds = sorted(g.kind for g in groups)
ok(kinds == ["audio", "video"],
   "ticking video and audio together makes one file of each, not a muddle (%s)" % kinds)
audio = [g for g in groups if g.kind == "audio"][0]
ok(audio.output.endswith("(1.01-1.02).mp3") and all(f.endswith(".mp3") for f in audio.files),
   "the audio join holds only the tracks, as an MP3")
by_folder = C.plan_by_folder(mixed)
ok(sorted(os.path.basename(g.output) for g in by_folder)
   == ["Watercolour Basics - Complete.mp3", "Watercolour Basics - Complete.mp4"],
   "one click gives a folder holding both one video and one audio file")
ok(C.kind_of("x.m4a") == "audio" and C.kind_of("x.pdf") == "" and C.kind_of("x.mkv") == "video",
   "worksheets are neither, so they never go in")
shutil.rmtree(ROOT)

if FFMPEG:
    os.makedirs(COURSE)
    cover = os.path.join(ROOT, "cover.jpg")
    subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=red:size=64x64",
                    "-frames:v", "1", cover], check=True, creationflags=C.CREATE_NO_WINDOW)

    def track(path, seconds, rate=44100, codec=None, art=False):
        raw = path + ".raw" + os.path.splitext(path)[1]
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=%d" % rate, "-t", str(seconds), "-ac", "2"]
                       + (["-c:a", codec] if codec else []) + [raw],
                       check=True, creationflags=C.CREATE_NO_WINDOW)
        if art:
            subprocess.run([FFMPEG, "-v", "error", "-i", raw, "-i", cover, "-map", "0", "-map", "1",
                            "-c", "copy", "-disposition:v", "attached_pic", path],
                           check=True, creationflags=C.CREATE_NO_WINDOW)
            os.remove(raw)
        else:
            os.replace(raw, path)

    def length(path):
        m = re.search(r"Duration: 00:(\d+):(\d+\.\d+)", streams(path)[0])
        return int(m.group(1)) * 60 + float(m.group(2)) if m else 0.0

    print("6. real audio joins", flush=True)
    mp3s = [os.path.join(COURSE, "1.0%d_Talk.mp3" % n) for n in (1, 2, 3)]
    for p, secs in zip(mp3s, (3, 4, 2)):
        track(p, secs, art=True)                 # MP3s with cover art, as downloaded
    groups = C.plan_ticked(mp3s)
    j = run(groups)
    ok(len(j.done) == 1 and groups[0].copy,
       "matching MP3s are copied, not re-encoded (%s)" % (j.failed or "ok"))
    _out, titles = streams(j.done[0])
    ok(abs(length(j.done[0]) - 9) < 0.2,
       "as long as its tracks - cover art did not confuse it (%.2f s)" % length(j.done[0]))
    ok(titles == ["1.01 Talk", "1.02 Talk", "1.03 Talk"], "one chapter per track %s" % titles)

    others = [os.path.join(COURSE, n) for n in ("2.01_A.mp3", "2.02_B.m4a", "2.03_C.mp3")]
    track(others[0], 3), track(others[1], 4, rate=48000, codec="aac"), track(others[2], 2, rate=22050)
    groups = C.plan_ticked(others)
    j = run(groups)
    ok(len(j.done) == 1 and not groups[0].copy and j.done[0].endswith(".mp3"),
       "mixed formats and rates are re-encoded to the first one's format")
    ok(abs(length(j.done[0]) - 9) < 0.2, "and keep their full length (%.2f s)" % length(j.done[0]))

    flacs = [os.path.join(COURSE, "3.0%d_Lossless.flac" % n) for n in (1, 2, 3)]
    for p, secs in zip(flacs, (3, 4, 2)):
        track(p, secs)
    groups = C.plan_ticked(flacs)
    j = run(groups)
    ok(len(j.done) == 1 and abs(length(j.done[0]) - 9) < 0.2,
       "FLAC keeps its full length - a copy would have claimed only the first "
       "track's (%.2f s)" % (length(j.done[0]) if j.done else 0))
    ok(not [f for f in os.listdir(COURSE) if f.startswith(".joining-")], "nothing left behind")
    shutil.rmtree(ROOT)

print("7. the toolbar has room for it", flush=True)
from evd import ui as U
app = U.App()
app.root.attributes("-alpha", 0.0)
for width in (1280, 1000):
    app.root.geometry("%dx800+40+40" % width)
    app.root.update()
    app.rebuild()
    app.root.update()
    comb, clear = app.b_combine, app.b_clear
    count_right = app.cv.bbox(app.count_item)[2] if app.cv.bbox(app.count_item) else 0
    ok(comb.x + comb.w <= clear.x, "%d px: Combine sits clear of Clear done" % width)
    ok(comb.x >= count_right + 8,
       "%d px: and clear of the item count (%d >= %d)" % (width, comb.x, count_right + 8))
app.root.geometry("1280x800+40+40"); app.root.update(); app.rebuild(); app.root.update()
ok(app.b_combine.text == "Combine", "labelled Combine on a full-width window")
ok("each folder" in app.b_combine.tooltip, "with nothing ticked it offers the one-click join")
app.engine.add("https://example.com/a.m3u8", {"outdir": "."}, name="x")
app.queue.select_all(True)
app.root.update()
ok("ticked" in app.b_combine.tooltip, "with rows ticked it offers to join those instead")

print("8. a repeated link is queued once, and an empty Combine says why", flush=True)
for jid in list(app.engine.order):
    app.engine.remove(jid)
app.engine.start = lambda: None
same = "https://player.vimeo.com/video/786347455"
app.stage_data = [["01_Jan82023", same], ["02_Jan102023", same], ["03_Jan122023", same],
                  ["Clip", same + " 1:30-2:00"], ["Other", "https://player.vimeo.com/video/957512030"]]
app.stage_rows = []
app.start_download()
urls = [(j.url, j.section) for j in app.engine.all_jobs()]
ok(len(urls) == 3, "three distinct downloads from five rows (%d)" % len(urls))
ok(urls.count((same, "")) == 1, "the repeated link once")
ok((same, "90-120") in urls, "but a clip of it is a different download, and kept")

shown = []
U.messagebox.showinfo = lambda title, text, **kw: shown.append((title, text))
for j in app.engine.all_jobs():
    j.status = D.DONE                    # finished, but no file on disk
app.queue.select_all(False)
app.combine_videos()
ok(shown and shown[0][0] == "Nothing to combine",
   "pressing Combine with nothing joinable opens a box, not a vanishing footer line")
ok(shown and "no file of their own" in shown[0][1],
   "and names the usual cause - rows marked done with no file")
app.root.destroy()

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
