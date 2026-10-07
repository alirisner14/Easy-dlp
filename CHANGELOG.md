# Changelog

Notable changes, newest first. Versions follow [semantic versioning](https://semver.org):
given `MAJOR.MINOR.PATCH`, the major number changes when something you rely on
works differently, the minor when a feature is added, the patch when a fault is
fixed. The version lives in `evd/__init__.py`.

Anything before 1.0.0 predates this repository, so it is recorded from memory
rather than from history.

Each released version is tagged `vMAJOR.MINOR.PATCH`. `version_test.py`
checks that the number in `evd/__init__.py`, the newest heading here, and the
newest tag all agree, because three places that can disagree eventually
will.

## 1.4.0 - 2026-10-07

### Added

- **Identify** (beside Paste in the staging area). Paste a video link or a
  page's source and it says how to get the videos: paste the link, paste the
  page, or run a collector snippet in DevTools. When a snippet is needed it can
  be copied straight from the window, so the tools folder is never needed. A
  playlist link with Playlists turned off is flagged, since only one video
  would download.
- The collector snippets are bundled inside the app.

### Fixed

- Freya courses failed with "403 Forbidden". The site now signs each video
  address, and a page signs only the lesson open on it. A pasted page now uses
  the signed address and says how many lessons were locked;
  `tools/BunnyCollectionScript.js` collects the signed address for every lesson.
- Lessons on the redesigned Freya pages were named after their running time
  ("1.04_141253") instead of their title.

## 1.3.1 - 2026-10-06

### Fixed

- **The Vimeo collector fetched one video many times over.** On a tutorial
  post, every comment timestamp ("Jan 8, 2023") is a link back to the same
  post with a #comment on the end, and each was taken for a separate lesson:
  a real run queued one video seventeen times under seventeen dates. Links
  are now compared without their #fragment or ?query, links back to the page
  itself are ignored, and run on a single post the collector takes that
  post's own video rather than every post its sidebar links to. As a last
  guard, two lessons that resolve to the same video are reported rather than
  both listed.
- **The app queues a repeated link once.** The repeat used to be skipped as
  "already there", record no file, and leave the queue looking finished.
- **Combine explained nothing when there was nothing to join.** A footer line
  that vanished in three seconds made the button look dead. It now opens a
  box saying why - and names the usual cause, finished rows with no file of
  their own.
- **The Cloudflare collector, run on a Vimeo site, says so** - at once,
  instead of after a 30-second wait for a lesson list that is never coming.

## 1.3.0 - 2026-10-04

### Added

- **Combine joins audio too.** Tracks downloaded as Audio only join the same
  two ways as video - ticked, or one file per folder - into one MP3, M4A,
  Opus, FLAC, Ogg or WAV, with a chapter per track where the format can hold
  one (MP3, M4A and Opus can; FLAC, Ogg and WAV cannot, and join without).
  Video and audio never go into the same file: ticking both makes one of
  each, and a folder holding both gets one of each.

  Matching tracks are copied, so the join is instant. MP3s carrying cover art
  are compared on their sound alone, since the art shows up as a one-frame
  video stream and would otherwise make identical tracks look different.
  FLAC is always re-encoded, losslessly: its header states its own length,
  and a stream copy kept the first track's, so a nine-minute join claimed
  three. Opus is resampled to 48 kHz when re-encoded, the only rates it
  supports. Joined MP3s are written with ID3v2.3, which Windows Explorer and
  most car stereos read where they ignore ffmpeg's default 2.4.

## 1.2.0 - 2026-10-04

### Added

- **The collector scripts can be paused and stopped.** A run over a big
  library takes many minutes, and started on the wrong page - or once it is
  plainly missing everything - the only way out was to wait for it to try
  every link. Both scripts now show a small bar while they work, with a
  running count of found and missed, a Pause and a Stop. Stop answers within
  a fraction of a second, cuts off pages still loading rather than waiting
  for them to time out, and opens the links panel with everything found so
  far. The Vimeo collector's panel then offers to carry on with the lessons
  not reached, at normal speed, rather than starting over. The same controls
  work as console commands - evdPause(), evdResume(), evdStop() - and
  starting a second run on top of one already going is refused.

- **Combine finished videos into one file, two ways.** Tick rows and Combine
  joins exactly those, in queue order - for batches that mix courses, where
  only the person downloading knows what belongs together. Tick nothing and
  it joins each folder's videos into one file per folder, which with a folder
  per course is one click per course. Every original becomes a chapter, so the
  joined file can still be navigated lesson by lesson, and the originals are
  kept.

  Matching pieces are joined by stream copy: fast and lossless. Pieces that
  differ go through ffmpeg's concat filter instead of its concat demuxer,
  because the demuxer misplaced the sound by a second when a 48 kHz lesson sat
  among 44.1 kHz ones; the filter normalises each piece on its own and keeps
  every segment in step. A lesson with no sound gets silence of its own
  length, so later lessons do not slide out of sync. Checked against real
  files on both paths: five pieces totalling 13 s came out at 13.00 s of
  picture and 13.00 s of sound, chapter boundaries on the second.

  Stopping, or closing the window, mid-join removes the half-written file.

- **Download part of a video.** Type a range after the link -
  `https://... 1:30-5:00` - and only that stretch is fetched, rather than the
  whole recording followed by a trim in another program. Either end may be
  left off, hours work, and a pasted list can carry a range as a third
  column. The file is named for the part it holds, so a clip never collides
  with the full video, and the range survives a restart.

  A range that makes no sense - backwards, or not a time - holds the row back
  in the list with a note, rather than being ignored. Ignoring it would mean
  silently downloading the whole two-hour video, which is the one outcome the
  feature exists to prevent.

### Changed

- **Handouts are read from the part of a page meant for them.** Extension
  alone decided it before, which missed files a page offered without naming
  them and could not tell a reference sheet from a photograph. A page that
  keeps its downloads in a named section - or under a heading that says
  Downloads, Resources, Materials - now has that section read as a whole, so
  an image inside it comes along and the same kind of image outside it does
  not. `.brushset`, `.procreate`, `.brush`, `.rar` and `.7z` are taken
  anywhere on the page, as `.pdf` and `.zip` already were.

  A heading has no container to measure, so the section it announces is
  bounded three ways: the next heading, the close of the block it sits in, or
  a few thousand characters. Without that last bound a "Downloads" heading
  near the foot of a page claimed the footer with it.

## 1.1.0 - 2026-10-03

### Added

- **Course handouts are collected with the videos.** A course is rarely only
  its videos: worksheets, brush sets, project files and reference sheets come
  with it, and gathering those by hand was the same tedium the page scanner
  was written to end. A pasted page now stages them after the lessons, and the
  two collector scripts pick them up as they walk a course - there a handout
  keeps the number of the lesson it belongs to, so it sorts beside the video.

  The rule is deliberately narrow. A link ending `.pdf` or `.zip` is a handout
  by any reading; a link ending `.png` is as likely to be the site's logo or
  somebody's avatar, so an image is only taken when the page says outright it
  is meant to be saved. The **Resources** switch turns the whole thing off.

  A handout skips the video machinery - no format picking, no container merge,
  no tag embedding, all of which would either do nothing to a PDF or corrupt
  it - and is fetched under the name it was staged with, extension and all.

- **The Vimeo collector handles the other ways a site lays a course out.**
  Besides a course numbered into sections, it now reads a library of tutorial
  posts and a single tutorial page with the video on it.

### Fixed

- **The Vimeo collector lost lessons on a big library.** On a page of a
  hundred tutorials or more it reported a screenful of MISSED, and could lock
  the tab up outright. Each hidden frame is a whole copy of the site's app
  running in the same renderer as the page you are watching, so three at a
  time is fine for a course and far too many for a library: the ones that
  came back empty were simply the ones that loaded while the browser was
  busiest.

  A run of 125 came back with 79 collected and 46 missed, and the shape of it
  named the cause: the first 35 all fine, the last 30 all fine, and the middle
  60 lost bar a success every fifth or sixth. That is a site throttling a
  client asking for a hundred pages back to back, not a hundred broken pages.

  So the run asks less often rather than waiting longer: two at a time above
  sixty lessons, started a beat apart, a pause between one page and the next,
  in smaller frames, polled three times a second so a slot is handed back the
  moment a page is ready. Anything that still does not answer gets a second
  pass at the end, slower, and the panel then offers a button to try whatever
  is left one at a time - recovering a few stragglers without fetching the
  whole library again.

  A lesson that comes back empty now says why - the page never finished
  loading, or it loaded and has no player on it - and only the first kind is
  retried. Any player is taken, not only Vimeo: a library built over years
  collects the odd YouTube or Wistia embed, and yt-dlp handles those too.

- **Pasting a web page could stage hundreds of junk rows.** A page the lesson
  reader does not recognise fell through to the plain link parser, which takes
  every http address in the markup - stylesheets, scripts, fonts, trackers -
  and stages a row for each. Each row is two text boxes and a button drawn on
  the canvas, so a few hundred of them lock the window up long enough to look
  like a crash, and none of them are videos.

  Markup is now searched for video addresses only: manifests, plain video
  files, and the player pages of Vimeo, YouTube, Wistia and Cloudflare Stream.
  A page with none of those says so rather than staging its furniture. Past
  150 rows from any source, the app asks before drawing them.

- **A packaged build can carry yt-dlp and ffmpeg inside it.** It looked for
  them on `PATH` only, so a packaged app on a machine that had never installed
  either - which is every machine but a developer's - opened its window and
  failed every download with "yt-dlp was not found on PATH". Drop the two
  executables in `vendor/` and the build bundles them; what ships wins over
  what is installed, so a stale copy on `PATH` cannot change how an install
  behaves. A build from source still uses `PATH`, which is what you want while
  developing. `RELEASING.md` covers the rest, including which ffmpeg licence
  to take.

### Changed

- **The licence is now proprietary.** Versions published before 2026-10-03
  were MIT, and that grant still covers those copies - it cannot be
  withdrawn. Everything from this release on is licensed, not sold, under
  `legal/shared/EULA.md`. The bundled open-source tools keep their own
  licences, which this does not touch and which still have to be shipped
  with the application; see `legal/shared/THIRD-PARTY-LICENCES.md`.

- **Start Download moved to the foot of the options.** It used to sit above
  them, which put the folder the files land in past the button - easy to press
  Start before remembering to point it somewhere new. Everything that decides
  where a download goes is now read on the way down to it. **Add** joined
  Paste, Import and Clear on the row above.

  The options card's height was a number kept in step with its contents by
  hand, and was already 16px short of what it drew. It is now worked out from
  the same walk down the card, and `layout_test.py` builds the real window and
  checks the two agree.

## 1.0.0 - 2026-09-19

First version kept under version control.

### Fixed

- **The parallel limit could be ignored entirely.** Pausing a row while its
  download was still being prepared marked it Paused and freed its slot, while
  the worker thread carried on and launched anyway. The download then ran
  untracked, its freed slot started another, and the limit stopped meaning
  anything - nine downloads ran at once with the limit set to three, saturating
  the connection and the network share. Deciding and launching now happen under
  one lock. Cancel had the same hole. Covered by `parallel_test.py`.
- **A restart threw away part-finished downloads.** Restored jobs were given
  fresh ids, and the scratch folder is named after the job id, so every restart
  silently orphaned gigabytes of fragments and started each video again. The id
  is now saved with the queue. Covered by `resume_test.py`.

### Added

- **Stage a whole course from its page.** Copy a course page's source and paste
  it in: every lesson is staged at once, named `Section.Lesson_Title`, taken
  from the video id in each lesson's own thumbnail. Saves opening DevTools once
  per video. See `evd/pagescan.py`.
- **Shift-click a row's x** to drop every row in the same numbered section,
  for courses whose opening section is the same introduction each time.
- **Import** now accepts saved web pages as well as `.txt` link lists.
- Scripts for checking and repairing state: `repair_queue.py` reunites a saved
  queue with fragments already on disk, `check_done.py` confirms finished jobs
  really have a finished file, `check_dupes.py` looks for lessons already
  downloaded under another name.

### Earlier, before this repository

- Queue saved to `queue.json` and restored on start, so closing or losing the
  app no longer costs the list. Nothing restarts by itself.
- Every batch sent to the queue written out as a `.txt` beside the downloads
  and into a history folder, so a list of links can always be recovered.
- Fragments staged in a private local folder per job rather than on the
  destination share, after a batch of eighteen failed with decryption errors
  caused by fragment writes over a flaky SMB link.
- Automatic retry for transient failures, a gentler second attempt, per-row
  and toolbar pause and stop, a filename box per row, and the staging table
  that replaced pasting links into a text file.
