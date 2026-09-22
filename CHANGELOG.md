# Changelog

Notable changes, newest first. Versions follow [semantic versioning](https://semver.org):
given `MAJOR.MINOR.PATCH`, the major number changes when something you rely on
works differently, the minor when a feature is added, the patch when a fault is
fixed. The version lives in `evd/__init__.py`.

Anything before 1.0.0 predates this repository, so it is recorded from memory
rather than from history.

## 1.1.0 - 2026-09-22

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

  Now two at a time above sixty lessons, started a beat apart, in smaller
  frames, polled three times a second so a slot is handed back the moment a
  page is ready. Anything that still times out gets a second pass at the end
  with the browser to itself and twice the patience.

  A lesson that comes back empty now says why - the page never finished
  loading, or it loaded and has no player on it - and only the first kind is
  retried. Any player is taken, not only Vimeo: a library built over years
  collects the odd YouTube or Wistia embed, and yt-dlp handles those too.

### Changed

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
