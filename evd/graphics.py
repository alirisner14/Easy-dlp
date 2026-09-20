"""Pillow compositor: backdrop, frosted panels, controls and icons.

Everything the UI paints is an RGBA image drawn onto a Tk canvas.  Tk 8.6
alpha-composites canvas images over the items beneath them, so translucent
surfaces stack correctly and genuinely show what is behind them.
"""
from __future__ import annotations

import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SS = 4  # supersample factor for crisp small geometry


# ----------------------------------------------------------------- basics ---
def blur(img: Image.Image, radius: float) -> Image.Image:
    """Gaussian blur, downsampled for large radii (visually identical, far faster)."""
    if radius < 4:
        return img.filter(ImageFilter.GaussianBlur(radius))
    w, h = img.size
    s = 2 if radius < 40 else 4
    small = img.resize((max(1, w // s), max(1, h // s)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius / s))
    return small.resize((w, h), Image.BICUBIC)


def rounded_mask(size, radius: int) -> Image.Image:
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius * SS, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def rrect(size, radius, fill=None, outline=None, width=1) -> Image.Image:
    """Antialiased rounded rectangle as RGBA."""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, w * SS - 1, h * SS - 1], radius * SS,
        fill=fill, outline=outline, width=int(width * SS) if outline else 0,
    )
    return img.resize((w, h), Image.LANCZOS)


def gradient(size, c1, c2, horizontal=True) -> Image.Image:
    """Two-stop linear gradient from RGB(A) tuples."""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    n = w if horizontal else h
    strip = Image.new("RGBA", (n, 1))
    px = strip.load()
    a1 = c1[3] if len(c1) > 3 else 255
    a2 = c2[3] if len(c2) > 3 else 255
    for i in range(n):
        t = i / max(1, n - 1)
        px[i, 0] = (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
            int(a1 + (a2 - a1) * t),
        )
    return strip.resize((w, h), Image.BILINEAR)


def tint_layer(size, rgba) -> Image.Image:
    return Image.new("RGBA", (max(1, int(size[0])), max(1, int(size[1]))), rgba)


def glow(size, radius, color, spread=14, alpha=140) -> Image.Image:
    """Soft coloured halo used behind accented controls."""
    w, h = int(size[0]), int(size[1])
    img = Image.new("RGBA", (w + spread * 2, h + spread * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [spread, spread, spread + w, spread + h], radius,
        fill=(color[0], color[1], color[2], alpha),
    )
    return blur(img, spread * 0.55)


# --------------------------------------------------------------- backdrop ---
_BLOBS = [
    (0.04, -0.06, 0.52, 0.62, (92, 58, 226)),
    (0.92, 0.04, 0.46, 0.52, (24, 132, 186)),
    (0.80, 0.92, 0.55, 0.60, (188, 40, 122)),
    (0.22, 0.98, 0.48, 0.52, (22, 128, 168)),
    (0.52, 0.42, 0.40, 0.44, (58, 40, 158)),
]


def make_backdrop(w: int, h: int) -> Image.Image:
    """Dark aurora field: blurred colour blobs, vignette and a little grain."""
    w, h = max(2, int(w)), max(2, int(h))
    s = 4
    sw, sh = max(2, w // s), max(2, h // s)

    small = Image.new("RGB", (sw, sh), (8, 10, 18))
    d = ImageDraw.Draw(small)
    for cx, cy, rx, ry, col in _BLOBS:
        x, y, a, b = cx * sw, cy * sh, rx * sw, ry * sh
        d.ellipse([x - a, y - b, x + a, y + b], fill=col)
    small = small.filter(ImageFilter.GaussianBlur(min(sw, sh) * 0.28))
    small = Image.blend(Image.new("RGB", (sw, sh), (7, 9, 16)), small, 0.62)
    bg = small.resize((w, h), Image.BICUBIC)

    vg = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(vg).ellipse([-sw * 0.30, -sh * 0.30, sw * 1.30, sh * 1.30], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(min(sw, sh) * 0.22)).resize((w, h), Image.BICUBIC)
    bg = Image.composite(bg, Image.new("RGB", (w, h), (4, 5, 11)), vg)

    noise = Image.effect_noise((w, h), 7).convert("L")
    return Image.blend(bg, Image.merge("RGB", (noise, noise, noise)), 0.030)


def frost(backdrop, box, radius=18, blur_px=26, tint=(255, 255, 255, 16),
          shadow=26, sheen=True):
    """Frosted panel sampled from the backdrop.

    Returns (tile, origin); the tile carries margin for its drop shadow.
    """
    x0, y0, x1, y1 = (int(v) for v in box)
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    m = shadow

    tile = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([m, m + 7, m + w, m + h + 7], radius, fill=(0, 0, 0, 130))
    tile = Image.alpha_composite(tile, blur(sh, m * 0.5))

    # A panel can sit partly, or entirely, outside the window: the left column
    # scrolls, so its cards may start below the bottom edge. Clamp the sampling
    # box into the backdrop and stretch what we get over the panel, rather than
    # handing Pillow an inverted crop.
    bw, bh = backdrop.size
    sx0 = max(0, min(bw - 1, x0))
    sy0 = max(0, min(bh - 1, y0))
    sx1 = max(sx0 + 1, min(bw, x1))
    sy1 = max(sy0 + 1, min(bh, y1))
    crop = backdrop.crop((sx0, sy0, sx1, sy1)).convert("RGB")
    if crop.size != (w, h):
        crop = crop.resize((w, h), Image.BICUBIC)
    glass = blur(crop, blur_px).convert("RGBA")
    # deepen first, then frost: keeps the aurora readable through the panel
    # while giving the text on top of it somewhere dark to sit
    glass = Image.alpha_composite(glass, tint_layer((w, h), (8, 10, 20, 96)))
    glass = Image.alpha_composite(glass, tint_layer((w, h), tint))

    if sheen:
        sl = Image.new("L", (w, h), 0)
        ImageDraw.Draw(sl).ellipse([-w * 0.30, -h * 0.70, w * 0.90, h * 0.34], fill=44)
        sheen_img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        sheen_img.putalpha(blur(sl, min(w, h) * 0.13))
        glass = Image.alpha_composite(glass, sheen_img)

    stroke = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(stroke).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius, outline=(255, 255, 255, 255), width=1)
    ramp = ImageChops.invert(Image.linear_gradient("L").resize((w, h), Image.BILINEAR))
    ramp = ramp.point(lambda v: int(22 + v * 0.30))
    stroke.putalpha(ImageChops.multiply(stroke.split()[3], ramp))
    glass = Image.alpha_composite(glass, stroke)

    glass.putalpha(rounded_mask((w, h), radius))
    tile.alpha_composite(glass, (m, m))
    return tile, (x0 - m, y0 - m)


def sample(img: Image.Image, box) -> str:
    """Average colour of a region as #rrggbb (used to match Tk widget backgrounds).

    The box is clamped into the image, so callers may ask about a region that
    is partly or wholly outside it -- scrolled content, for instance -- and get
    the nearest colour instead of an error.
    """
    w, h = img.size
    x0 = max(0, min(w - 1, int(box[0])))
    y0 = max(0, min(h - 1, int(box[1])))
    x1 = max(x0 + 1, min(w, int(box[2])))
    y1 = max(y0 + 1, min(h, int(box[3])))
    r, g, b = img.convert("RGB").crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX).getpixel((0, 0))
    return "#%02x%02x%02x" % (r, g, b)


def mix(hex_color: str, rgb, t: float) -> str:
    """Blend a #rrggbb string toward an rgb tuple."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return "#%02x%02x%02x" % (
        int(r + (rgb[0] - r) * t), int(g + (rgb[1] - g) * t), int(b + (rgb[2] - b) * t))


# ------------------------------------------------------------------ icons ---
def icon(name: str, size: int = 18, color=(238, 242, 255, 255), width: float = 1.8) -> Image.Image:
    """Small stroked glyph, drawn at 4x and downsampled."""
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(1, int(width * SS))

    def L(*pts):
        d.line([(p[0] * n, p[1] * n) for p in pts], fill=color, width=w, joint="curve")

    def E(x0, y0, x1, y1, fill=None, out=True):
        d.ellipse([x0 * n, y0 * n, x1 * n, y1 * n], fill=fill,
                  outline=color if out else None, width=w)

    def P(*pts):
        d.polygon([(p[0] * n, p[1] * n) for p in pts], fill=color)

    def RR(x0, y0, x1, y1, r, fill=None, out=True):
        d.rounded_rectangle([x0 * n, y0 * n, x1 * n, y1 * n], r * n, fill=fill,
                            outline=color if out else None, width=w)

    if name == "download":
        L((.5, .10), (.5, .58))
        P((.29, .44), (.71, .44), (.50, .74))
        L((.16, .86), (.84, .86))
    elif name == "plus":
        L((.5, .18), (.5, .82))
        L((.18, .5), (.82, .5))
    elif name == "clipboard":
        RR(.24, .16, .76, .88, .10)
        RR(.38, .07, .62, .25, .05, fill=color, out=False)
        L((.36, .48), (.64, .48))
        L((.36, .64), (.58, .64))
    elif name == "folder":
        RR(.10, .26, .90, .82, .09)
        L((.10, .34), (.42, .34), (.50, .20), (.10, .20))
    elif name == "play":
        P((.30, .16), (.84, .50), (.30, .84))
    elif name == "pause":
        RR(.26, .18, .42, .82, .05, fill=color, out=False)
        RR(.58, .18, .74, .82, .05, fill=color, out=False)
    elif name == "x":
        L((.24, .24), (.76, .76))
        L((.76, .24), (.24, .76))
    elif name == "check":
        L((.20, .52), (.42, .74), (.80, .26))
    elif name == "refresh":
        d.arc([.16 * n, .16 * n, .84 * n, .84 * n], 35, 320, fill=color, width=w)
        P((.70, .02), (.97, .28), (.60, .34))
    elif name == "trash":
        L((.14, .26), (.86, .26))
        RR(.24, .26, .76, .88, .08)
        L((.40, .15), (.60, .15))
        L((.42, .42), (.42, .74))
        L((.58, .42), (.58, .74))
    elif name == "chevron":
        L((.26, .40), (.50, .64), (.74, .40))
    elif name == "chevron_up":
        L((.26, .62), (.50, .38), (.74, .62))
    elif name == "music":
        L((.40, .78), (.40, .20), (.82, .12), (.82, .68))
        E(.20, .64, .44, .86, fill=color, out=False)
        E(.62, .54, .86, .76, fill=color, out=False)
    elif name == "film":
        RR(.10, .22, .90, .78, .08)
        L((.34, .22), (.34, .78))
        L((.66, .22), (.66, .78))
    elif name == "log":
        L((.18, .26), (.82, .26))
        L((.18, .44), (.82, .44))
        L((.18, .62), (.66, .62))
        L((.18, .80), (.50, .80))
    elif name == "external":
        L((.44, .20), (.20, .20), (.20, .80), (.80, .80), (.80, .56))
        L((.52, .48), (.84, .16))
        L((.58, .16), (.84, .16), (.84, .42))
    elif name == "spark":
        P((.50, .08), (.60, .38), (.90, .48), (.60, .58), (.50, .90), (.40, .58),
          (.10, .48), (.40, .38))
    elif name == "pencil":
        L((.18, .82), (.26, .58), (.70, .14), (.86, .30), (.42, .74))
        L((.18, .82), (.42, .74))
        L((.62, .22), (.78, .38))
    elif name == "link":
        d.arc([.06 * n, .34 * n, .54 * n, .66 * n], 40, 320, fill=color, width=w)
        d.arc([.46 * n, .34 * n, .94 * n, .66 * n], 220, 140, fill=color, width=w)
        L((.36, .50), (.64, .50))
    return img.resize((size, size), Image.LANCZOS)


_LOGO_CACHE: dict[int, Image.Image] = {}


def _logo_file() -> str | None:
    """The logo shipped with the app, whether running from source or packaged."""
    import sys
    roots = [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        roots.insert(0, bundled)
    for root in roots:
        path = os.path.join(root, "docs", "Easy-dlp_Logo.png")
        if os.path.isfile(path):
            return path
    return None


def app_icon(size: int = 64) -> Image.Image:
    """The app's mark, at whatever size is asked for.

    The drawn tile below was the icon before there was a logo, and it stays as
    the fallback so the app still has a face when run from a copy without the
    artwork.
    """
    if size not in _LOGO_CACHE:
        path = _logo_file()
        _LOGO_CACHE[size] = None
        if path:
            try:
                logo = Image.open(path).convert("RGBA")
                _LOGO_CACHE[size] = logo.resize((size, size), Image.LANCZOS)
            except Exception:
                _LOGO_CACHE[size] = None
    if _LOGO_CACHE[size] is not None:
        return _LOGO_CACHE[size].copy()

    n = size * 2
    tile = gradient((n, n), (124, 92, 255), (35, 211, 232))
    tile.putalpha(rounded_mask((n, n), int(n * 0.24)))
    sl = Image.new("L", (n, n), 0)
    ImageDraw.Draw(sl).ellipse([-n * .3, -n * .7, n * .9, n * .34], fill=70)
    sheen = Image.new("RGBA", (n, n), (255, 255, 255, 0))
    sheen.putalpha(ImageChops.multiply(blur(sl, n * 0.12), tile.split()[3]))
    tile = Image.alpha_composite(tile, sheen)
    g = icon("download", int(n * 0.60), (10, 8, 22, 255), width=2.6)
    tile.alpha_composite(g, ((n - g.size[0]) // 2, (n - g.size[1]) // 2))
    return tile.resize((size, size), Image.LANCZOS)
