"""Scrolling download queue.

Rows live on a nested canvas (which clips them), are pooled and recycled as the
list scrolls, and are repainted only when the job they show changes.

Each row keeps its controls hidden until the pointer is over it: a tick box
replaces the type badge on the left, and the actions for that job's state
appear on the right.
"""
from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageTk

from . import downloader as D
from . import graphics as G
from . import theme as T
from . import widgets as WG

CARD_PAD = 8
GUTTER = 12          # space reserved on the right for the scrollbar
BTN = 26             # row action button size
BTN_GAP = 6

STATUS_TONE = {
    D.QUEUED: (T.IDLE_HEX, "accent"),
    D.RUNNING: (T.ACCENT_B_HEX, "accent"),
    D.POST: (T.WARN_HEX, "warn"),
    D.PAUSED: (T.WARN_HEX, "warn"),
    D.HELD: (T.IDLE_HEX, "accent"),
    D.DONE: (T.OK_HEX, "ok"),
    D.ERROR: (T.ERR_HEX, "err"),
    D.CANCELED: (T.TEXT_MUTE, "err"),
}

# Which actions a row offers, listed right to left.
# Renaming is offered only where no partly-downloaded file is tied to the old
# name: a paused job's .part would be orphaned, and a finished file already
# exists on disk.
CONTROLS = {
    D.RUNNING: ("trash", "stop", "pause"),
    D.POST: ("trash", "stop"),        # no pause mid-merge; that would redo work
    D.QUEUED: ("trash", "stop", "pause", "rename"),
    D.PAUSED: ("trash", "stop", "resume"),
    D.HELD: ("trash", "stop", "resume", "rename"),
    D.DONE: ("trash", "retry", "folder"),
    D.ERROR: ("trash", "retry", "rename"),
    D.CANCELED: ("trash", "retry", "rename"),
}


def _saving_as(job: D.Job) -> str:
    """Name the output file when it is not already the row's visible title."""
    if job.name and job.title:
        return " · saving as " + job.name
    return ""


def _plan(job: D.Job) -> str:
    """Short description of what a pending job will fetch."""
    quality = job.opts.get("quality", "")
    if quality == "Audio only":
        return "Audio only · " + str(job.opts.get("audio_format", "mp3"))
    container = job.opts.get("container", "Auto")
    bits = [quality] if quality else []
    if container and container != "Auto":
        bits.append(container)
    return " · ".join(bits)


class Row:
    """One pooled queue entry."""

    def __init__(self, view: "QueueView", width: int):
        self.view = view
        self.cv = view.cv
        self.w = width
        self.job_id: str | None = None
        self._job: D.Job | None = None
        self._sig = None
        self._ctl_sig = None
        self.y = 0
        self.hovered = False
        self._build()

    @property
    def card_w(self) -> int:
        return self.w - GUTTER - CARD_PAD * 2

    # -- construction --------------------------------------------------
    def _build(self):
        cv = self.cv
        self.tag = "row%d" % id(self)
        cw, ch = self.card_w, T.ROW_H - 10

        self.card_img = ImageTk.PhotoImage(
            G.rrect((cw, ch), 14, fill=T.CARD, outline=(255, 255, 255, 26)))
        self.card_hover_img = ImageTk.PhotoImage(
            G.rrect((cw, ch), 14, fill=T.CARD_HOVER, outline=(255, 255, 255, 46)))
        self.card_item = cv.create_image(CARD_PAD, 0, image=self.card_img,
                                         anchor="nw", tags=self.tag)

        self.badge_imgs = {}
        for tone, color in (("accent", T.ACCENT_A), ("ok", T.OK), ("err", T.ERR),
                            ("warn", T.WARN), ("idle", (126, 138, 168))):
            self.badge_imgs[tone] = G.rrect(
                (40, 40), 12, fill=(color[0], color[1], color[2], 46),
                outline=(color[0], color[1], color[2], 110))
        self.badge_item = cv.create_image(CARD_PAD + 14, 13, anchor="nw", tags=self.tag)
        self._badge_photo = None
        self.glyph_item = cv.create_image(CARD_PAD + 34, 33, anchor="center", tags=self.tag)
        self._glyph_photo = None

        tx = CARD_PAD + 66
        self.title_item = cv.create_text(tx, 18, text="", fill=T.TEXT, anchor="w",
                                         font=T.f("row_title"), tags=self.tag)
        self.meta_item = cv.create_text(tx, 38, text="", fill=T.TEXT_DIM, anchor="w",
                                        font=T.f("small"), tags=self.tag)
        self.bar = WG.Bar(cv, tx, 52, max(60, self.card_w - 66 - 130), 5)
        self.pill = WG.Pill(cv, 0, 10, text=D.QUEUED, color=T.IDLE_HEX)

        # tick box sits exactly where the badge is, so nothing shifts on hover
        self.tick = WG.TickBox(cv, CARD_PAD + 24, 23, 20, command=self._ticked,
                               tooltip="Select")

        self.btns = {
            "pause": WG.IconButton(cv, 0, 0, BTN, "pause", command=self._pause,
                                   tooltip="Pause"),
            "resume": WG.IconButton(cv, 0, 0, BTN, "play", command=self._resume,
                                    tooltip="Resume"),
            "stop": WG.IconButton(cv, 0, 0, BTN, "x", command=self._stop,
                                  tooltip="Stop"),
            "retry": WG.IconButton(cv, 0, 0, BTN, "refresh", command=self._retry,
                                   tooltip="Download again"),
            "folder": WG.IconButton(cv, 0, 0, BTN, "folder", command=self._folder,
                                    tooltip="Show in folder"),
            "trash": WG.IconButton(cv, 0, 0, BTN, "trash", command=self._remove,
                                   tooltip="Remove"),
            "rename": WG.IconButton(cv, 0, 0, BTN, "pencil", command=self._rename,
                                    tooltip="Set output file name"),
        }
        self.hide()

    # -- actions -------------------------------------------------------
    def _ticked(self, value: bool):
        if self.job_id:
            self.view.set_selected(self.job_id, value)

    def _pause(self):
        if self.job_id:
            self.view.engine.pause_job(self.job_id)

    def _resume(self):
        if self.job_id:
            self.view.engine.resume_job(self.job_id)

    def _stop(self):
        if self.job_id:
            self.view.engine.cancel(self.job_id)

    def _retry(self):
        if self.job_id:
            self.view.engine.retry(self.job_id)
            self.view.on_retry()

    def _remove(self):
        if self.job_id:
            self.view.engine.remove(self.job_id)
            self.view.refresh(force=True)

    def _folder(self):
        job = self.view.engine.get(self.job_id) if self.job_id else None
        if job:
            self.view.on_reveal(job)

    def _rename(self):
        job = self.view.engine.get(self.job_id) if self.job_id else None
        if job and self.view.on_rename:
            self.view.on_rename(job)

    # -- visibility ----------------------------------------------------
    def hide(self):
        self.job_id = None
        self._job = None
        self._sig = None
        self._ctl_sig = None
        self.hovered = False
        self.cv.itemconfigure(self.tag, state="hidden")
        self.bar.hide()
        self.pill.hide()
        self.tick.hide()
        for b in self.btns.values():
            b.hide()

    def _place(self, y: int):
        dy = y - self.y
        if not dy:
            return
        self.cv.move(self.tag, 0, dy)
        self.bar.move_by(0, dy)
        self.pill.move_by(0, dy)
        self.tick.move_by(0, dy)
        for b in self.btns.values():
            b.move_by(0, dy)
        self.y = y

    def set_hovered(self, value: bool):
        value = bool(value)
        if value == self.hovered:
            return
        self.hovered = value
        self.cv.itemconfigure(self.card_item,
                              image=self.card_hover_img if value else self.card_img)
        self._apply_controls()

    def show(self, job: D.Job, y: int):
        first = self.job_id != job.id
        self.job_id = job.id
        self._place(y)
        if first:
            self.cv.itemconfigure(self.tag, state="normal")
            self.bar.show()
            self.pill.show()
        self.update(job, force=first)

    # -- painting ------------------------------------------------------
    def update(self, job: D.Job, force=False):
        cv = self.cv
        self._job = job
        tone_color, bar_tone = STATUS_TONE.get(job.status, (T.IDLE_HEX, "accent"))

        sig = (job.status, round(job.pct, 3), job.title, job.stage, job.item,
               job.items, int(job.speed or 0), int(job.eta or -1), job.error[:40])
        if force or sig != self._sig:
            self._sig = sig
            title_max = self.card_w - 66 - 152
            cv.itemconfigure(self.title_item,
                             text=WG.elide(T.f("row_title"), job.label, title_max))
            cv.itemconfigure(self.meta_item,
                             text=WG.elide(T.f("small"), self._meta(job), title_max + 20),
                             fill=T.ERR_HEX if job.status == D.ERROR else T.TEXT_DIM)

            tone = {D.DONE: "ok", D.ERROR: "err", D.CANCELED: "err", D.POST: "warn",
                    D.PAUSED: "warn", D.RUNNING: "accent"}.get(job.status, "idle")
            self._badge_photo = ImageTk.PhotoImage(self.badge_imgs[tone])
            cv.itemconfigure(self.badge_item, image=self._badge_photo)
            rgb = {"ok": T.OK, "err": T.ERR, "warn": T.WARN,
                   "accent": (150, 130, 255), "idle": (126, 138, 168)}[tone]
            glyph = {D.DONE: "check", D.ERROR: "x", D.CANCELED: "x",
                     D.PAUSED: "pause", D.HELD: "pause"}.get(job.status)
            if glyph is None:
                glyph = "music" if job.opts.get("quality") == "Audio only" else "film"
            self._glyph_photo = ImageTk.PhotoImage(
                G.icon(glyph, 18, (rgb[0], rgb[1], rgb[2], 255), width=1.8))
            cv.itemconfigure(self.glyph_item, image=self._glyph_photo)

            label = job.status
            if job.items > 1 and job.status in D.ACTIVE:
                label = "%d/%d" % (max(1, job.item), job.items)
            self.pill.set(label, tone_color)
            self.pill.move(CARD_PAD + self.card_w - 12 - self.pill.w, self.y + 10)
            self.bar.set(job.pct, bar_tone)

        self._apply_controls()

    def _apply_controls(self):
        """Show the tick box and the actions that suit this job's state."""
        job = self._job
        if job is None:
            return
        selected = job.id in self.view.selected
        sig = (self.hovered, selected, job.status, bool(job.filepath))
        if sig == self._ctl_sig:
            return
        self._ctl_sig = sig

        # a selected row keeps its tick box visible so the choice stays readable
        reveal_tick = self.hovered or selected
        self.tick.set(selected)
        self.tick.show() if reveal_tick else self.tick.hide()
        badge_state = "hidden" if reveal_tick else "normal"
        self.cv.itemconfigure(self.badge_item, state=badge_state)
        self.cv.itemconfigure(self.glyph_item, state=badge_state)

        names = CONTROLS.get(job.status, ("trash",)) if self.hovered else ()
        x = CARD_PAD + self.card_w - 12 - BTN
        shown = set()
        for name in names:
            if name == "folder" and not job.filepath:
                continue
            btn = self.btns[name]
            btn.move_to(x, self.y + 30)
            btn.show()
            shown.add(name)
            x -= BTN + BTN_GAP
        for name, btn in self.btns.items():
            if name not in shown:
                btn.hide()

    def _meta(self, job: D.Job) -> str:
        if job.status == D.ERROR:
            return job.error or "Download failed"
        if job.status == D.CANCELED:
            return "Stopped"
        if job.status == D.PAUSED:
            done = D.human_size(job.downloaded) if job.downloaded else ""
            return "Paused at %.1f%%" % (job.pct * 100) + (" · " + done if done else "")
        if job.status == D.HELD:
            return "On hold" + (" · " + _plan(job) if _plan(job) else "") + _saving_as(job)
        if job.status == D.DONE and job.duplicate:
            return "Same file name as another item · only one was kept"
        if job.status == D.DONE and job.skipped:
            return "Skipped \u00b7 a file with that name is already there"
        if job.status == D.DONE:
            bits = []
            if job.files > 1:
                bits.append("%d files" % job.files)
            elif job.filepath:
                bits.append(job.filepath.rsplit("\\", 1)[-1].rsplit("/", 1)[-1])
            if job.total:
                bits.append(D.human_size(job.total))
            if job.started and job.ended:
                bits.append("in %s" % D.human_eta(job.ended - job.started))
            return " · ".join(bits) or "Finished"
        if job.status == D.QUEUED:
            if job.stage.startswith("retry"):
                return job.stage.capitalize() + " after an error"
            return "Waiting" + (" · " + _plan(job) if _plan(job) else "") + _saving_as(job)
        if job.status == D.POST or job.stage:
            return (job.stage or "processing").capitalize() + "…"
        if job.status == D.RUNNING:
            bits = ["%.1f%%" % (job.pct * 100)]
            if job.speed:
                bits.append(D.human_speed(job.speed))
            if job.eta is not None:
                bits.append("ETA " + D.human_eta(job.eta))
            if job.total:
                bits.append("%s / %s" % (D.human_size(job.downloaded), D.human_size(job.total)))
            return " · ".join(bits)
        return job.url

    def resize(self, width: int):
        self.w = width
        self.cv.delete(self.tag)
        self.bar.destroy()
        self.pill.destroy()
        self.tick.destroy()
        for b in self.btns.values():
            b.destroy()
        self.y = 0
        self._build()

    def destroy(self):
        self.cv.delete(self.tag)
        self.bar.destroy()
        self.pill.destroy()
        self.tick.destroy()
        for b in self.btns.values():
            b.destroy()


class QueueView:
    """Nested canvas that renders the job list with its own scrolling."""

    def __init__(self, parent: tk.Canvas, engine: D.Engine, on_reveal, on_retry,
                 on_selection=None, on_rename=None):
        self.parent = parent
        self.engine = engine
        self.on_reveal = on_reveal
        self.on_retry = on_retry
        self.on_selection = on_selection
        self.on_rename = on_rename
        self.selected: set[str] = set()
        self.offset = 0
        self.rows: list[Row] = []
        self.x = self.y = 0
        self.w = self.h = 10
        self._bg_photo = None
        self._sb_photo = None
        self._drag_from = None

        self.cv = tk.Canvas(parent, highlightthickness=0, bd=0, bg="#0c0f18")
        self.win = parent.create_window(0, 0, window=self.cv, anchor="nw",
                                        width=10, height=10)
        self.bg_item = self.cv.create_image(0, 0, anchor="nw")
        self.empty_items: list[int] = []
        self._empty_photo = None

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.cv.bind(seq, self._wheel)
        self.cv.bind("<Button-1>", self._maybe_drag)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_drag_from", None))
        # hover is tracked here, not per item: moving onto a row's own button
        # would otherwise read as leaving the row and hide the buttons again
        self.cv.bind("<Motion>", self._motion)
        self.cv.bind("<Leave>", lambda _e: self._hover_row(None))

    # -- layout --------------------------------------------------------
    def place(self, x, y, w, h, backdrop: Image.Image):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)
        self.parent.coords(self.win, self.x, self.y)
        self.parent.itemconfigure(self.win, width=self.w, height=self.h)
        self.cv.configure(width=self.w, height=self.h)

        crop = backdrop.crop((self.x, self.y, self.x + self.w, self.y + self.h))
        self._bg_photo = ImageTk.PhotoImage(crop)
        self.cv.itemconfigure(self.bg_item, image=self._bg_photo)
        self.cv.configure(bg=G.sample(backdrop, (self.x, self.y,
                                                 self.x + self.w, self.y + self.h)))

        need = self.h // T.ROW_H + 2
        while len(self.rows) < need:
            self.rows.append(Row(self, self.w))
        for row in self.rows:
            if row.w != self.w:
                row.resize(self.w)
        self.refresh(force=True)

    # -- selection -----------------------------------------------------
    def set_selected(self, job_id: str, value: bool):
        if value:
            self.selected.add(job_id)
        else:
            self.selected.discard(job_id)
        self._notify()

    def select_all(self, value: bool):
        self.selected = {j.id for j in self.engine.all_jobs()} if value else set()
        for row in self.rows:
            row._ctl_sig = None
        self.refresh()
        self._notify()

    def selected_jobs(self) -> list[D.Job]:
        return [j for j in self.engine.all_jobs() if j.id in self.selected]

    def _notify(self):
        live = {j.id for j in self.engine.all_jobs()}
        if not self.selected <= live:
            self.selected &= live
        if self.on_selection:
            self.on_selection(self.selected_jobs())

    # -- hover ---------------------------------------------------------
    def _motion(self, event):
        target = None
        for row in self.rows:
            if row.job_id and row.y <= event.y < row.y + T.ROW_H - 6:
                target = row
                break
        self._hover_row(target)

    def _hover_row(self, target: Row | None):
        for row in self.rows:
            row.set_hovered(row is target)

    # -- scrolling -----------------------------------------------------
    def _content_h(self) -> int:
        return len(self.engine.order) * T.ROW_H

    def _max_offset(self) -> int:
        return max(0, self._content_h() - self.h + 6)

    def _wheel(self, event):
        delta = 0
        if getattr(event, "num", None) == 4:
            delta = 1
        elif getattr(event, "num", None) == 5:
            delta = -1
        elif event.delta:
            delta = event.delta / 120.0
        self.scroll_by(int(-delta * T.ROW_H * 0.9))
        return "break"

    def scroll_by(self, dy: int):
        new = max(0, min(self._max_offset(), self.offset + dy))
        if new != self.offset:
            self.offset = new
            self.refresh()

    def _maybe_drag(self, event):
        if event.x >= self.w - GUTTER - 2 and self._max_offset() > 0:
            self._drag_from = (event.y, self.offset)

    def _drag(self, event):
        if not self._drag_from:
            return
        y0, off0 = self._drag_from
        track = self.h - 12
        ratio = self._content_h() / max(1, track)
        self.offset = max(0, min(self._max_offset(), int(off0 + (event.y - y0) * ratio)))
        self.refresh()

    # -- rendering -----------------------------------------------------
    def refresh(self, force=False, dirty: set[str] | None = None):
        jobs = self.engine.all_jobs()
        self.offset = min(self.offset, self._max_offset())

        if self.selected:
            live = {j.id for j in jobs}
            if not self.selected <= live:
                self.selected &= live
                if self.on_selection:
                    self.on_selection(self.selected_jobs())

        if not jobs:
            self._draw_empty()
            for row in self.rows:
                row.hide()
            self._draw_scrollbar()
            return
        self._clear_empty()

        first = max(0, self.offset // T.ROW_H)
        last = min(len(jobs), first + len(self.rows))
        used = 0
        for idx in range(first, last):
            job = jobs[idx]
            row = self.rows[used]
            used += 1
            y = idx * T.ROW_H - self.offset + 4
            if row.job_id == job.id and not force:
                row._place(y)
                if dirty is None or job.id in dirty:
                    row.update(job)
            else:
                row.show(job, y)
        for row in self.rows[used:]:
            row.hide()
        self._draw_scrollbar()

    def _draw_scrollbar(self):
        self.cv.delete("sb")
        max_off = self._max_offset()
        if max_off <= 0:
            self._sb_photo = None
            return
        track = self.h - 12
        th = max(36, int(track * self.h / max(1, self._content_h())))
        ty = 6 + int((track - th) * (self.offset / max_off))
        self._sb_photo = ImageTk.PhotoImage(G.rrect((5, th), 2, fill=(255, 255, 255, 70)))
        self.cv.create_image(self.w - GUTTER + 3, ty, image=self._sb_photo,
                             anchor="nw", tags="sb")

    def _draw_empty(self):
        if self.empty_items:
            return
        cx, cy = self.w / 2, self.h / 2 - 16
        self._empty_photo = ImageTk.PhotoImage(
            G.icon("download", 46, (120, 132, 166, 150), width=1.4))
        self.empty_items = [
            self.cv.create_image(cx, cy - 34, image=self._empty_photo, anchor="center"),
            self.cv.create_text(cx, cy + 14, text="Your queue is empty",
                                fill=T.TEXT_DIM, font=T.f("body_bold"), anchor="center"),
            self.cv.create_text(cx, cy + 36,
                                text="Stage links on the left, then press Start Download",
                                fill=T.TEXT_MUTE, font=T.f("small"), anchor="center"),
        ]

    def _clear_empty(self):
        for i in self.empty_items:
            self.cv.delete(i)
        self.empty_items = []

    def scroll_to_end(self):
        self.offset = self._max_offset()
        self.refresh()
