"""Course pages whose video host signs each address.

Run: python signed_test.py
"""
from evd import pagescan

failures = 0


def ok(cond, label):
    global failures
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures += 1


HOST = "https://vz-test-1.b-cdn.net"
A = "11111111-2222-3333-4444-555555555555"
B = "66666666-7777-8888-9999-000000000000"


def card(guid, meta, title):
    return ('<li><a href="/courses/c/lessons/%s"><div><img src="%s/%s/thumbnail.jpg"/>'
            '</div><div><p class="tabular-nums">%s</p><p>%s</p></div></a></li>'
            % (guid, HOST, guid, meta, title))


SIGNED_A = ("%s/bcdn_token=abc\\u0026expires=1\\u0026token_path=%%2F%s%%2F/%s/playlist.m3u8"
            % (HOST, A, A))
page = ("<ul>" + card(A, "1.5<!-- --> \u00b7 31:30", "Building Your First Earrings")
        + card(B, "2.1 \u00b7 21:22", "Rings") + "</ul>"
        + '<script>self.push("{\\"src\\":\\"' + SIGNED_A + '\\"}")</script>')

rows = pagescan.lessons_from_page(page)
ok([n for _u, n in rows] == ["1.05_BuildingYourFirstEarrings"],
   "number and running time on one line are not taken for the title: %r" % rows)
ok(rows and rows[0][0].startswith(HOST + "/bcdn_token=abc&expires=1&token_path=")
   and rows[0][0].endswith("/%s/playlist.m3u8" % A),
   "the signed address is used, unescaped")
ok(pagescan.locked_lessons(page) == 1, "the unsigned lesson is reported, not staged")

plain = page.split("<script>")[0]
rows = pagescan.lessons_from_page(plain)
ok([n for _u, n in rows] == ["1.05_BuildingYourFirstEarrings", "2.01_Rings"],
   "a page with no signatures still gives every lesson")
ok(rows[1][0] == "%s/%s/playlist.m3u8" % (HOST, B), "unsigned address unchanged")
ok(pagescan.locked_lessons(plain) == 0, "nothing locked when nothing is signed")

print("ALL PASS" if not failures else "%d FAILED" % failures)
raise SystemExit(1 if failures else 0)
