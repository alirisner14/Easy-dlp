"""A copied course page should stage the whole course, named and numbered."""
import os
import sys

sys.path.insert(0, "C:/EasyVideoDownloader")
import sandbox                       # noqa: F401  (redirects APPDATA)
from evd import pagescan, downloader as D

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8", errors="replace") as fh:
        return fh.read()


# The pages this checks against are saved course pages from an account, so
# they carry an email address and are deliberately not in the repository.
# Save one yourself (Ctrl+U, Ctrl+A, Ctrl+C into a file) to run the lot.
if not os.path.isdir(FIX) or not os.listdir(FIX):
    print("no saved pages in %s - skipping.\n"
          "Save a course page there as course-index.html to run this."
          % FIX, flush=True)
    raise SystemExit(0)


print("1. the real course page (53 lessons, saved from the site)", flush=True)
rows = pagescan.lessons_from_page(read("course-index.html"))
ok(len(rows) == 53, "every lesson found (%d)" % len(rows))
ok(len(set(u for u, _ in rows)) == 53, "no url repeated")
ok(len(set(n for _, n in rows)) == 53, "no two files would collide")
ok(all(n for _, n in rows), "every one is named")
ok(all(u.endswith("/playlist.m3u8") for u, _ in rows),
   "urls point at the master playlist, not one fixed size")
ok(rows[0][1] == "1.01_CharacterDesignIntroduction",
   "first is numbered and titled (%r)" % rows[0][1])
ok(rows[52][1] == "3.17_FinalThoughts", "last one too (%r)" % rows[52][1])
ok([n for _, n in rows][20:22] == ["1.21_FinalThoughts", "2.01_Introduction"],
   "module boundaries are right")
ok(sum(1 for _, n in rows if n.endswith("FinalThoughts")) == 3,
   "the three identical titles are kept apart by their numbers")
ok(sorted(n for _, n in rows) == [n for _, n in rows],
   "they sort into course order in the folder")
print("     %s" % rows[0][1], flush=True)
print("     %s" % rows[17][1], flush=True)

print("2. a lesson page works too, markup and embedded json", flush=True)
rows = pagescan.lessons_from_page(read("lesson-page.html"))
names = [n for _, n in rows]
ok(len(rows) == 5, "sidebar and json merged without duplicates (%d)" % len(rows))
ok("1.01_CharacterDesignIntroduction" in names, "sidebar rows are read")
ok("1.10_ExploreFeatures" in names, "a two digit lesson number survives")
ok("1.18_CreateABlurredBackground" in names,
   "the playing lesson still gets its number, from the json (%r)"
   % [n for n in names if "Blurred" in n])
ok("2.14_PaintingTheBackground" in names, "json only rows are picked up as well")
ok(not any("0.05" in n for n in names), "a css class like mt-0.5 is not a lesson number")

print("3. it stays out of the way of ordinary pasting", flush=True)
ok(pagescan.lessons_from_page("") == [], "empty text")
ok(pagescan.lessons_from_page("https://example.com/a.m3u8 | Lesson 1") == [],
   "a plain list of links is left for the normal parser")
ok(pagescan.lessons_from_page("<html><body>no video here</body></html>") == [],
   "an unrelated page")
plain = "https://example.com/a.m3u8 | Lesson 1\nhttps://example.com/b.m3u8 | Lesson 2"
ok(len(D.parse_entries(plain)) == 2, "and that parser still handles it")

print("4. names are safe to use as file names", flush=True)
nasty = ('<a href="/l/1"><span>2.3</span><img src="https://vz-x.b-cdn.net/'
         '11111111-2222-3333-4444-555555555555/thumbnail.jpg">'
         '<p>Colour: red / blue &amp; "grey"?</p></a>')
rows = pagescan.lessons_from_page(nasty)
ok(len(rows) == 1, "found it")
name = rows[0][1]
ok(not any(c in name for c in '<>:"/\\|?*'), "no characters Windows refuses (%r)" % name)
ok(name == "2.03_ColourRedBlueGrey", "entities decoded and joined up (%r)" % name)
ok(name.startswith("2.03_"), "still numbered (%r)" % name)

print("5. no resolution is baked into the address", flush=True)
rows = pagescan.lessons_from_page(read("lesson-page.html"))
ok(not any("/720p/" in u or "/1080p/" in u for u, _ in rows),
   "a video published without per-size paths still works, and the Quality "
   "setting decides the size")

print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
