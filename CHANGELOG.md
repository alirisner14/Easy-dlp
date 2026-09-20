# Changelog

Notable changes, newest first. Versions follow [semantic versioning](https://semver.org):
given `MAJOR.MINOR.PATCH`, the major number changes when something you rely on
works differently, the minor when a feature is added, the patch when a fault is
fixed. The version lives in `evd/__init__.py`.

Anything before 1.0.0 predates this repository, so it is recorded from memory
rather than from history.

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
