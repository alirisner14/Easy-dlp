# Working on Easy-dlp

## Running it from source

```
pip install -r requirements.txt
python app.py
```

yt-dlp must be on `PATH`. `ffmpeg` is optional but needed for merging formats,
embedding thumbnails and converting audio.

## Building the double-clickable version

```
python build_exe.py
```

PyInstaller produces `dist/Easy-dlp.exe`, about 18 MB. The exe is
not kept in the repository because it is rebuilt from source in a minute.

**The app must be closed before building**, or PyInstaller cannot replace the
running file.

## The tests

Each one prints `ALL PASS` or the failures, and exits non-zero if anything
failed. Run them from the project root.

| script | what it holds to account |
|---|---|
| `parallel_test.py` | the parallel limit, including rows paused mid-launch |
| `resume_test.py` | a restart keeps part-finished downloads |
| `pagescan_test.py` | a course page yields every lesson, named and numbered |

The tests that build a real window read and write the same `settings.json` and
`queue.json` as the installed app. **Point `APPDATA` at a scratch folder before
running those**, or a real queue will be overwritten:

```
set APPDATA=C:\Temp\evd-sandbox
python resume_test.py
```

`parallel_test.py` and `resume_test.py` replace `subprocess.Popen`, so they
never download anything.

## Where the app keeps things

| what | where |
|---|---|
| settings | `%APPDATA%\EasyVideoDownloader\settings.json` |
| the queue | `%APPDATA%\EasyVideoDownloader\queue.json` |
| activity log | `%APPDATA%\EasyVideoDownloader\activity.log` (rolls at 2 MB) |
| batch lists | `%APPDATA%\EasyVideoDownloader\batches\` |
| crash report | `%APPDATA%\EasyVideoDownloader\crash.log` |
| part-downloaded video | `%TEMP%\EasyVideoDownloader\work\<job id>\` |

The scratch folder is named after the job id, and the queue records that id -
that pairing is what lets a restart carry on instead of downloading each video
again. Breaking it silently wastes gigabytes, so `resume_test.py` guards it.

## The pieces

| module | what it does |
|---|---|
| `app.py` | entry point; installs the crash handler and opens the window |
| `evd/ui.py` | the window: staging table, options, toolbar, the 120 ms tick |
| `evd/queueview.py` | the queue rows, pooled and redrawn only when dirty |
| `evd/downloader.py` | the engine: job queue, scheduler, yt-dlp process handling |
| `evd/pagescan.py` | turns a copied course page into staged rows |
| `evd/widgets.py` | buttons, fields, selects and tooltips drawn on a canvas |
| `evd/graphics.py` | the frosted glass compositing, via Pillow |
| `evd/theme.py` | colours, fonts, spacing |
| `evd/config.py` | settings, queue and batch files on disk |
| `evd/errors.py` | writes `crash.log` instead of vanishing |

There is no Tk theming here: every control is drawn onto a canvas, because Tk
widgets cannot sit under a blurred backdrop. `README.md` explains how that
works.

## Two things that will bite you

**The interface runs on one thread.** Anything touching the download folder -
`os.makedirs`, `os.path.exists`, a directory listing - blocks the window while
it waits. On a network share that can be minutes. Keep filesystem work off the
tick.

**Launching a download is not instant.** Preparation can block for seconds
before the process exists. Pausing during that window used to free the job's
slot while it went on to launch anyway; the decision and the launch are now
made under one lock in `Engine._run`. Keep them together.

## Helper scripts

Written to investigate a specific mess and kept because the next one will look
similar. They read the download folder from `settings.json`, or take a path as
their first argument.

| script | what it is for |
|---|---|
| `repair_queue.py` | reunite a saved queue with fragments already on disk |
| `check_done.py` | confirm jobs marked Done really have a finished file |
| `check_dupes.py` | find lessons already downloaded under another name |

`repair_queue.py` only writes when passed `--apply`; the others only read.

## Cloudflare Stream, and why it needs a different approach

`pagescan.py` exists because Bunny puts a playable video id on every lesson
thumbnail. Cloudflare Stream does not work that way:

| | Bunny | Cloudflare Stream |
|---|---|---|
| video id alone | works, unauthenticated | refused, HTTP 401 |
| what authorises playback | nothing | a signed token, ~6 hours |
| where the address lives | in the page, on every thumbnail | nowhere - minted per playback |

So scraping ids off the page gets you ids that will not play. The links have
to be caught as each lesson starts, which is what
`tools/cloudflare-stream-links.js` does - it walks the lesson list and reads
the addresses back out of the browser's own resource timing log.

Verified against a live six-lesson course: 6 of 6 captured, named and
numbered. It depends on the player actually running, because a browser will
not start playback until the person has interacted with the page.

yt-dlp handles the resulting links natively through its CloudflareStream
extractor, at 1080p.

**One thing that does not work**, in case it looks tempting: the same video is
also offered as a single mp4 at `.../downloads/default.mp4`, which would avoid
hundreds of fragment writes. yt-dlp cannot fetch it - it matches the
cloudflarestream.com domain and runs its own extractor even when handed the
mp4 address, and forcing the generic extractor makes it follow the redirect,
match the domain again, and fail with 401. Fetching that file would mean
downloading it ourselves rather than through yt-dlp.
