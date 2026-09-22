"""Main window: paints the glass surface and wires the controls to the engine."""
from __future__ import annotations

import os
import pathlib
import subprocess
import time
import sys
import tkinter as tk
from tkinter import filedialog

from PIL import Image, ImageTk

from . import config
from . import errors
from . import downloader as D
from . import pagescan
from . import graphics as G
from . import theme as T
from . import widgets as WG
from .queueview import QueueView

def _restore_stage(settings) -> list[list[str]]:
    """Read the saved staging list back, tolerating anything odd in the file."""
    rows = []
    for item in settings.get("staged") or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            name, url = item
            if isinstance(name, str) and isinstance(url, str) and (name or url):
                rows.append([name, url])
    return rows or [["", ""]]


HEADER_H = 68
LEFT_BLEED = 10      # room inside the left column for panel shadows


class App:
    def __init__(self):
        self.settings = config.load()

        self.root = tk.Tk()
        self.root.title("Easy-dlp")
        self.root.configure(bg=T.BASE)
        # Pin the point-to-pixel conversion so the pixel layout always agrees
        # with the text it is sized around, whatever the display scaling.
        self.root.tk.call("tk", "scaling", 96.0 / 72.0)
        T.resolve(self.root)

        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w = min(1280, max(1040, sw - 120))
        h = min(800, max(620, sh - 110))
        self.root.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, max(0, (sh - h) // 2 - 20)))
        self.root.minsize(1000, 560)

        self._icon = ImageTk.PhotoImage(G.app_icon(64))
        try:
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass

        self.cv = tk.Canvas(self.root, highlightthickness=0, bd=0, bg=T.BASE)
        self.cv.pack(fill="both", expand=True)

        # The left column lives on its own canvas so it can scroll, and clip,
        # independently of the window.
        self.left_cv = tk.Canvas(self.cv, highlightthickness=0, bd=0, bg=T.BASE)
        self.left_win = self.cv.create_window(0, 0, window=self.left_cv, anchor="nw",
                                              width=10, height=10)
        self.left_bg_item = self.left_cv.create_image(0, 0, anchor="nw")
        self._left_bg_photo = None
        self._left_sb_photo = None
        self.left_widgets: list[WG.W] = []
        self.left_offset = 0
        self.left_content_h = 0
        self.left_view_h = 10
        self.left_origin = (0, 0)
        self.left_width = 10
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.left_cv.bind(seq, self._left_wheel)

        self.engine = D.Engine()
        self.engine.max_parallel = int(self.settings.get("parallel", "2") or 2)
        self.version = D.ytdlp_version(self.engine.exe)

        # bring back whatever was in the queue when we last ran; nothing
        # starts on its own, so a restored queue waits for Start
        saved = config.load_queue()
        restored = self.engine.import_jobs(saved)
        # say so in the log: a queue that comes back empty is alarming, and
        # without this there is no way to tell "nothing was saved" from
        # "the saved queue would not load"
        self.engine._log("opened: %d of %d saved jobs restored"
                         % (restored, len(saved)))
        self._queue_sig = None

        self.queue = QueueView(self.cv, self.engine, self.reveal, self.after_retry,
                                on_selection=self.on_selection_change,
                                on_rename=self.open_name_sheet)

        self.widgets: list[WG.W] = []
        self.backdrop: Image.Image | None = None
        self.composite: Image.Image | None = None
        self.photos: list[ImageTk.PhotoImage] = []
        self.advanced = bool(self.settings.get("advanced_open"))
        # staged rows, each a [file name, url] pair the user is filling in,
        # restored from the last session so a batch in progress is never lost
        self.stage_data: list[list[str]] = _restore_stage(self.settings)
        self.stage_rows: list[dict] = []
        self._focus_row: int | None = None
        self.log_window: LogWindow | None = None
        self.name_sheet: NameSheet | None = None
        self._resize_after = None
        self._last_size = (0, 0)
        self._stat_sig = None
        self._sel_jobs: list[D.Job] = []
        self._layout_failures = 0
        self._layout_ready = False
        self._scroll_to_stage = False
        self._stage_bottom = 0
        self._saved_stage: list[list[str]] | None = None
        self._autosave_ticks = 0
        self._tick_failures = 0

        self.cv.bind("<Configure>", self._on_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        # No global Ctrl+V: the text boxes already paste on their own, and a
        # second global handler would paste the same link twice and spawn a
        # spare staged row. The Paste button is the bulk-fill path.
        self.root.bind("<Escape>", lambda _e: WG.Select.open_instance
                       and WG.Select.open_instance.close())

        self.root.after(60, self._first_paint)
        self._tick_after = self.root.after(120, self.tick)

    # ------------------------------------------------------------ setup --
    def _first_paint(self):
        _dark_titlebar(self.root)
        self.rebuild()

    def _on_configure(self, event):
        if (event.width, event.height) == self._last_size:
            return
        self._last_size = (event.width, event.height)
        if self._resize_after:
            self.root.after_cancel(self._resize_after)
        self._resize_after = self.root.after(140, self.rebuild)

    # ----------------------------------------------------------- layout --
    def rebuild(self):
        """Lay the window out again, surviving a failure rather than blanking."""
        try:
            self._rebuild()
            self._layout_failures = 0
        except Exception:
            path = errors.log(*sys.exc_info(), note="rebuild")
            self._layout_failures += 1
            if self._layout_failures <= 1:
                self.root.after(250, self.rebuild)      # transient? try once more
            else:
                self._draw_layout_error(path)

    def _draw_layout_error(self, path: str):
        """Last resort: say what happened instead of showing an empty window."""
        try:
            w = max(200, self.cv.winfo_width())
            self.cv.create_text(
                w / 2, 120, width=w - 120, justify="center", anchor="n", tags="ui",
                fill=T.TEXT, font=T.f("body_bold"),
                text="The window could not be laid out.")
            self.cv.create_text(
                w / 2, 150, width=w - 120, justify="center", anchor="n", tags="ui",
                fill=T.TEXT_DIM, font=T.f("small"),
                text="Your staged links are safe and will come back. Resize the "
                     "window to try again.\nDetails were written to " + path)
        except Exception:
            pass

    def _rebuild(self):
        self._resize_after = None
        self._layout_ready = False
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        if w < 400 or h < 300:
            return          # transient size while minimising or restoring

        self._capture_stage()

        if WG.Select.open_instance:
            WG.Select.open_instance.close()
        if self.name_sheet:
            self.name_sheet.close()
        for wdg in self.widgets:
            wdg.destroy()
        self.widgets.clear()
        self.left_widgets.clear()
        self.cv.delete("ui")
        self.left_cv.delete("lui")
        self.left_cv.delete("lsb")
        self.photos.clear()

        self.backdrop = G.make_backdrop(w, h)
        self.composite = self.backdrop.copy().convert("RGBA")
        self._backdrop_photo = ImageTk.PhotoImage(self.backdrop)
        self.cv.create_image(0, 0, image=self._backdrop_photo, anchor="nw", tags="ui")

        pad, gap = T.PAD, T.GAP
        left_w = T.LEFT_W if w >= 1220 else max(340, int(w * 0.37))
        right_x = pad + left_w + gap
        right_w = w - right_x - pad

        # left column viewport
        lx, ly = pad - LEFT_BLEED, HEADER_H - 6
        lw, lh = left_w + LEFT_BLEED * 2, h - (HEADER_H - 6) - pad
        self.left_origin = (lx, ly)
        self.left_width = lw
        self.left_view_h = lh
        self.cv.coords(self.left_win, lx, ly)
        self.cv.itemconfigure(self.left_win, width=lw, height=lh)
        self.left_cv.configure(width=lw, height=lh)

        add_h = self._add_card_height()
        options_h = self._options_card_height()
        add_box = (pad, HEADER_H, pad + left_w, HEADER_H + add_h)
        opt_box = (pad, HEADER_H + add_h + gap,
                   pad + left_w, HEADER_H + add_h + gap + options_h)
        queue_box = (right_x, HEADER_H, right_x + right_w, h - pad)

        bg_crop = self.backdrop.crop((lx, ly, lx + lw, ly + lh))
        self._left_bg_photo = ImageTk.PhotoImage(bg_crop)
        self.left_cv.itemconfigure(self.left_bg_item, image=self._left_bg_photo)
        self.left_cv.configure(bg=G.sample(self.backdrop, (lx, ly, lx + lw, ly + lh)))

        # frosted panels are sampled in window space, drawn in their own canvas
        tile, origin = G.frost(self.backdrop, queue_box, radius=T.CARD_R)
        photo = ImageTk.PhotoImage(tile)
        self.photos.append(photo)
        self.cv.create_image(origin[0], origin[1], image=photo, anchor="nw", tags="ui")
        self.composite.alpha_composite(tile, origin)

        for box in (add_box, opt_box):
            tile, origin = G.frost(self.backdrop, box, radius=T.CARD_R,
                                   shadow=LEFT_BLEED)
            photo = ImageTk.PhotoImage(tile)
            self.photos.append(photo)
            self.left_cv.create_image(origin[0] - lx, origin[1] - ly, image=photo,
                                      anchor="nw", tags="lui")
            self.composite.alpha_composite(tile, origin)
        self.composite = self.composite.convert("RGB")

        keep_offset = self.left_offset
        self.left_offset = 0
        self.left_content_h = (opt_box[3] - ly) + 8

        self._draw_header(w)
        self._draw_add_card(add_box)
        self._draw_options_card(opt_box)
        self._draw_queue_card(queue_box)
        if self._scroll_to_stage:
            self._scroll_to_stage = False
            keep_offset = max(0, self._stage_bottom - self.left_view_h + 24)
        if keep_offset:
            self._left_scroll(keep_offset)
        self._draw_left_scrollbar()
        self._sync_quality_state()
        self._layout_ready = True
        self._stat_sig = None
        self.update_stats()

    def _local(self, box):
        """Window-space box -> left canvas coordinates."""
        lx, ly = self.left_origin
        return (box[0] - lx, box[1] - ly, box[2] - lx, box[3] - ly)

    # -- left column scrolling ----------------------------------------
    def _left_max_offset(self) -> int:
        return max(0, self.left_content_h - self.left_view_h)

    def _left_wheel(self, event):
        delta = 0
        if getattr(event, "num", None) == 4:
            delta = 1
        elif getattr(event, "num", None) == 5:
            delta = -1
        elif event.delta:
            delta = event.delta / 120.0
        self._left_scroll(int(-delta * 48))
        return "break"

    def _left_scroll(self, dy: int):
        target = max(0, min(self._left_max_offset(), self.left_offset + dy))
        shift = self.left_offset - target
        if not shift:
            return
        self.left_offset = target
        if WG.Select.open_instance:
            WG.Select.open_instance.close()
        self.left_cv.move("lui", 0, shift)
        for wdg in self.left_widgets:
            wdg.move_by(0, shift)
        self._draw_left_scrollbar()

    def _draw_left_scrollbar(self):
        self.left_cv.delete("lsb")
        max_off = self._left_max_offset()
        if max_off <= 0:
            return
        track = self.left_view_h - 12
        th = max(40, int(track * self.left_view_h / max(1, self.left_content_h)))
        ty = 6 + int((track - th) * (self.left_offset / max_off))
        self._left_sb_photo = ImageTk.PhotoImage(G.rrect((4, th), 2, fill=(255, 255, 255, 52)))
        self.left_cv.create_image(self.left_width - 6, ty, image=self._left_sb_photo,
                                  anchor="nw", tags="lsb")

    # -- header --------------------------------------------------------
    def _draw_header(self, w):
        cv = self.cv
        ph = ImageTk.PhotoImage(G.app_icon(34))
        self.photos.append(ph)
        cv.create_image(T.PAD, 14, image=ph, anchor="nw", tags="ui")
        cv.create_text(T.PAD + 46, 16, text="Easy-dlp", fill=T.TEXT,
                       anchor="nw", font=T.f("title"), tags="ui")
        sub = "yt-dlp %s" % self.version
        sub += "  ·  ffmpeg ready" if self.engine.ffmpeg else "  ·  ffmpeg missing"
        cv.create_text(T.PAD + 48, 44, text=sub, fill=T.TEXT_MUTE, anchor="nw",
                       font=T.f("small"), tags="ui")

        bx = w - T.PAD
        b_log = WG.Button(cv, bx - 96, 20, 96, 32, text="Activity", icon="log",
                          variant="ghost", command=self.toggle_log,
                          tooltip="Show the yt-dlp output")
        b_folder = WG.Button(cv, bx - 224, 20, 120, 32, text="Open folder", icon="folder",
                             variant="ghost", command=self.open_outdir)
        self.widgets += [b_log, b_folder]
        self.speed_item = cv.create_text(bx - 244, 36, text="", fill=T.TEXT_DIM,
                                         anchor="e", font=T.f("body_bold"), tags="ui")

    # -- add card ------------------------------------------------------
    STAGE_ROW_H = 38
    STAGE_TOP = 48            # section caption plus column headings

    def _add_card_height(self) -> int:
        rows = max(1, len(self.stage_data))
        return self.STAGE_TOP + rows * self.STAGE_ROW_H + 2 + 28 + 14

    def _draw_add_card(self, win_box):
        cv = self.left_cv
        x0, y0, x1, y1 = self._local(win_box)
        inner = x1 - x0 - 28
        x = x0 + 14
        cv.create_text(x, y0 + 14, text="STAGE DOWNLOADS", fill=T.TEXT_DIM, anchor="nw",
                       font=T.f("section"), tags="lui")

        del_w, gap = 22, 8
        name_w = max(96, int((inner - del_w - gap - 6) * 0.36))
        url_w = inner - name_w - gap - del_w - 6

        cv.create_text(x, y0 + 34, text="FILE NAME", fill=T.TEXT_DIM, anchor="nw",
                       font=T.f("tiny"), tags="lui")
        cv.create_text(x + name_w + gap, y0 + 34, text="URL", fill=T.TEXT_DIM,
                       anchor="nw", font=T.f("tiny"), tags="lui")

        self.stage_rows = []
        ry = y0 + self.STAGE_TOP
        for i, (nm, url) in enumerate(self.stage_data):
            f_name = WG.Field(cv, x, ry, name_w, 30, value=nm, placeholder="optional",
                              font=T.f("small"),
                              bg=self._well_bg(win_box, ry, name_w, 30))
            f_url = WG.Field(cv, x + name_w + gap, ry, url_w, 30, value=url,
                             placeholder="https://\u2026", font=T.f("small"),
                             bg=self._well_bg(win_box, ry, url_w, 30),
                             on_return=lambda _v: self.add_stage_row())
            b_del = WG.IconButton(cv, x + inner - del_w, ry + 4, del_w, "x",
                                  tooltip="Remove this row "
                                          "(hold Shift to drop its whole section)")
            b_del.command = (lambda i=i, b=b_del:
                             self.remove_stage_row(i, section=b.shift))
            for wdg in (f_name, f_url, b_del):
                self._add_left(wdg)
            self.stage_rows.append({"name": f_name, "url": f_url})
            ry += self.STAGE_ROW_H

        # Start Download is not here but at the foot of the options card, so
        # that the folder the files land in is read past on the way to it.
        by = ry + 2
        bw = (inner - 24) // 4
        for i, (text, icon, tip, cmd) in enumerate([
            ("Add", "plus", "Add another row", self.add_stage_row),
            ("Paste", "clipboard", "Fill rows from the clipboard", self.paste_clipboard),
            ("Import", "folder", "Fill rows from a .txt file of links", self.import_file),
            ("Clear", "x", "Empty the staging list", self.clear_stage),
        ]):
            bx = x + (bw + 8) * i
            w = bw if i < 3 else inner - (bw + 8) * 3
            self._add_left(WG.Button(cv, bx, by, w, 28, text=text, icon=icon,
                                     variant="subtle", font=T.f("small"),
                                     command=cmd, tooltip=tip))

        self._stage_bottom = by + 28
        if self._focus_row is not None and 0 <= self._focus_row < len(self.stage_rows):
            self.stage_rows[self._focus_row]["url"].entry.focus_set()
        self._focus_row = None

    # -- staging ---------------------------------------------------------
    def _capture_stage(self):
        """Read the staged fields back into plain data before any relayout."""
        if not self.stage_rows:
            return
        try:
            self.stage_data = [[r["name"].get(), r["url"].get()] for r in self.stage_rows]
        except tk.TclError:
            pass
        if not self.stage_data:
            self.stage_data = [["", ""]]

    def _save_queue(self, force: bool = False):
        """Write the queue out when it changes, so a restart keeps the list."""
        jobs = self.engine.all_jobs()
        sig = tuple((j.id, j.status, round(j.pct, 2)) for j in jobs)
        if not force and sig == self._queue_sig:
            return
        self._queue_sig = sig
        config.save_queue(self.engine.export_jobs())

    def _save_stage(self):
        """Write the staging list to settings so it survives a close or a crash."""
        rows = [[n, u] for n, u in self.stage_data if n.strip() or u.strip()]
        if rows == self._saved_stage:
            return
        self._saved_stage = [list(r) for r in rows]
        self.settings["staged"] = rows
        config.save(self.settings)

    def add_stage_row(self):
        self._capture_stage()
        self.stage_data.append(["", ""])
        self._focus_row = len(self.stage_data) - 1
        self.stage_rows = []          # stage_data is now the source of truth
        self._scroll_to_stage = True  # keep the new row and the buttons in view
        self._save_stage()
        self.rebuild()

    def remove_stage_row(self, index: int, section: bool = False):
        """Drop one staged row, or the whole numbered section it belongs to.

        A course page brings in every lesson, and the opening section is
        usually the same housekeeping videos each time, so being able to
        drop all of "1.x" in one go saves twenty odd clicks.
        """
        self._capture_stage()
        if 0 <= index < len(self.stage_data):
            mark = pagescan.section_of(self.stage_data[index][0]) if section else ""
            if mark:
                keep = [row for row in self.stage_data
                        if pagescan.section_of(row[0]) != mark]
                gone = len(self.stage_data) - len(keep)
                self.stage_data = keep
                self.flash_footer("Dropped section %s - %d lesson%s"
                                  % (mark, gone, "" if gone == 1 else "s"))
            else:
                del self.stage_data[index]
        if not self.stage_data:
            self.stage_data = [["", ""]]
        self.stage_rows = []
        self._save_stage()
        self.rebuild()

    def clear_stage(self):
        self.stage_data = [["", ""]]
        self.stage_rows = []
        self._save_stage()
        self.rebuild()

    def _fill_stage(self, entries):
        """Drop parsed (url, name) pairs into empty rows, adding rows as needed."""
        self._capture_stage()
        for url, name in entries:
            slot = next((row for row in self.stage_data if not row[1].strip()), None)
            if slot is None:
                slot = ["", ""]
                self.stage_data.append(slot)
            slot[1] = url
            if name and not slot[0].strip():
                slot[0] = name
        self.stage_rows = []
        self._save_stage()
        self.rebuild()

    # -- options card --------------------------------------------------
    SWITCHES = [
        ("Subtitles", "subtitles", "Download and embed subtitles"),
        ("Thumbnail", "thumbnail", "Embed the cover image"),
        ("Metadata", "metadata", "Embed title, artist and chapters"),
        ("SponsorBlock", "sponsorblock", "Cut sponsor segments out"),
        ("Playlists", "playlists", "Follow playlist links instead of a single video"),
        ("Skip existing", "archive", "Keep an archive file and skip repeats"),
        ("Resources", "resources",
         "Stage the handouts a course page offers - worksheets, brush sets, "
         "project files - alongside its videos"),
    ]

    @classmethod
    def _switch_rows(cls) -> int:
        return -(-len(cls.SWITCHES) // 2)          # two to a row, rounded up

    def _options_card_height(self) -> int:
        """Must agree with what _draw_options_card lays out.

        Written as the same walk down the card, so adding a control to one
        without the other cannot quietly clip the panel it is drawn on.
        """
        y = 34 + 16 + 44 + 16 + 44 + 16 + 46       # down to the switch grid
        y += self._switch_rows() * 30 + 6          # ... and past it
        if self.advanced:
            y += 36 + 16 + 42 + 16 + 42 + 16 + 30  # the advanced fields
            y += 14                                # before the button
        else:
            y += 26 + 12                           # the Advanced options button
        return y + 40 + 14                         # Start Download, then padding

    def _draw_options_card(self, win_box):
        cv = self.left_cv
        x0, y0, x1, y1 = self._local(win_box)
        inner = x1 - x0 - 28
        x = x0 + 14
        half = (inner - 10) // 2
        s = self.settings

        cv.create_text(x, y0 + 13, text="DOWNLOAD OPTIONS", fill=T.TEXT_DIM, anchor="nw",
                       font=T.f("section"), tags="lui")

        def label(tx, ty, text):
            cv.create_text(tx, ty, text=text, fill=T.TEXT_DIM, anchor="nw",
                           font=T.f("tiny"), tags="lui")

        y = y0 + 34
        label(x, y, "SAVE TO")
        y += 16
        bw = 84
        self.f_outdir = WG.Field(cv, x, y, inner - bw - 8, 32, value=s["outdir"],
                                 placeholder="Download folder", font=T.f("small"),
                                 bg=self._well_bg(win_box, y, inner - bw - 8, 32),
                                 on_change=lambda v: self.set_opt("outdir", v))
        b_browse = WG.Button(cv, x + inner - bw, y, bw, 32, text="Browse",
                             variant="subtle", font=T.f("small"), command=self.browse)
        self._add_left(self.f_outdir)
        self._add_left(b_browse)

        y += 44
        label(x, y, "QUALITY")
        label(x + half + 10, y, "CONTAINER")
        y += 16
        self.s_quality = WG.Select(cv, x, y, half, 32, D.QUALITY, s["quality"],
                                   command=self.on_quality)
        self.s_container = WG.Select(cv, x + half + 10, y, inner - half - 10, 32,
                                     D.CONTAINERS, s["container"],
                                     command=lambda v: self.set_opt("container", v))
        self._add_left(self.s_quality)
        self._add_left(self.s_container)

        y += 44
        label(x, y, "AUDIO FORMAT")
        label(x + half + 10, y, "PARALLEL DOWNLOADS")
        y += 16
        self.s_audio = WG.Select(cv, x, y, half, 32, D.AUDIO_FORMATS, s["audio_format"],
                                 command=lambda v: self.set_opt("audio_format", v))
        self.s_parallel = WG.Select(cv, x + half + 10, y, inner - half - 10, 32,
                                    D.PARALLEL, str(s["parallel"]), command=self.on_parallel)
        self._add_left(self.s_audio)
        self._add_left(self.s_parallel)

        y += 46
        col_w = (inner - 16) // 2
        for i, (text, key, tip) in enumerate(self.SWITCHES):
            sx = x + (col_w + 16) * (i % 2)
            sw_w = col_w if i % 2 == 0 else inner - col_w - 16
            switch = WG.Switch(cv, sx, y + (i // 2) * 30, sw_w, text,
                               bool(s.get(key, True)), tooltip=tip,
                               command=lambda v, k=key: self.set_opt(k, v))
            self._add_left(switch)

        y += self._switch_rows() * 30 + 6
        self.b_advanced = WG.Button(
            cv, x, y, inner, 26,
            text="Advanced options" + ("  ▴" if self.advanced else "  ▾"),
            variant="subtle", font=T.f("small"), command=self.toggle_advanced)
        self._add_left(self.b_advanced)

        if not self.advanced:
            self._draw_start_button(x, y + 26 + 12, inner)
            return

        y += 36
        label(x, y, "SPEED LIMIT (e.g. 4M)")
        label(x + half + 10, y, "COOKIES FROM BROWSER")
        y += 16
        self.f_rate = WG.Field(cv, x, y, half, 30, value=s["rate_limit"],
                               placeholder="unlimited", font=T.f("small"),
                               bg=self._well_bg(win_box, y, half, 30),
                               on_change=lambda v: self.set_opt("rate_limit", v))
        self.s_cookies = WG.Select(cv, x + half + 10, y, inner - half - 10, 30,
                                   D.COOKIE_SOURCES, s["cookies"], font=T.f("small"),
                                   command=self.on_cookies)
        self._add_left(self.f_rate)
        self._add_left(self.s_cookies)

        y += 42
        label(x, y, "SUBTITLE LANGUAGES")
        y += 16
        self.f_langs = WG.Field(cv, x, y, inner, 30, value=s["sub_langs"],
                                placeholder="en.*,en", font=T.f("small"),
                                bg=self._well_bg(win_box, y, inner, 30),
                                on_change=lambda v: self.set_opt("sub_langs", v))
        self._add_left(self.f_langs)

        y += 42
        label(x, y, "FILENAME TEMPLATE")
        y += 16
        self.f_template = WG.Field(cv, x, y, inner, 30, value=s["template"],
                                   placeholder="%(title)s [%(id)s].%(ext)s",
                                   font=T.f("small"),
                                   bg=self._well_bg(win_box, y, inner, 30),
                                   on_change=lambda v: self.set_opt("template", v))
        self._add_left(self.f_template)

        self._draw_start_button(x, y + 30 + 14, inner)

    def _draw_start_button(self, x: int, y: int, w: int):
        """The last thing in the column, on purpose.

        It used to sit above the options, which put the folder the files land
        in past the button - easy to press Start before remembering to point
        it somewhere new. Now everything that decides where a download goes is
        read on the way down to it.
        """
        self.b_start_dl = WG.Button(self.left_cv, x, y, w, 40,
                                    text="Start Download", icon="download",
                                    variant="primary", command=self.start_download,
                                    tooltip="Queue every staged row and begin")
        self._add_left(self.b_start_dl)

    def _add_left(self, wdg: WG.W):
        self.widgets.append(wdg)
        self.left_widgets.append(wdg)

    def _well_bg(self, win_box, local_y, w, h) -> str:
        """Colour-match an embedded Tk widget to the glass it is sitting on."""
        lx, ly = self.left_origin
        wx = win_box[0] + 14
        wy = ly + local_y
        base = G.sample(self.composite, (wx, wy, wx + w, wy + h))
        return G.mix(base, (0, 0, 0), 0.45)

    # -- queue card ----------------------------------------------------
    def _draw_queue_card(self, box):
        cv = self.cv
        x0, y0, x1, y1 = box
        x = x0 + 16
        right = x1 - 16

        self.tick_all = WG.TickBox(cv, x, y0 + 14, 18, command=self.queue.select_all,
                                   tooltip="Select every item")
        cv.create_text(x + 27, y0 + 16, text="QUEUE", fill=T.TEXT_DIM, anchor="nw",
                       font=T.f("section"), tags="ui")
        self.count_item = cv.create_text(x + 91, y0 + 15, text="", fill=T.TEXT_MUTE,
                                         anchor="nw", font=T.f("small"), tags="ui")

        self.b_start = WG.Button(cv, right - 112, y0 + 10, 112, 32, text="Start",
                                 icon="play", variant="primary", command=self.toggle_run)
        self.b_pause_sel = WG.Button(cv, right - 214, y0 + 10, 94, 32, text="Pause",
                                     icon="pause", variant="ghost", font=T.f("small"),
                                     command=self.pause_selected,
                                     tooltip="Pause the ticked items")
        self.b_stop_sel = WG.Button(cv, right - 314, y0 + 10, 92, 32, text="Stop",
                                    icon="x", variant="danger", font=T.f("small"),
                                    command=self.stop_selected,
                                    tooltip="Stop the ticked items")
        self.b_clear = WG.Button(cv, right - 426, y0 + 10, 104, 32, text="Clear done",
                                 icon="trash", variant="subtle", font=T.f("small"),
                                 command=self.clear_done)
        self.widgets += [self.tick_all, self.b_start, self.b_pause_sel,
                         self.b_stop_sel, self.b_clear]
        self.b_pause_sel.set_enabled(False)
        self.b_stop_sel.set_enabled(False)
        self.on_selection_change(self.queue.selected_jobs())

        list_y = y0 + 54
        self.queue.place(x0 + 6, list_y, (x1 - x0) - 12, max(60, (y1 - 42) - list_y),
                         self.composite)

        self.footer_item = cv.create_text(x, y1 - 26, text="", fill=T.TEXT_MUTE,
                                          anchor="nw", font=T.f("small"), tags="ui")
        self.footer_right = cv.create_text(right, y1 - 26, text="", fill=T.TEXT_MUTE,
                                           anchor="ne", font=T.f("small"), tags="ui")

    # ---------------------------------------------------------- actions --
    def set_opt(self, key, value):
        self.settings[key] = value
        config.save(self.settings)

    def on_quality(self, value):
        self.set_opt("quality", value)
        self._sync_quality_state()

    def _sync_quality_state(self):
        audio = self.settings.get("quality") == "Audio only"
        if getattr(self, "s_audio", None):
            self.s_audio.set_enabled(audio)
        if getattr(self, "s_container", None):
            self.s_container.set_enabled(not audio)

    def on_cookies(self, value):
        """Choose where sign-in cookies come from.

        Recent Chrome encrypts its cookie store so nothing else can read it,
        and a membership site then just redirects to its login page. Exporting
        a cookies.txt with a browser extension sidesteps that, so the file is
        offered alongside the browsers and wins when it is set.
        """
        if value != D.COOKIE_FILE_CHOICE:
            self.set_opt("cookies", value)
            self.set_opt("cookies_file", "")
            return
        path = filedialog.askopenfilename(
            title="Choose an exported cookies.txt",
            filetypes=[("Cookie files", "*.txt"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.settings.get("cookies_file") or "") or None)
        if not path:
            previous = self.settings.get("cookies", "None")
            if previous == D.COOKIE_FILE_CHOICE and not self.settings.get("cookies_file"):
                previous = "None"
            self.s_cookies.set(previous)
            return
        self.set_opt("cookies", D.COOKIE_FILE_CHOICE)
        self.set_opt("cookies_file", path)
        self.flash_footer("Signing in with %s" % os.path.basename(path))

    def on_parallel(self, value):
        self.set_opt("parallel", value)
        self.engine.max_parallel = int(value)

    def toggle_advanced(self):
        self.advanced = not self.advanced
        self.set_opt("advanced_open", self.advanced)
        self.rebuild()

    def snapshot(self) -> dict:
        opts = dict(self.settings)
        opts["outdir"] = self.f_outdir.get().strip() or config.default_download_dir()
        opts["playlist_folders"] = bool(self.settings.get("playlist_folders", True))
        return opts

    def start_download(self):
        """Queue every staged row that has a URL, then start working the queue."""
        self._capture_stage()
        staged = [(name.strip(), url.strip()) for name, url in self.stage_data]
        ready = [(n, u) for n, u in staged if u]
        if not ready:
            self.flash_footer("Put a link in the URL box first")
            return

        opts = self.snapshot()
        queued: list[tuple[str, str]] = []
        added = skipped = 0
        for name, url in ready:
            found = D.parse_entries(url)
            if not found:
                skipped += 1
                continue
            final_name = name or found[0][1]
            self.engine.add(found[0][0], opts, name=final_name)
            queued.append((final_name, found[0][0]))
            added += 1

        if not added:
            self.flash_footer("That does not look like an http(s) link")
            return

        self._save_batch(queued)
        self._save_queue(force=True)
        self.stage_data = [["", ""]]
        self.stage_rows = []
        self._save_stage()
        self.engine.start()
        self.rebuild()
        self.queue.refresh(force=True)
        self.queue.scroll_to_end()
        self.on_selection_change(self.queue.selected_jobs())
        self.update_stats()
        if skipped:
            self.flash_footer("Started %d, skipped %d that were not links"
                              % (added, skipped))

    def _save_batch(self, queued):
        """Keep a copy of the batch, written so it can be pasted back in.

        Each line is "url | file name", which is what Paste and Import already
        understand, so recovering a batch is copy, paste, Start Download.
        """
        if not queued:
            return
        stamp = time.strftime("%Y-%m-%d_%H%M%S")
        targets = [config.batches_dir() / ("%s_%d-items.txt" % (stamp, len(queued)))]
        # and one alongside the downloads themselves, which is where it is
        # actually useful when you want the batch back
        outdir = self.f_outdir.get().strip()
        if outdir:
            try:
                os.makedirs(outdir, exist_ok=True)
                targets.append(pathlib.Path(outdir)
                               / ("_download-list_%s.txt" % time.strftime("%Y-%m-%d_%H%M")))
            except OSError:
                pass
        for path in targets:
            self._write_batch_file(path, queued)
        self._prune_batches()

    def _write_batch_file(self, path, queued):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# Easy-dlp batch - %s\n"
                         % time.strftime("%Y-%m-%d %H:%M:%S"))
                fh.write("# %d item%s, saved to %s\n"
                         % (len(queued), "" if len(queued) == 1 else "s",
                            self.f_outdir.get().strip()))
                fh.write("# Paste these back in, or use Import, to queue them again.\n")
                for name, url in queued:
                    safe = (name or "").replace("|", "-").strip()
                    fh.write("%s | %s\n" % (url, safe) if safe else "%s\n" % url)
        except OSError as exc:
            self.flash_footer("Could not save the list to %s: %s" % (path.parent, exc))

    @staticmethod
    def _prune_batches(keep: int = 100):
        try:
            files = sorted(config.batches_dir().glob("*.txt"))
            for old_file in files[:-keep]:
                old_file.unlink(missing_ok=True)
        except OSError:
            pass

    def open_batches(self):
        _open_path(str(config.batches_dir()))

    def paste_clipboard(self):
        try:
            data = self.root.clipboard_get()
        except tk.TclError:
            self.flash_footer("Clipboard is empty")
            return
        if self._stage_page(data or ""):
            return
        entries = D.parse_entries(data or "")
        if not entries:
            self.flash_footer("No http(s) link on the clipboard")
            return
        self._fill_stage(entries)

    def _stage_page(self, text: str) -> bool:
        """Copy a whole course page in and get the lessons out of it.

        Saves gathering every link by hand from the network tab: the page
        already lists them, named and numbered. Any handouts it attaches -
        worksheets, brush sets, project files - are staged after them, since
        those are part of the course too.
        """
        lessons = pagescan.lessons_from_page(text)
        extras = pagescan.resources_from_page(text) if self.settings.get("resources", True) else []
        if not lessons and not extras:
            return False
        self._fill_stage(lessons + extras)
        marks = pagescan.sections(name for _u, name in lessons)
        note = ""
        if len(marks) > 1:
            # the opening section is usually the same intro videos every
            # time, so say how to get rid of it while it is on screen
            note = (" in %d sections - Shift-click a row's x to drop one"
                    % len(marks))
        if extras:
            note = (" and %d resource%s"
                    % (len(extras), "" if len(extras) == 1 else "s")) + note
        self.flash_footer("Found %d lesson%s on that page%s"
                          % (len(lessons), "" if len(lessons) == 1 else "s", note))
        return True

    def import_file(self):
        path = filedialog.askopenfilename(
            title="Import links",
            filetypes=[("Links and saved pages", "*.txt *.html *.htm"),
                       ("Text files", "*.txt"),
                       ("Saved web pages", "*.html *.htm"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            self.flash_footer("Could not read that file: %s" % exc)
            return
        if self._stage_page(text):
            return
        entries = D.parse_entries(text)
        if not entries:
            self.flash_footer("No links found in that file")
            return
        self._fill_stage(entries)

    def browse(self):
        path = filedialog.askdirectory(title="Choose download folder",
                                       initialdir=self.f_outdir.get() or None)
        if path:
            clean = D.normalize_outdir(path)
            self.f_outdir.set(clean)
            self.set_opt("outdir", clean)

    def on_selection_change(self, jobs):
        """Ticking rows is what arms the Pause and Stop buttons."""
        self._sel_jobs = list(jobs)
        if not self._layout_ready:
            return
        armed = bool(jobs)
        resumable = armed and all(j.status in D.RESUMABLE for j in jobs)
        label, icon = ("Resume", "play") if resumable else ("Pause", "pause")
        if self.b_pause_sel.text != label:
            self.b_pause_sel.set_text(label, icon=icon)
        if self.b_pause_sel.enabled != armed:
            self.b_pause_sel.set_enabled(armed)
        if self.b_stop_sel.enabled != armed:
            self.b_stop_sel.set_enabled(armed)
        total = len(self.engine.order)
        self.tick_all.set(bool(total) and len(self.queue.selected) == total)

    def pause_selected(self):
        jobs = self.queue.selected_jobs()
        if not jobs:
            return
        ids = [j.id for j in jobs]
        if all(j.status in D.RESUMABLE for j in jobs):
            self.engine.resume_jobs(ids)
        else:
            self.engine.pause_jobs(ids)
        self.queue.refresh(force=True)
        self.on_selection_change(self.queue.selected_jobs())
        self.update_stats()

    def stop_selected(self):
        jobs = self.queue.selected_jobs()
        if not jobs:
            return
        self.engine.cancel_jobs([j.id for j in jobs])
        self.queue.refresh(force=True)
        self.on_selection_change(self.queue.selected_jobs())
        self.update_stats()

    def toggle_run(self):
        if self.engine.running and self.engine.counts()["active"]:
            self.engine.pause_all()
        else:
            self.engine.resume_all()
        self.queue.refresh(force=True)
        self.update_stats()

    def clear_done(self):
        self.engine.clear_finished()
        self.queue.refresh(force=True)
        self.update_stats()

    def after_retry(self):
        self.engine.start()
        self.queue.refresh(force=True)

    def open_outdir(self):
        path = self.f_outdir.get().strip() or config.default_download_dir()
        try:
            os.makedirs(path, exist_ok=True)
            _open_path(path)
        except OSError as exc:
            self.flash_footer(str(exc))

    def reveal(self, job: D.Job):
        if job.filepath and os.path.exists(job.filepath):
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(job.filepath)])
                return
            _open_path(os.path.dirname(job.filepath))
            return
        _open_path(job.opts.get("outdir") or config.default_download_dir())

    def open_name_sheet(self, job: D.Job):
        if self.name_sheet:
            self.name_sheet.close()
        self.name_sheet = NameSheet(self, job)

    def apply_name(self, job: D.Job, name: str):
        job.name = D.sanitize_name(name)
        self.engine.touch(job.id)
        self.queue.refresh(force=True)
        if job.name:
            self.flash_footer("Saving that item as %s" % job.name)

    def toggle_log(self):
        if self.log_window and self.log_window.alive():
            self.log_window.close()
            self.log_window = None
        else:
            self.log_window = LogWindow(self.root, self.engine)

    # ------------------------------------------------------------- loop --
    def flash_footer(self, message: str):
        self.cv.itemconfigure(self.footer_item, text=message, fill=T.WARN_HEX)
        self._stat_sig = None
        self.root.after(3200, self.update_stats)

    def update_stats(self):
        if not self._layout_ready:
            return
        counts = self.engine.counts()
        speed = self.engine.total_speed()
        sig = (counts["total"], counts[D.QUEUED], counts["active"], counts[D.DONE],
               counts[D.ERROR], counts[D.CANCELED], counts[D.PAUSED], counts[D.HELD],
               int(speed / 50000), self.engine.running, len(self.queue.selected))
        if sig == self._stat_sig:
            return
        self._stat_sig = sig

        self.cv.itemconfigure(
            self.count_item,
            text="%d item%s" % (counts["total"], "" if counts["total"] == 1 else "s"))

        bits = []
        if counts["active"]:
            bits.append("%d downloading" % counts["active"])
        if counts[D.QUEUED]:
            bits.append("%d waiting" % counts[D.QUEUED])
        if counts[D.DONE]:
            bits.append("%d done" % counts[D.DONE])
        if counts[D.ERROR]:
            bits.append("%d failed" % counts[D.ERROR])
        if counts[D.PAUSED]:
            bits.append("%d paused" % counts[D.PAUSED])
        if counts[D.HELD]:
            bits.append("%d on hold" % counts[D.HELD])
        if counts[D.CANCELED]:
            bits.append("%d stopped" % counts[D.CANCELED])
        self.cv.itemconfigure(self.footer_item,
                              text="  ·  ".join(bits) or "Nothing queued yet",
                              fill=T.TEXT_MUTE)

        state = "Running" if self.engine.running else "Paused"
        if not self.engine.exe:
            state = "yt-dlp not found"
        self.cv.itemconfigure(self.footer_right, text=state)
        self.cv.itemconfigure(self.speed_item, text=D.human_speed(speed) if speed else "")

        # the primary button is the whole-queue control; the toolbar Pause and
        # Stop next to it act only on ticked rows
        if self.engine.running and counts["active"]:
            label, icon = "Pause all", "pause"
        else:
            label, icon = "Start", "play"
        if self.b_start.text != label:
            self.b_start.set_text(label, icon=icon)

        self.on_selection_change(self.queue.selected_jobs())

    def tick(self):
        """The heartbeat: saves, redraws the queue, updates the totals.

        It re-arms itself at the end, so anything that threw in here used to
        stop it for good - no progress, no autosave, and a queue that looked
        empty because it was never redrawn again, all while the window still
        answered. One bad tick must not cost the session, so failures are
        recorded and the timer carries on.
        """
        try:
            if not self.root.winfo_exists():
                return          # the window went away; stop the timer quietly
        except tk.TclError:
            return
        try:
            self._tick_body()
        except Exception:
            self._tick_failures += 1
            if self._tick_failures <= 3:        # enough to diagnose, not a flood
                path = errors.log(*sys.exc_info(), note="tick")
                self.engine._log("a display update failed (%d so far), details in %s"
                                 % (self._tick_failures, path))
        self._tick_after = self.root.after(120, self.tick)

    def _tick_body(self):
        self._autosave_ticks += 1
        if self._autosave_ticks >= 40:          # roughly every five seconds
            self._autosave_ticks = 0
            self._capture_stage()
            self._save_stage()
            self._save_queue()
        dirty = self.engine.take_dirty()
        if dirty:
            self.queue.refresh(dirty=dirty)
        self.update_stats()
        if self.log_window and self.log_window.alive():
            self.log_window.pump()

    def close(self):
        if getattr(self, "_tick_after", None):
            try:
                self.root.after_cancel(self._tick_after)
            except Exception:
                pass
            self._tick_after = None
        # Each of these used to be able to take the rest down with it: a
        # failure in the first left the queue unsaved, which is the one thing
        # here that costs real work to rebuild. They stand alone now, and the
        # queue is written first.
        for what, step in (
            # the queue first and on its own: it is the one thing here that
            # costs real work to rebuild, so nothing else gets to take it down
            ("the queue", lambda: self._save_queue(force=True)),
            ("the staging list", lambda: (self._capture_stage(), self._save_stage())),
            ("settings", self._save_settings),
        ):
            try:
                step()
            except Exception:
                errors.log(*sys.exc_info(), note="closing - saving " + what)
        try:
            self.engine.shutdown()
        except Exception:
            errors.log(*sys.exc_info(), note="closing - stopping downloads")
        self.root.destroy()

    def _save_settings(self):
        self.settings["parallel"] = str(self.engine.max_parallel)
        try:
            self.settings["outdir"] = self.f_outdir.get().strip() or self.settings["outdir"]
        except tk.TclError:
            pass
        config.save(self.settings)

    def run(self):
        self.root.mainloop()


# ------------------------------------------------------------- name sheet --
class NameSheet:
    """Modal sheet for setting one job's output file name.

    Drawn on the queue canvas rather than the window canvas: embedded Tk
    widgets always paint above canvas items, so a sheet on the window canvas
    would end up behind the queue. The dimming overlay is an image, which also
    makes it swallow clicks meant for the rows underneath.
    """

    def __init__(self, app: "App", job: D.Job):
        self.app = app
        self.job = job
        self.cv = app.queue.cv
        self.items: list[int] = []
        self.photos: list[ImageTk.PhotoImage] = []
        self.widgets: list[WG.W] = []
        self._build()

    def _build(self):
        cv = self.cv
        cw, ch = cv.winfo_width(), cv.winfo_height()

        overlay = ImageTk.PhotoImage(G.tint_layer((max(1, cw), max(1, ch)), (4, 6, 14, 170)))
        self.photos.append(overlay)
        dim = cv.create_image(0, 0, image=overlay, anchor="nw")
        self.items.append(dim)
        cv.tag_bind(dim, "<Button-1>", lambda _e: self.close())

        sw = min(452, max(280, cw - 48))
        sh = 188
        sx, sy = (cw - sw) // 2, max(10, (ch - sh) // 3)

        shadow = ImageTk.PhotoImage(G.glow((sw, sh), 18, (0, 0, 0), spread=22, alpha=170))
        self.photos.append(shadow)
        self.items.append(cv.create_image(sx - 22, sy - 22, image=shadow, anchor="nw"))
        panel = ImageTk.PhotoImage(G.rrect((sw, sh), 18, fill=(19, 22, 35, 250),
                                           outline=(255, 255, 255, 58)))
        self.photos.append(panel)
        self.items.append(cv.create_image(sx, sy, image=panel, anchor="nw"))

        self.items.append(cv.create_text(
            sx + 22, sy + 20, text="Output file name", fill=T.TEXT, anchor="nw",
            font=T.f("body_bold")))
        self.items.append(cv.create_text(
            sx + 22, sy + 42, text=WG.elide(T.f("small"), self.job.label, sw - 44),
            fill=T.TEXT_MUTE, anchor="nw", font=T.f("small")))

        self.field = WG.Field(cv, sx + 22, sy + 68, sw - 44, 34, value=self.job.name,
                              placeholder="Leave empty for the default template",
                              font=T.f("body"), bg="#0E111B",
                              on_return=lambda _v: self.save())
        self.widgets.append(self.field)

        self.items.append(cv.create_text(
            sx + 22, sy + 112, text="The extension is added for you.",
            fill=T.TEXT_MUTE, anchor="nw", font=T.f("tiny")))

        b_save = WG.Button(cv, sx + sw - 22 - 94, sy + sh - 48, 94, 32, text="Save",
                           icon="check", variant="primary", command=self.save)
        b_cancel = WG.Button(cv, sx + sw - 22 - 94 - 8 - 86, sy + sh - 48, 86, 32,
                             text="Cancel", variant="ghost", font=T.f("small"),
                             command=self.close)
        self.widgets += [b_save, b_cancel]

        self._esc = self.app.root.bind("<Escape>", lambda _e: self.close(), add="+")
        self.field.entry.focus_set()
        self.field.entry.selection_range(0, "end")

    def save(self):
        self.app.apply_name(self.job, self.field.get())
        self.close()

    def close(self):
        for wdg in self.widgets:
            wdg.destroy()
        self.widgets.clear()
        for item in self.items:
            self.cv.delete(item)
        self.items.clear()
        self.photos.clear()
        try:
            self.app.root.unbind("<Escape>", self._esc)
        except Exception:
            pass
        if self.app.name_sheet is self:
            self.app.name_sheet = None


# ------------------------------------------------------------- log window --
class LogWindow:
    def __init__(self, parent, engine: D.Engine):
        self.engine = engine
        self.seen = 0
        self.top = tk.Toplevel(parent)
        self.top.title("Activity log")
        self.top.configure(bg="#0A0C14")
        self.top.geometry("860x420")
        _dark_titlebar(self.top)

        bar = tk.Frame(self.top, bg="#0A0C14")
        bar.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(bar, text="yt-dlp output", bg="#0A0C14", fg=T.TEXT_DIM,
                 font=T.f("body_bold")).pack(side="left")
        for text, cmd in (("Copy", self.copy), ("Clear", self.clear),
                          ("Batches", self.open_batches)):
            tk.Button(bar, text=text, command=cmd, bg="#161A26", fg=T.TEXT,
                      activebackground="#222838", activeforeground=T.TEXT, bd=0,
                      relief="flat", padx=14, pady=4, font=T.f("small"),
                      cursor="hand2").pack(side="right", padx=4)

        self.text = tk.Text(self.top, bg="#0C0F18", fg="#C7D2EA", bd=0, relief="flat",
                            highlightthickness=0, wrap="none", font=T.f("mono"),
                            padx=12, pady=8, insertbackground=T.ACCENT_B_HEX)
        self.text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.text.configure(state="disabled")
        self.pump()

    def alive(self) -> bool:
        try:
            return bool(self.top.winfo_exists())
        except tk.TclError:
            return False

    def pump(self):
        lines = list(self.engine.log_lines)
        if len(lines) <= self.seen:
            return
        new = lines[self.seen:]
        self.seen = len(lines)
        self.text.configure(state="normal")
        self.text.insert("end", "\n".join(new) + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def open_batches(self):
        """Open the folder holding one file per queued batch."""
        _open_path(str(config.batches_dir()))

    def copy(self):
        self.top.clipboard_clear()
        self.top.clipboard_append("\n".join(self.engine.log_lines))

    def clear(self):
        self.engine.log_lines.clear()
        self.seen = 0
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def close(self):
        try:
            self.top.destroy()
        except tk.TclError:
            pass


# ----------------------------------------------------------- os helpers --
def _dark_titlebar(window):
    """Dark immersive caption, matching colour and rounded corners (Windows 10/11)."""
    if os.name != "nt":
        return
    import ctypes
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dwm = ctypes.windll.dwmapi
        for attr, value in ((20, 1), (35, 0x100907), (33, 2)):
            try:
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(ctypes.c_int(value)), 4)
            except Exception:
                pass
    except Exception:
        pass


def _open_path(path: str):
    if os.name == "nt":
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])