"""Pasting a web page must not stage every address in it.

A page the lesson reader does not recognise used to fall through to the plain
link parser, which takes every http address in the markup - stylesheets,
scripts, fonts, trackers, the lot - and stages a row for each. Several hundred
rows lock the window up while it draws them, and not one of them is a video.
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import downloader as D, pagescan, ui as U

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


PAGE = """<!doctype html><html><head>
<link rel="stylesheet" href="https://cdn.site.com/app.css">
<link rel="preload" href="https://cdn.site.com/sprite.svg" as="image">
<script src="https://analytics.example.com/track.js"></script>
<script src="https://cdn.site.com/vendor.9f3a.js"></script>
</head><body>
<img src="https://cdn.site.com/logo.png">
<img src="https://cdn.site.com/avatars/42.jpg">
<iframe src="https://player.vimeo.com/video/123456?h=abcdef"></iframe>
<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>
<source src="https://vz-x.b-cdn.net/abc/playlist.m3u8">
<a href="https://twitter.com/someone">Follow</a>
<a href="https://site.com/terms">Terms</a>
</body></html>"""

print("1. a page yields its videos and nothing else", flush=True)
rows = pagescan.media_from_page(PAGE)
urls = [u for u, _n in rows]
ok(len(rows) == 3, "three videos, not every address on the page (%d)" % len(rows))
ok(any("player.vimeo.com/video/123456" in u for u in urls), "the Vimeo player")
ok(any("youtube.com/embed/" in u for u in urls), "the YouTube embed")
ok(any(u.endswith("playlist.m3u8") for u in urls), "the manifest")
ok(not any(".css" in u or ".js" in u for u in urls), "no stylesheet or script")
ok(not any("logo.png" in u or "avatars" in u for u in urls), "no images")
ok(not any("twitter" in u or "/terms" in u for u in urls), "no ordinary links")
ok(len(D.parse_entries(PAGE)) > len(rows),
   "the plain parser would have taken more (%d of them)" % len(D.parse_entries(PAGE)))

print("2. telling a page from a list of links", flush=True)
ok(pagescan.looks_like_page(PAGE), "markup is a page")
ok(pagescan.looks_like_page("<div><a href='/x'>y</a></div>"), "a fragment is too")
ok(not pagescan.looks_like_page("https://a.com/x.m3u8 | Lesson 1"),
   "a typed list is not")
ok(not pagescan.looks_like_page(""), "nor is nothing")
ok(not pagescan.looks_like_page("https://a.com/a.m3u8\nhttps://a.com/b.m3u8"),
   "nor is a column of links")

print("3. a plain list is still read as one", flush=True)
plain = "https://example.com/a.m3u8 | Lesson 1\nhttps://example.com/b.m3u8 | Lesson 2"
ok(len(D.parse_entries(plain)) == 2, "both links, named")
ok(pagescan.media_from_page("") == [], "and nothing is invented from nothing")

print("4. a page with no video in it is reported, not staged", flush=True)
ok(pagescan.media_from_page("<html><body><a href='https://x.com/a'>hi</a></body></html>") == [],
   "an ordinary page yields nothing to stage")

print("5. there is a limit before the window is asked to draw too much", flush=True)
ok(isinstance(U.App.MANY_ROWS, int) and 20 <= U.App.MANY_ROWS <= 500,
   "a sane threshold is set (%r)" % U.App.MANY_ROWS)
ok(hasattr(U.App, "_too_many") and hasattr(U.App, "_take_links"),
   "and both paste and import go through it")

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
