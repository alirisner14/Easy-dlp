"""A small widget toolkit drawn directly onto a Tk canvas.

Native Tk widgets cannot be translucent, so every control here is painted as an
RGBA image and composited over the frosted panels.  Only text entry uses a real
Tk widget (you cannot fake a caret), and those are colour-matched to the glass
behind them.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from . import graphics as G
from . import theme as T

_FONT_CACHE: dict[tuple, tkfont.Font] = {}


def font_obj(spec) -> tkfont.Font:
    key = tuple(spec)
    if key not in _FONT_CACHE:
        fam, size = spec[0], spec[1]
        weight = spec[2] if len(spec) > 2 else "normal"
        _FONT_CACHE[key] = tkfont.Font(family=fam, size=size, weight=weight)
    return _FONT_CACHE[key]


def measure(spec, text: str) -> int:
    return font_obj(spec).measure(text)


def elide(spec, text: str, max_px: int) -> str:
    """Truncate with an ellipsis so the string fits in max_px."""
    f = font_obj(spec)
    if f.measure(text) <= max_px:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if f.measure(text[:mid] + ell) <= max_px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell


def _canvas_size(cv: tk.Canvas) -> tuple[int, int]:
    """Canvas size in pixels, preferring the size it was configured with.

    winfo_width/height can still report a stale value right after a relayout,
    which would put a dropdown outside the visible area.
    """
    try:
        w = int(float(cv.cget("width")))
        h = int(float(cv.cget("height")))
    except Exception:
        w = h = 0
    if w <= 1:
        w = max(1, cv.winfo_width())
    if h <= 1:
        h = max(1, cv.winfo_height())
    return w, h


class W:
    """Base: a group of canvas items sharing one tag."""

    _seq = 0

    def __init__(self, cv: tk.Canvas, x, y, w, h):
        W._seq += 1
        self.cv = cv
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)
        self.tag = "w%d" % W._seq
        self.imgs: dict[str, ImageTk.PhotoImage] = {}
        self.enabled = True
        self.visible = True

    # -- image helpers -------------------------------------------------
    def keep(self, key: str, pil: Image.Image) -> ImageTk.PhotoImage:
        ph = ImageTk.PhotoImage(pil)
        self.imgs[key] = ph
        return ph

    def _bind_hover(self, on_enter, on_leave):
        self.cv.tag_bind(self.tag, "<Enter>", on_enter)
        self.cv.tag_bind(self.tag, "<Leave>", on_leave)

    def set_enabled(self, value: bool):
        self.enabled = bool(value)
        self._refresh()

    def _refresh(self):
        pass

    def hide(self):
        self.visible = False
        self.cv.itemconfigure(self.tag, state="hidden")

    def show(self):
        self.visible = True
        self.cv.itemconfigure(self.tag, state="normal")

    def move_to(self, x, y):
        self.cv.move(self.tag, int(x) - self.x, int(y) - self.y)
        self.x, self.y = int(x), int(y)

    def move_by(self, dx, dy):
        self.cv.move(self.tag, dx, dy)
        self.x += int(dx)
        self.y += int(dy)

    def destroy(self):
        self.cv.delete(self.tag)
        self.imgs.clear()


# ------------------------------------------------------------------ button --
class Button(W):
    """Pill button. variant: primary | ghost | subtle | danger."""

    def __init__(self, cv, x, y, w, h, text="", icon=None, variant="ghost",
                 command=None, font=None, radius=None, tooltip=None):
        super().__init__(cv, x, y, w, h)
        self.text = text
        self.icon_name = icon
        self.variant = variant
        self.command = command
        self.font = font or T.f("button")
        self.radius = radius if radius is not None else min(self.h // 2, 14)
        self.state = "rest"
        self.tooltip = tooltip
        self.shift = False          # was Shift held for the click in hand
        self._build()

    # -- painting ------------------------------------------------------
    def _face(self, state: str) -> Image.Image:
        w, h, r = self.w, self.h, self.radius
        if self.variant == "primary":
            a = (124, 92, 255) if state != "hover" else (146, 116, 255)
            b = (35, 211, 232) if state != "hover" else (72, 226, 244)
            img = G.gradient((w, h), a, b)
            img.putalpha(G.rounded_mask((w, h), r))
            rim = G.rrect((w, h), r, outline=(255, 255, 255, 70), width=1)
            img = Image.alpha_composite(img, rim)
        elif self.variant == "danger":
            fill = (255, 99, 122, 36 if state == "rest" else 62)
            img = G.rrect((w, h), r, fill=fill, outline=(255, 99, 122, 110), width=1)
        elif self.variant == "subtle":
            fill = (255, 255, 255, 8 if state == "rest" else 18)
            img = G.rrect((w, h), r, fill=fill, outline=(255, 255, 255, 22), width=1)
        else:  # ghost
            fill = T.GHOST if state == "rest" else T.GHOST_HOVER
            img = G.rrect((w, h), r, fill=fill, outline=(255, 255, 255, 38), width=1)
        if state == "down":
            img = Image.alpha_composite(img, G.rrect((w, h), r, fill=(0, 0, 0, 50)))
        if not self.enabled:
            img.putalpha(img.split()[3].point(lambda v: int(v * 0.4)))
        return img

    def _fg(self) -> str:
        if not self.enabled:
            return T.TEXT_MUTE
        if self.variant == "primary":
            return T.TEXT_ON_ACCENT
        if self.variant == "danger":
            return T.ERR_HEX
        return T.TEXT

    def _build(self):
        cv = self.cv
        if self.variant == "primary":
            gl = G.glow((self.w, self.h), self.radius, T.ACCENT_A, spread=16, alpha=110)
            self.glow_item = cv.create_image(
                self.x - 16, self.y - 16, image=self.keep("glow", gl), anchor="nw", tags=self.tag)
        for st in ("rest", "hover", "down"):
            self.keep(st, self._face(st))
        self.bg_item = cv.create_image(
            self.x, self.y, image=self.imgs["rest"], anchor="nw", tags=self.tag)

        fg = self._fg()
        rgba = tuple(int(fg[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
        icon_w = 0
        if self.icon_name:
            ic = G.icon(self.icon_name, 16, rgba, width=1.7)
            self.keep("icon", ic)
            icon_w = 16 + (7 if self.text else 0)
        tw = measure(self.font, self.text) if self.text else 0
        total = icon_w + tw
        sx = self.x + (self.w - total) / 2
        cy = self.y + self.h / 2
        if self.icon_name:
            self.icon_item = cv.create_image(sx, cy, image=self.imgs["icon"],
                                             anchor="w", tags=self.tag)
            sx += icon_w
        if self.text:
            self.text_item = cv.create_text(sx, cy, text=self.text, fill=fg, anchor="w",
                                            font=self.font, tags=self.tag)

        cv.tag_bind(self.tag, "<Enter>", self._enter)
        cv.tag_bind(self.tag, "<Leave>", self._leave)
        cv.tag_bind(self.tag, "<Button-1>", self._press)
        cv.tag_bind(self.tag, "<ButtonRelease-1>", self._release)

    # -- events --------------------------------------------------------
    def _enter(self, _e=None):
        if not self.enabled:
            return
        self.cv.configure(cursor="hand2")
        self.cv.itemconfigure(self.bg_item, image=self.imgs["hover"])
        if self.tooltip:
            Tooltip.show(self.cv, self.tooltip, self.x + self.w // 2, self.y - 6)

    def _leave(self, _e=None):
        self.cv.configure(cursor="")
        if self.enabled:
            self.cv.itemconfigure(self.bg_item, image=self.imgs["rest"])
        Tooltip.hide(self.cv)

    def _press(self, _e=None):
        if self.enabled:
            self.cv.itemconfigure(self.bg_item, image=self.imgs["down"])

    def _release(self, _e=None):
        if not self.enabled:
            return
        self.cv.itemconfigure(self.bg_item, image=self.imgs["hover"])
        if self.command:
            # commands that want to know can read this instead of taking
            # the event, which would change every callback in the app
            self.shift = bool(getattr(_e, "state", 0) & 0x0001)
            self.command()

    def set_text(self, text: str, icon: str | None = None):
        self.text = text
        if icon is not None:
            self.icon_name = icon
        self.cv.delete(self.tag)
        self.imgs.clear()
        self._build()

    def _refresh(self):
        for st in ("rest", "hover", "down"):
            self.keep(st, self._face(st))
        self.cv.itemconfigure(self.bg_item, image=self.imgs["rest"])
        if self.text:
            self.cv.itemconfigure(self.text_item, fill=self._fg())


class IconButton(Button):
    def __init__(self, cv, x, y, size, icon, command=None, tooltip=None, variant="subtle"):
        super().__init__(cv, x, y, size, size, text="", icon=icon, variant=variant,
                         command=command, radius=size // 2, tooltip=tooltip)


# ----------------------------------------------------------------- tooltip --
class Tooltip:
    """One shared canvas tooltip."""
    _items: list[int] = []
    _img = None
    _after = None

    @classmethod
    def show(cls, cv, text, x, y, delay=420):
        cls.hide(cv)
        cls._after = cv.after(delay, lambda: cls._draw(cv, text, x, y))

    @classmethod
    def _draw(cls, cv, text, x, y):
        spec = T.f("small")
        tw = measure(spec, text)
        w, h = tw + 20, 26
        x0 = max(6, min(int(cv.winfo_width()) - w - 6, int(x - w / 2)))
        y0 = int(y - h)
        if y0 < 4:
            y0 = int(y + 26)
        img = G.rrect((w, h), 8, fill=(14, 16, 26, 238), outline=(255, 255, 255, 40))
        cls._img = ImageTk.PhotoImage(img)
        cls._items = [
            cv.create_image(x0, y0, image=cls._img, anchor="nw"),
            cv.create_text(x0 + w / 2, y0 + h / 2, text=text, fill=T.TEXT,
                           font=spec, anchor="center"),
        ]

    @classmethod
    def hide(cls, cv):
        if cls._after is not None:
            try:
                cv.after_cancel(cls._after)
            except Exception:
                pass
            cls._after = None
        for i in cls._items:
            cv.delete(i)
        cls._items = []


# ------------------------------------------------------------------ switch --
class Switch(W):
    """Label plus a sliding toggle, right-aligned within (x, y, w)."""

    TRACK_W, TRACK_H = 38, 21

    def __init__(self, cv, x, y, w, label, value=False, command=None, tooltip=None):
        super().__init__(cv, x, y, w, 26)
        self.label = label
        self.value = bool(value)
        self.command = command
        self.tooltip = tooltip
        self._build()

    def _track(self, on: bool, hover=False) -> Image.Image:
        w, h, r = self.TRACK_W, self.TRACK_H, self.TRACK_H // 2
        if on:
            img = G.gradient((w, h), (124, 92, 255), (35, 211, 232))
            img.putalpha(G.rounded_mask((w, h), r))
            img = Image.alpha_composite(img, G.rrect((w, h), r, outline=(255, 255, 255, 80), width=1))
        else:
            fill = (255, 255, 255, 26 if hover else 16)
            img = G.rrect((w, h), r, fill=fill, outline=(255, 255, 255, 46), width=1)
        return img

    def _build(self):
        cv = self.cv
        cy = self.y + self.h / 2
        self.text_item = cv.create_text(
            self.x, cy, text=self.label, fill=T.TEXT_DIM, anchor="w",
            font=T.f("body"), tags=self.tag)
        tx = self.x + self.w - self.TRACK_W
        self.keep("on", self._track(True))
        self.keep("off", self._track(False))
        self.keep("off_h", self._track(False, hover=True))
        self.track_item = cv.create_image(
            tx, cy - self.TRACK_H / 2,
            image=self.imgs["on" if self.value else "off"], anchor="nw", tags=self.tag)
        knob = G.rrect((15, 15), 7, fill=(255, 255, 255, 246))
        self.keep("knob", knob)
        kx = tx + (self.TRACK_W - 18) if self.value else tx + 3
        self.knob_item = cv.create_image(kx, cy - 7.5, image=self.imgs["knob"],
                                         anchor="nw", tags=self.tag)
        self._tx = tx
        cv.tag_bind(self.tag, "<Enter>", self._enter)
        cv.tag_bind(self.tag, "<Leave>", self._leave)
        cv.tag_bind(self.tag, "<Button-1>", self._click)

    def _enter(self, _e=None):
        if not self.enabled:
            return
        self.cv.configure(cursor="hand2")
        self.cv.itemconfigure(self.text_item, fill=T.TEXT)
        if not self.value:
            self.cv.itemconfigure(self.track_item, image=self.imgs["off_h"])
        if self.tooltip:
            Tooltip.show(self.cv, self.tooltip, self.x + self.w / 2, self.y - 2)

    def _leave(self, _e=None):
        self.cv.configure(cursor="")
        self.cv.itemconfigure(self.text_item, fill=T.TEXT_DIM)
        if not self.value:
            self.cv.itemconfigure(self.track_item, image=self.imgs["off"])
        Tooltip.hide(self.cv)

    def _click(self, _e=None):
        if not self.enabled:
            return
        self.set(not self.value)
        if self.command:
            self.command(self.value)

    def set(self, value: bool, animate=True):
        self.value = bool(value)
        self.cv.itemconfigure(self.track_item,
                              image=self.imgs["on" if self.value else "off"])
        target = self._tx + (self.TRACK_W - 18) if self.value else self._tx + 3
        if not animate:
            self.cv.coords(self.knob_item, target, self.y + self.h / 2 - 7.5)
            return
        x0 = self.cv.coords(self.knob_item)[0]
        steps = 6
        for i in range(1, steps + 1):
            t = i / steps
            ease = 1 - (1 - t) ** 3
            self.cv.after(i * 14, lambda v=x0 + (target - x0) * ease:
                          self.cv.coords(self.knob_item, v, self.y + self.h / 2 - 7.5))

    def _refresh(self):
        col = T.TEXT_DIM if self.enabled else T.TEXT_MUTE
        self.cv.itemconfigure(self.text_item, fill=col)


# ----------------------------------------------------------------- tickbox --
class TickBox(W):
    """Square check box used to select queue rows."""

    def __init__(self, cv, x, y, size=20, value=False, command=None, tooltip=None):
        super().__init__(cv, x, y, size, size)
        self.value = bool(value)
        self.command = command
        self.tooltip = tooltip
        self.hovered = False
        self._build()

    def _face(self, checked: bool, hover: bool):
        size, r = self.w, max(5, self.w // 3)
        if checked:
            img = G.gradient((size, size), (124, 92, 255), (35, 211, 232))
            img.putalpha(G.rounded_mask((size, size), r))
            rim = (255, 255, 255, 110 if hover else 80)
            img = Image.alpha_composite(img, G.rrect((size, size), r, outline=rim, width=1))
            glyph = G.icon("check", size - 6, (12, 10, 26, 255), width=2.1)
            img.alpha_composite(glyph, (3, 3))
            return img
        fill = (255, 255, 255, 26 if hover else 12)
        rim = (255, 255, 255, 96 if hover else 58)
        return G.rrect((size, size), r, fill=fill, outline=rim, width=1)

    def _build(self):
        for checked in (False, True):
            for hover in (False, True):
                self.keep("%d%d" % (checked, hover), self._face(checked, hover))
        self.item = self.cv.create_image(self.x, self.y, image=self._current(),
                                         anchor="nw", tags=self.tag)
        self.cv.tag_bind(self.tag, "<Enter>", self._enter)
        self.cv.tag_bind(self.tag, "<Leave>", self._leave)
        self.cv.tag_bind(self.tag, "<Button-1>", self._click)

    def _current(self):
        return self.imgs["%d%d" % (int(self.value), int(self.hovered))]

    def _paint(self):
        self.cv.itemconfigure(self.item, image=self._current())

    def _enter(self, _e=None):
        self.hovered = True
        self.cv.configure(cursor="hand2")
        self._paint()
        if self.tooltip:
            Tooltip.show(self.cv, self.tooltip, self.x + self.w / 2, self.y - 4)

    def _leave(self, _e=None):
        self.hovered = False
        self.cv.configure(cursor="")
        self._paint()
        Tooltip.hide(self.cv)

    def _click(self, _e=None):
        if not self.enabled:
            return
        self.value = not self.value
        self._paint()
        if self.command:
            self.command(self.value)
        return "break"

    def set(self, value: bool):
        value = bool(value)
        if value != self.value:
            self.value = value
            self._paint()


# ------------------------------------------------------------------ select --
class Select(W):
    """Dropdown whose menu is drawn on the same canvas (so it stays translucent)."""

    open_instance: "Select | None" = None

    def __init__(self, cv, x, y, w, h, options, value=None, command=None,
                 font=None, radius=None):
        super().__init__(cv, x, y, w, h)
        self.options = list(options)
        self.value = value if value in self.options else (self.options[0] if self.options else "")
        self.command = command
        self.font = font or T.f("body")
        self.radius = radius if radius is not None else T.CTRL_R
        self.menu_items: list[int] = []
        self.menu_imgs: list[ImageTk.PhotoImage] = []
        self._build()

    def _face(self, state="rest") -> Image.Image:
        fill = (255, 255, 255, 10 if state == "rest" else 20)
        rim = (255, 255, 255, 34 if state == "rest" else 60)
        return G.rrect((self.w, self.h), self.radius, fill=fill, outline=rim, width=1)

    def _build(self):
        cv = self.cv
        self.keep("rest", self._face())
        self.keep("hover", self._face("hover"))
        self.bg_item = cv.create_image(self.x, self.y, image=self.imgs["rest"],
                                       anchor="nw", tags=self.tag)
        cy = self.y + self.h / 2
        self.text_item = cv.create_text(
            self.x + 12, cy, text=self._display(), fill=T.TEXT, anchor="w",
            font=self.font, tags=self.tag)
        self.keep("chev", G.icon("chevron", 14, (154, 166, 196, 255), width=1.7))
        self.chev_item = cv.create_image(self.x + self.w - 12, cy, image=self.imgs["chev"],
                                         anchor="e", tags=self.tag)
        cv.tag_bind(self.tag, "<Enter>", self._enter)
        cv.tag_bind(self.tag, "<Leave>", self._leave)
        cv.tag_bind(self.tag, "<Button-1>", self._toggle)

    def _display(self) -> str:
        return elide(self.font, str(self.value), self.w - 36)

    def _enter(self, _e=None):
        if self.enabled:
            self.cv.configure(cursor="hand2")
            self.cv.itemconfigure(self.bg_item, image=self.imgs["hover"])

    def _leave(self, _e=None):
        self.cv.configure(cursor="")
        self.cv.itemconfigure(self.bg_item, image=self.imgs["rest"])

    def _toggle(self, _e=None):
        if not self.enabled:
            return
        if Select.open_instance is self:
            self.close()
        else:
            if Select.open_instance:
                Select.open_instance.close()
            self.open()

    # -- menu ----------------------------------------------------------
    def open(self):
        cv = self.cv
        Select.open_instance = self
        pad = 6
        view_w, view_h = _canvas_size(cv)
        row_h = 30 if len(self.options) * 30 + 12 <= view_h - 16 else 26
        mw = max(self.w, 168)
        mh = len(self.options) * row_h + pad * 2

        mx = self.x
        my = self.y + self.h + 6
        if my + mh > view_h - 8:
            my = self.y - mh - 6            # not enough room below, open upwards
        # whichever way it went, keep the whole menu inside the canvas
        my = max(8, min(my, view_h - mh - 8))
        mx = max(8, min(mx, view_w - mw - 8))

        shadow = G.glow((mw, mh), 14, (0, 0, 0), spread=18, alpha=150)
        panel = G.rrect((mw, mh), 14, fill=(16, 19, 31, 243), outline=(255, 255, 255, 50))
        self.menu_imgs = [ImageTk.PhotoImage(shadow), ImageTk.PhotoImage(panel)]
        self.menu_items = [
            cv.create_image(mx - 18, my - 18, image=self.menu_imgs[0], anchor="nw"),
            cv.create_image(mx, my, image=self.menu_imgs[1], anchor="nw"),
        ]

        hl = G.rrect((mw - pad * 2, row_h - 2), 8, fill=(255, 255, 255, 22))
        self.menu_imgs.append(ImageTk.PhotoImage(hl))
        check = G.icon("check", 13, (63, 216, 234, 255), width=2.0)
        self.menu_imgs.append(ImageTk.PhotoImage(check))

        for i, opt in enumerate(self.options):
            ry = my + pad + i * row_h
            tag = "%s_opt%d" % (self.tag, i)
            rect = cv.create_rectangle(mx + pad, ry, mx + mw - pad, ry + row_h - 2,
                                       fill="", outline="", tags=tag)
            hl_item = cv.create_image(mx + pad, ry, image=self.menu_imgs[2],
                                      anchor="nw", state="hidden", tags=tag)
            is_cur = opt == self.value
            txt = cv.create_text(mx + pad + 12, ry + row_h / 2 - 1, text=elide(self.font, str(opt), mw - 52),
                                 fill=T.TEXT if is_cur else T.TEXT_DIM, anchor="w",
                                 font=self.font, tags=tag)
            self.menu_items += [rect, hl_item, txt]
            if is_cur:
                self.menu_items.append(
                    cv.create_image(mx + mw - pad - 10, ry + row_h / 2 - 1,
                                    image=self.menu_imgs[3], anchor="e", tags=tag))
            cv.tag_bind(tag, "<Enter>",
                        lambda _e, it=hl_item, t=txt: (cv.itemconfigure(it, state="normal"),
                                                       cv.itemconfigure(t, fill=T.TEXT)))
            cv.tag_bind(tag, "<Leave>",
                        lambda _e, it=hl_item, t=txt, c=is_cur: (
                            cv.itemconfigure(it, state="hidden"),
                            cv.itemconfigure(t, fill=T.TEXT if c else T.TEXT_DIM)))
            cv.tag_bind(tag, "<Button-1>", lambda _e, o=opt: self._choose(o))

        self._menu_box = (mx, my, mx + mw, my + mh)
        self._hidden_windows = []
        for item in cv.find_all():
            if cv.type(item) != "window" or cv.itemcget(item, "state") == "hidden":
                continue
            bx = cv.bbox(item)
            if bx and bx[0] < mx + mw and bx[2] > mx and bx[1] < my + mh and bx[3] > my:
                cv.itemconfigure(item, state="hidden")
                self._hidden_windows.append(item)
        # Registering this during the opening click would let that same event
        # reach _maybe_close and shut the menu again, so wait for the event to
        # finish being delivered first.
        self._outside = None
        self._bind_after = cv.after_idle(self._bind_outside)

    def _bind_outside(self):
        self._bind_after = None
        if Select.open_instance is self:
            self._outside = self.cv.bind("<Button-1>", self._maybe_close, add="+")

    def _maybe_close(self, e):
        if Select.open_instance is not self:
            return
        x0, y0, x1, y1 = self._menu_box
        if not (x0 <= e.x <= x1 and y0 <= e.y <= y1):
            self.close()

    def _choose(self, opt):
        self.value = opt
        self.cv.itemconfigure(self.text_item, text=self._display())
        self.close()
        if self.command:
            self.command(opt)

    def close(self):
        cv = self.cv
        for i in self.menu_items:
            cv.delete(i)
        self.menu_items = []
        self.menu_imgs = []
        pending = getattr(self, "_bind_after", None)
        if pending is not None:
            try:
                cv.after_cancel(pending)
            except Exception:
                pass
            self._bind_after = None
        for item in getattr(self, "_hidden_windows", []):
            try:
                cv.itemconfigure(item, state="normal")
            except Exception:
                pass
        self._hidden_windows = []
        if Select.open_instance is self:
            Select.open_instance = None
        if self._outside is not None:
            try:
                cv.unbind("<Button-1>", self._outside)
            except Exception:
                pass
            self._outside = None

    def set(self, value, notify=False):
        if value not in self.options:
            return
        self.value = value
        self.cv.itemconfigure(self.text_item, text=self._display())
        if notify and self.command:
            self.command(value)

    def set_options(self, options, value=None):
        self.options = list(options)
        if value is not None:
            self.value = value
        elif self.value not in self.options:
            self.value = self.options[0] if self.options else ""
        self.cv.itemconfigure(self.text_item, text=self._display())

    def _refresh(self):
        self.cv.itemconfigure(self.text_item, fill=T.TEXT if self.enabled else T.TEXT_MUTE)
        a = 255 if self.enabled else 110
        self.keep("chev", G.icon("chevron", 14, (154, 166, 196, a), width=1.7))
        self.cv.itemconfigure(self.chev_item, image=self.imgs["chev"])


# ------------------------------------------------------------------- field --
class _Placeholder:
    """Placeholder text living inside the Tk widget.

    A canvas text item cannot be used: embedded Tk widgets always paint above
    canvas items, so the hint would be hidden behind the entry it belongs to.
    """

    def _ph_init(self, placeholder: str):
        self.placeholder = placeholder
        self._ph_active = False
        self._ph_apply()

    def _ph_apply(self):
        if self.placeholder and not self._read_raw():
            self._ph_active = True
            self._write_raw(self.placeholder)
            self._set_fg(T.TEXT_MUTE)

    def _ph_clear(self):
        if self._ph_active:
            self._ph_active = False
            self._write_raw("")
            self._set_fg(T.TEXT)

    def _ph_focus_in(self, _e=None):
        self._ph_clear()
        self._focus_paint(True)

    def _ph_focus_out(self, _e=None):
        self._ph_apply()
        self._focus_paint(False)


class Field(W, _Placeholder):
    """Recessed single-line input: a glass well with a real Tk entry inside."""

    def __init__(self, cv, x, y, w, h, value="", placeholder="", bg="#12151F",
                 font=None, on_change=None, on_return=None):
        super().__init__(cv, x, y, w, h)
        self.font = font or T.f("body")
        self.bg = bg
        self.on_change = on_change
        self.var = tk.StringVar(value=value)
        self._build()
        self._ph_init(placeholder)
        self.var.trace_add("write", self._changed)
        if on_return:
            self.entry.bind("<Return>", lambda _e: on_return(self.get()))

    # -- placeholder plumbing -----------------------------------------
    def _read_raw(self) -> str:
        return self.var.get()

    def _write_raw(self, value: str):
        self.var.set(value)

    def _set_fg(self, color: str):
        self.entry.configure(fg=color)

    def _focus_paint(self, focused: bool):
        self.cv.itemconfigure(self.bg_item,
                              image=self.imgs["focus" if focused else "rest"])

    def _changed(self, *_):
        if self._ph_active or not self.on_change:
            return
        self.on_change(self.var.get())

    def _well(self, focus=False) -> Image.Image:
        rim = (63, 216, 234, 150) if focus else T.WELL_RIM
        return G.rrect((self.w, self.h), T.CTRL_R, fill=T.WELL, outline=rim, width=1)

    def _build(self):
        cv = self.cv
        self.keep("rest", self._well())
        self.keep("focus", self._well(True))
        self.bg_item = cv.create_image(self.x, self.y, image=self.imgs["rest"],
                                       anchor="nw", tags=self.tag)
        self.entry = tk.Entry(
            cv, textvariable=self.var, font=self.font, bd=0, relief="flat",
            highlightthickness=0, bg=self.bg, fg=T.TEXT,
            insertbackground=T.ACCENT_B_HEX, selectbackground="#33406B",
            selectforeground=T.TEXT,
        )
        self.win_item = cv.create_window(
            self.x + 11, self.y + self.h / 2, window=self.entry, anchor="w",
            width=self.w - 22, height=self.h - 12, tags=self.tag)
        self.entry.bind("<FocusIn>", self._ph_focus_in)
        self.entry.bind("<FocusOut>", self._ph_focus_out)

    def get(self) -> str:
        return "" if self._ph_active else self.var.get()

    def set(self, value: str):
        self._ph_active = False
        self._set_fg(T.TEXT)
        self.var.set(value)
        if not value:
            self._ph_apply()

    def set_bg(self, color: str):
        self.bg = color
        self.entry.configure(bg=color)

    def _refresh(self):
        self.entry.configure(state="normal" if self.enabled else "disabled",
                             fg=T.TEXT if self.enabled else T.TEXT_MUTE)

    def destroy(self):
        self.entry.destroy()
        super().destroy()


class TextArea(W, _Placeholder):
    """Multi-line input for pasting batches of links."""

    def __init__(self, cv, x, y, w, h, placeholder="", bg="#12151F", font=None,
                 on_change=None):
        super().__init__(cv, x, y, w, h)
        self.font = font or T.f("body")
        self.bg = bg
        self.on_change = on_change
        self._build()
        self._ph_init(placeholder)

    def _read_raw(self) -> str:
        return self.text.get("1.0", "end-1c")

    def _write_raw(self, value: str):
        self.text.delete("1.0", "end")
        if value:
            self.text.insert("1.0", value)

    def _set_fg(self, color: str):
        self.text.configure(fg=color)

    def _focus_paint(self, focused: bool):
        self.cv.itemconfigure(self.bg_item,
                              image=self.imgs["focus" if focused else "rest"])

    def _build(self):
        cv = self.cv
        self.keep("rest", G.rrect((self.w, self.h), T.CTRL_R, fill=T.WELL,
                                  outline=T.WELL_RIM, width=1))
        self.keep("focus", G.rrect((self.w, self.h), T.CTRL_R, fill=T.WELL,
                                   outline=(63, 216, 234, 150), width=1))
        self.bg_item = cv.create_image(self.x, self.y, image=self.imgs["rest"],
                                       anchor="nw", tags=self.tag)
        self.text = tk.Text(
            cv, font=self.font, bd=0, relief="flat", highlightthickness=0,
            bg=self.bg, fg=T.TEXT, insertbackground=T.ACCENT_B_HEX, wrap="none",
            selectbackground="#33406B", selectforeground=T.TEXT, padx=0, pady=0,
            spacing1=2, spacing3=2,
        )
        self.win_item = cv.create_window(
            self.x + 11, self.y + 9, window=self.text, anchor="nw",
            width=self.w - 22, height=self.h - 18, tags=self.tag)
        self.text.bind("<FocusIn>", self._ph_focus_in)
        self.text.bind("<FocusOut>", self._ph_focus_out)
        self.text.bind("<<Modified>>", self._modified)

    def _modified(self, _e=None):
        self.text.edit_modified(False)
        if self.on_change and not self._ph_active:
            self.on_change(self.get())

    def get(self) -> str:
        return "" if self._ph_active else self._read_raw()

    def set(self, value: str):
        self._ph_active = False
        self._set_fg(T.TEXT)
        self._write_raw(value)
        if not value:
            self._ph_apply()

    def append(self, value: str):
        self._ph_clear()
        cur = self._read_raw()
        if cur and not cur.endswith("\n"):
            value = "\n" + value
        self.text.insert("end", value)
        self._set_fg(T.TEXT)

    def set_bg(self, color: str):
        self.bg = color
        self.text.configure(bg=color)

    def destroy(self):
        self.text.destroy()
        super().destroy()


# ---------------------------------------------------------------- progress --
class Bar(W):
    """Rounded progress track with a gradient fill and a bright head."""

    def __init__(self, cv, x, y, w, h=6):
        super().__init__(cv, x, y, w, h)
        self.value = 0.0
        self.tone = "accent"
        self._full: Image.Image | None = None
        self._build()

    def _gradient_for(self, tone: str) -> Image.Image:
        pairs = {
            "accent": ((124, 92, 255), (35, 211, 232)),
            "ok": ((46, 190, 140), (61, 220, 151)),
            "err": ((214, 70, 96), (255, 99, 122)),
            "warn": ((214, 140, 40), (255, 186, 73)),
        }
        a, b = pairs.get(tone, pairs["accent"])
        img = G.gradient((self.w, self.h), a, b)
        img.putalpha(G.rounded_mask((self.w, self.h), self.h // 2))
        return img

    def _build(self):
        cv = self.cv
        self.keep("trough", G.rrect((self.w, self.h), self.h // 2, fill=T.TROUGH))
        self.trough_item = cv.create_image(self.x, self.y, image=self.imgs["trough"],
                                           anchor="nw", tags=self.tag)
        self._full = self._gradient_for(self.tone)
        self.fill_item = cv.create_image(self.x, self.y, anchor="nw",
                                         state="hidden", tags=self.tag)

    def set(self, value: float, tone: str | None = None):
        if tone and tone != self.tone:
            self.tone = tone
            self._full = self._gradient_for(tone)
        value = max(0.0, min(1.0, float(value)))
        self.value = value
        px = int(self.w * value)
        if px < 2:
            self.cv.itemconfigure(self.fill_item, state="hidden")
            return
        crop = self._full.crop((0, 0, px, self.h))
        self.keep("fill", crop)
        self.cv.itemconfigure(self.fill_item, image=self.imgs["fill"], state="normal")

    def resize(self, w: int):
        self.w = int(w)
        self.cv.delete(self.tag)
        self.imgs.clear()
        self._build()
        self.set(self.value)


# -------------------------------------------------------------------- pill --
class Pill(W):
    """Status badge."""

    def __init__(self, cv, x, y, text="", color=T.IDLE_HEX, font=None, anchor="nw"):
        self.font = font or T.f("tiny")
        w = measure(self.font, text) + 18
        super().__init__(cv, x, y, w, 19)
        self.anchor = anchor
        self.text = text
        self.color = color
        self._build()

    def _build(self):
        cv = self.cv
        rgb = tuple(int(self.color[i:i + 2], 16) for i in (1, 3, 5))
        img = G.rrect((self.w, self.h), self.h // 2,
                      fill=(rgb[0], rgb[1], rgb[2], 38),
                      outline=(rgb[0], rgb[1], rgb[2], 120), width=1)
        self.keep("bg", img)
        self.bg_item = cv.create_image(self.x, self.y, image=self.imgs["bg"],
                                       anchor="nw", tags=self.tag)
        self.text_item = cv.create_text(self.x + self.w / 2, self.y + self.h / 2,
                                        text=self.text, fill=self.color, anchor="center",
                                        font=self.font, tags=self.tag)

    def set(self, text: str, color: str | None = None):
        if text == self.text and (color is None or color == self.color):
            return
        self.text = text
        if color:
            self.color = color
        x, y = self.x, self.y
        self.cv.delete(self.tag)
        self.imgs.clear()
        self.w = measure(self.font, text) + 18
        self.x, self.y = x, y
        self._build()

    def move(self, x, y):
        dx, dy = x - self.x, y - self.y
        self.cv.move(self.tag, dx, dy)
        self.x, self.y = x, y
