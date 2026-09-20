"""Turn a copied course page into a staged batch.

Collecting these links by hand means opening DevTools once per lesson. The
course pages already carry everything needed: each lesson's video id sits in
the url of its own thumbnail, so a single page yields the whole course. Both
page shapes are handled - the ones that render the list into the markup, and
the ones that also ship it as json.
"""
from __future__ import annotations

import html as _html
import re

# the video id, as it appears in .../<id>/thumbnail.jpg and .../<id>/preview.webp
_MEDIA = re.compile(
    r"(?P<host>[A-Za-z0-9.-]*b-cdn\.net)/"
    r"(?P<guid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/")

_ANCHOR = re.compile(r"<a\b", re.I)
_ANCHOR_END = re.compile(r"</a\s*>", re.I)
_ARIA = re.compile(r'aria-label="(?:Play\s+)?([^"]+)"', re.I)
_PARA = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
_TAGS = re.compile(r"<[^>]*>")
_SPACES = re.compile(r"\s+")
# "Lesson 1.1" on the course page, a bare "1.18" in a lesson page's sidebar
_NUMBER = re.compile(r"(?:Lesson\s+)?\b(\d{1,2})\.(\d{1,2})\b(?!\d)")
_DURATION = re.compile(r"^\d{1,2}:\d{2}$")

# lesson pages embed the same list as json, which also carries the numbering
_JSON = re.compile(
    r'"title":"(?P<title>(?:[^"\\]|\\.)*)"\s*,\s*"thumbnail_url":"[^"]*?'
    r'(?P<host>[A-Za-z0-9.-]*b-cdn\.net)/(?P<guid>[0-9a-fA-F-]{36})/[^"]*"'
    r'(?P<rest>.{0,400}?)"lesson_number":(?P<lesson>\d+)', re.S)
_MODULE = re.compile(r'"module_number":(\d+)')

_SECTION = re.compile(r"^\s*(\d{1,2})\.\d{1,2}(?!\d)")


def section_of(name: str) -> str:
    """The "1" in "1.04 - Find Inspiration", or nothing if it is not numbered."""
    match = _SECTION.match(name or "")
    return match.group(1) if match else ""


def sections(names) -> list[str]:
    """Which sections a staged list covers, in the order they appear."""
    found = []
    for name in names:
        mark = section_of(name)
        if mark and mark not in found:
            found.append(mark)
    return found


def _plain(fragment: str) -> str:
    """Markup in, readable one-line text out."""
    return _SPACES.sub(" ", _html.unescape(_TAGS.sub(" ", fragment))).strip()


_WORD = re.compile(r"[A-Za-z0-9]+")


def _clean(title: str) -> str:
    """One word, the way these files have always been named.

    "Create a blurred background" becomes "CreateABlurredBackground", which
    also sidesteps every character Windows will not take in a file name.
    """
    words = _WORD.findall(_html.unescape(title))
    return "".join(w[0].upper() + w[1:] for w in words)[:110]


def _numbered(module, lesson, title: str) -> str:
    """Section.Lesson_Title, zero padded so 2.03 sorts ahead of 2.10."""
    try:
        return "%d.%02d_%s" % (int(module), int(lesson), title)
    except (TypeError, ValueError):
        return title


_NUMBERED = re.compile(r"^\d{1,2}\.\d{2}_.")


def _rank(name: str) -> int:
    """Numbered beats named, named beats nothing."""
    if _NUMBERED.match(name):
        return 2
    return 1 if name else 0


def _from_anchors(text: str) -> list[tuple[str, str, str]]:
    """(guid, host, name) for every lesson link in the markup, in page order."""
    found = []
    for block in _ANCHOR.split(text)[1:]:
        end = _ANCHOR_END.search(block)
        card = block[:end.start()] if end else block[:4000]
        media = _MEDIA.search(card)
        if not media:
            continue
        aria = _ARIA.search(card)
        title = _plain(aria.group(1)) if aria else ""
        if not title:
            # otherwise the title is the first paragraph that is neither the
            # running time nor the lesson number
            for para in (_plain(p) for p in _PARA.findall(card)):
                if para and not _DURATION.match(para) and not _NUMBER.fullmatch(para):
                    title = para
                    break
        if not title:
            continue
        # read the numbering from the text, never from the markup: class
        # names like "mt-0.5" look exactly like a lesson number
        number = _NUMBER.search(_plain(card))
        # tidy the title first: cleaning the finished name would take the
        # dot out of "1.01"
        title = _clean(title)
        name = _numbered(number.group(1), number.group(2), title) if number else title
        found.append((media.group("guid").lower(), media.group("host"), name))
    return found


def _from_json(text: str) -> list[tuple[str, str, str]]:
    """The same thing again, for pages that ship the list as json."""
    found = []
    for match in _JSON.finditer(text):
        title = _plain(match.group("title"))
        if not title:
            continue
        module = _MODULE.search(match.group("rest"))
        name = _numbered(module.group(1) if module else None,
                         match.group("lesson"), _clean(title))
        found.append((match.group("guid").lower(), match.group("host"), name))
    return found


def lessons_from_page(text: str, quality: str = "720p") -> list[tuple[str, str]]:
    """Every lesson on a copied course page, as (url, name) pairs.

    Returns nothing at all when the text is not a page we recognise, which
    lets the caller fall back to reading it as a plain list of links.
    """
    if not text or "b-cdn.net" not in text:
        return []
    # the json arrives escaped inside a <script>, so read it unescaped
    flat = text.replace('\\"', '"').replace("\\/", "/")

    order: list[str] = []
    best: dict[str, tuple[str, str]] = {}
    for guid, host, name in _from_anchors(flat) + _from_json(flat):
        if guid not in best:
            order.append(guid)
            best[guid] = (host, name)
        elif _rank(name) > _rank(best[guid][1]):
            # the lesson being played shows a play icon where its number
            # would be, so let a numbered copy of it win
            best[guid] = (host, name)
    return [("https://%s/%s/%s/video.m3u8" % (best[g][0], g, quality), best[g][1])
            for g in order]
