"""Identify names the right way in for each kind of thing pasted.

Run: python identify_test.py
"""
import sandbox  # noqa: F401  (keeps the test out of the real AppData)
from evd import identify as ID

failures = 0


def ok(cond, label):
    global failures
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures += 1


def check(text, kind, snippet="", label="", playlists=True):
    a = ID.identify(text, playlists)
    ok(a.kind == kind and a.snippet == snippet,
       "%s -> %s %s (%s: %s)" % (label, kind, snippet, a.kind, a.headline))
    return a


G = "11111111-2222-3333-4444-555555555555"
H = "66666666-7777-8888-9999-000000000000"


def card(guid, meta, title):
    return ('<li><a href="/courses/c/lessons/%s"><img src="https://vz-1.b-cdn.net/%s/'
            'thumbnail.jpg"/><p>%s</p><p>%s</p></a></li>' % (guid, guid, meta, title))


# -- links ------------------------------------------------------------------
check("https://www.youtube.com/watch?v=abc123", ID.PASTE_LINK, label="youtube video")
a = check("https://www.youtube.com/playlist?list=PL123", ID.PASTE_LINK, label="playlist")
ok("Playlists is on" in a.detail, "playlist with Playlists on says it will follow it")
a = check("https://www.youtube.com/watch?v=a&list=PL1", ID.PASTE_LINK,
          label="watch-in-playlist, Playlists off", playlists=False)
ok("Turn on Playlists" in a.detail, "says to turn Playlists on")
check("https://studio.freya.courses/courses/x/lessons/%s" % G, ID.SNIPPET, "bunny",
      label="a Freya lesson address")
check("https://player.vimeo.com/video/123456789", ID.PASTE_LINK, "vimeo", label="vimeo player")
check("https://example.com/files/clip.mp4", ID.PASTE_LINK, label="direct file")
check("https://example.com/downloads/brushes.zip", ID.PASTE_LINK, label="handout")
check("https://some-course-site.com/lesson/4", ID.COPY_SOURCE, label="unknown site")
check("just some words", ID.UNKNOWN, label="not a link")
check("", ID.UNKNOWN, label="empty")

# -- page source --------------------------------------------------------------
open_page = "<html><body><ul>" + card(G, "1.1", "Intro") + card(H, "1.2", "Next") + "</ul></body></html>"
a = check(open_page, ID.PASTE_PAGE, label="bunny course page")
ok("2 lessons" in a.detail, "counts the lessons")
signed = ("https://vz-1.b-cdn.net/bcdn_token=x\\u0026expires=1\\u0026token_path=%%2F%s%%2F/%s/playlist.m3u8"
          % (G, G))
check(open_page.replace("</body>", '<script>"%s"</script></body>' % signed),
      ID.SNIPPET, "bunny", label="bunny page with locked lessons")
check('<html><body><iframe src="https://player.vimeo.com/video/987654321"></iframe></body></html>',
      ID.SNIPPET, "vimeo", label="vimeo course page")
check('<html><body><script src="https://customer-x.cloudflarestream.com/abc/iframe"></script>'
      '<iframe src="https://player.vimeo.com/video/987654321"></iframe></body></html>',
      ID.SNIPPET, "cloudflare", label="cloudflare page beats a stray vimeo mention")
check('<html><body><div class="wistia_embed"></div></body></html>', ID.PASTE_LINK,
      label="wistia page")
check('<html><body><iframe src="https://www.youtube.com/embed/xyz"></iframe></body></html>',
      ID.PASTE_LINK, label="page embedding youtube")
check('<html><body><div class="downloads"><a href="https://example.com/f/sheet.pdf">Worksheet</a></div></body></html>',
      ID.PASTE_PAGE, label="page with only handouts")
check("<html><body><p>Hello</p></body></html>", ID.UNKNOWN, label="page with nothing")

# -- every snippet the advice can name is really there -------------------------
for key in ID.SNIPPETS:
    ok(ID.snippet_text(key).lstrip().startswith("/*"), "snippet %s loads" % key)

print("ALL PASS" if not failures else "%d FAILED" % failures)
raise SystemExit(1 if failures else 0)
