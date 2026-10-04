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
from urllib.parse import urljoin

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


def lessons_from_page(text: str) -> list[tuple[str, str]]:
    """Every lesson on a copied course page, as (url, name) pairs.

    The address built is the master playlist rather than a fixed resolution.
    Not every video is published with per-resolution paths - plenty answer 404
    on .../720p/video.m3u8 while offering the same 720p inside the master - and
    the master also lets the Quality setting decide, instead of the size being
    fixed here.

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
    return [("https://%s/%s/playlist.m3u8" % (best[g][0], g), best[g][1])
            for g in order]


# --------------------------------------------------------------- resources --
# The worksheets, brush sets and project files that come with a course. Two
# lists, because they carry different risks: a link ending .pdf or .zip is
# the handout it looks like, while a link ending .png is as likely to be the
# site's logo or somebody's avatar.
#
# So images are taken only on evidence: the page marks the link as a
# download, says so in words, or - best of all - puts it inside a section
# plainly meant for downloads. That last one is what stops a course page
# handing over every photograph on it while still collecting the reference
# sheet a lesson attached.
_FILE_EXT = ("pdf", "zip", "rar", "7z", "gz", "tar", "psd", "psb", "ai",
             "eps", "clip", "procreate", "brushset", "brush", "abr", "atn",
             "tpl", "blend", "obj", "fbx", "doc", "docx", "rtf", "xls",
             "xlsx", "csv", "ppt", "pptx", "key", "epub", "mobi", "otf", "ttf")
_IMAGE_EXT = ("png", "jpg", "jpeg", "gif", "webp", "tif", "tiff", "svg", "txt")

# A part of the page given over to downloads. Sites label these consistently
# enough to find: a heading that says so, or a container whose class or id
# does. Everything between it and the end of its section counts as inside.
_AREA_WORDS = (r"download|resource|material|attachment|handout|worksheet"
               r"|freebie|asset|template|course\s*file|project\s*file|extra")
_AREA_OPEN = re.compile(
    r'<(?P<tag>section|div|aside|ul|ol|table|details)\b[^>]*'
    r'(?:class|id|data-[a-z-]+)\s*=\s*"[^"]*(?:' + _AREA_WORDS + r')[^"]*"',
    re.I)
_AREA_HEADING = re.compile(
    r"<(?P<tag>h[1-6]|summary|legend|strong|b)\b[^>]*>(?P<text>.{0,120}?)</(?P=tag)\s*>",
    re.I | re.S)
_SAYS_AREA = re.compile(_AREA_WORDS, re.I)
# how far past a heading its section is taken to run, when nothing closes it
_AREA_REACH = 4000
_BLOCK_CLOSE = re.compile(r"</(?:section|aside|article|main|footer|div)\s*>", re.I)

_HREF = re.compile(r'href\s*=\s*"([^"]+)"', re.I)
_DOWNLOAD_ATTR = re.compile(r'\sdownload(?:\s*=\s*"([^"]*)")?[\s>]', re.I)
_SAYS_DOWNLOAD = re.compile(
    r"download|worksheet|handout|attachment|resource|material|template", re.I)
_BASE = re.compile(r'<base[^>]+href\s*=\s*"([^"]+)"', re.I)
_CANONICAL = re.compile(
    r'<(?:link[^>]+rel\s*=\s*"canonical"|meta[^>]+property\s*=\s*"og:url")'
    r'[^>]+(?:href|content)\s*=\s*"(https?://[^"]+)"', re.I)
# "Download" on its own names nothing; the file has to supply its own name
_ONLY_DOWNLOAD = re.compile(r"^\s*(?:download|get|save)(?:\s+(?:it|file|now))?\s*$", re.I)


def _ext_of(url: str) -> str:
    """The extension of the file a link points at, ignoring any query."""
    tail = url.split("?")[0].split("#")[0].rsplit("/", 1)[-1]
    _, dot, ext = tail.rpartition(".")
    return ext.lower() if dot else ""


def _download_areas(text: str) -> list[tuple[int, int]]:
    """Where in the markup the page keeps its downloads, as (start, end) spans.

    Two ways a site says it: a container named for it, or a heading that
    announces one. A named container is measured to its matching close tag;
    a heading has no container to measure, so its section is taken to run a
    few thousand characters or until the next heading, whichever is sooner.
    """
    spans: list[tuple[int, int]] = []

    for match in _AREA_OPEN.finditer(text):
        tag = match.group("tag")
        start = match.start()
        # walk nested tags of the same name so an inner <div> does not end
        # the section early
        depth, pos, end = 0, match.end(), None
        nest = re.compile(r"<(/?)%s\b" % tag, re.I)
        for step in nest.finditer(text, pos):
            if step.group(1):
                if depth == 0:
                    end = step.end()
                    break
                depth -= 1
            else:
                depth += 1
        spans.append((start, end if end else min(len(text), start + _AREA_REACH)))

    headings = [(m.start(), m.end(), _plain(m.group("text")))
                for m in _AREA_HEADING.finditer(text)]
    for i, (start, end, title) in enumerate(headings):
        if not _SAYS_AREA.search(title):
            continue
        if _in_area(start, spans):
            continue        # a named container already bounds this, and better
        # A heading has nothing to measure, so the section it announces runs
        # until whichever comes first: the next heading, the close of the
        # block it sits in, or a few thousand characters. Without that last
        # bound a "Downloads" heading near the foot of a page would claim
        # everything after it, footer and all.
        stop = min(len(text), end + _AREA_REACH)
        for other_start, _other_end, _other in headings[i + 1:]:
            if other_start > end:
                stop = min(stop, other_start)
                break
        closing = _BLOCK_CLOSE.search(text, end)
        if closing:
            stop = min(stop, closing.start())
        spans.append((end, stop))

    return spans


def _in_area(at: int, spans) -> bool:
    return any(start <= at < end for start, end in spans)


def _page_base(text: str) -> str:
    """Where the page came from, so its relative links can be made whole."""
    for pattern in (_BASE, _CANONICAL):
        match = pattern.search(text)
        if match and match.group(1).startswith("http"):
            return match.group(1)
    return ""


def resources_from_page(text: str, base: str = "") -> list[tuple[str, str]]:
    """Every handout a copied page offers, as (url, name) pairs.

    Only links plainly meant to be downloaded are returned - a file the site
    attached to the lesson, or one the page itself labels as a download.
    Everything else on the page is left alone: the point is the course
    material, not every image the site happens to serve.
    """
    if not text or "<a" not in text.lower():
        return []
    base = base or _page_base(text)
    areas = _download_areas(text)

    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in _ANCHOR.finditer(text):
        at = anchor.start()
        block = text[anchor.end():anchor.end() + 2000]
        end = _ANCHOR_END.search(block)
        card = block[:end.start()] if end else block
        opening, _, inner = card.partition(">")
        href = _HREF.search(opening)
        if not href:
            continue
        url = _html.unescape(href.group(1)).strip()
        if not url or url.startswith(("#", "javascript:", "mailto:", "data:")):
            continue
        if not url.lower().startswith("http"):
            if not base:
                continue                  # nothing to resolve it against
            url = urljoin(base, url)

        attr = _DOWNLOAD_ATTR.search(opening + ">")
        aria = _ARIA.search(opening)
        label = _plain(inner)
        if aria:
            label = (label + " " + _plain(aria.group(1))).strip()

        ext = _ext_of(url)
        if attr and attr.group(1):
            ext = _ext_of(attr.group(1)) or ext
        inside = _in_area(at, areas)
        if ext in _FILE_EXT:
            pass                          # a handout by any reading
        elif ext in _IMAGE_EXT and (attr or inside or _SAYS_DOWNLOAD.search(label)):
            # an image the page offers to save, or one sitting in the part of
            # the page given over to downloads
            pass
        else:
            continue
        if url in seen:
            continue
        seen.add(url)

        # the link's own words name it, and the file name is the fallback -
        # a button that just reads "Download" tells us nothing
        title = "" if _ONLY_DOWNLOAD.match(label) else label
        if not title and attr and attr.group(1):
            title = attr.group(1).rsplit(".", 1)[0]
        if not title:
            title = url.split("?")[0].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        found.append((url, _clean(title) + "." + ext))
    return found


# ------------------------------------------------------------------ markup --
_MARKUP = re.compile(r"<(?:!doctype|html|head|body|script|div|a\s|link\s|meta\s)", re.I)

# a video address, whatever the site hosts it on: a manifest, a plain file,
# or a known player's own page
_MEDIA_URL = re.compile(
    # the host may itself be the player, so the part before it can be empty
    r"""https?://[^\s"'<>\\]*?"""
    r"(?:\.m3u8|\.mpd|\.mp4|\.webm|\.mkv|\.mov"
    r"|player\.vimeo\.com/video/\d+|youtube\.com/embed/[\w-]+"
    r"|youtu\.be/[\w-]+|wistia\.(?:net|com)/[\w/]+"
    r"|cloudflarestream\.com/\w+)"
    r"""[^\s"'<>\\]*""", re.I)


def looks_like_page(text: str) -> bool:
    """Is this a web page, rather than a list of links someone typed?"""
    return bool(text) and bool(_MARKUP.search(text[:4000]))


def media_from_page(text: str) -> list[tuple[str, str]]:
    """Video addresses in a page the lesson scanner could not read.

    Pasting such a page used to fall through to the plain-link parser, which
    takes every http address in the markup - every stylesheet, script, font
    and tracker - and stages a row for each. Several hundred of those lock
    the window up while it draws them, and not one of them is a video. So
    markup is searched for things that actually are video, and nothing else
    is offered.
    """
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    flat = _html.unescape(text.replace("\\/", "/"))
    for match in _MEDIA_URL.finditer(flat):
        url = match.group(0).rstrip(".,);]'\"")
        if url not in seen:
            seen.add(url)
            found.append((url, ""))
    return found
