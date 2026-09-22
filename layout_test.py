"""The left column is laid out twice - once to size the panel, once to draw
on it - and the two can drift apart.

Every card is a frosted tile painted at a height worked out before anything is
drawn on it. Add a control and forget the height, and the last thing in the
card is quietly clipped or floats past the glass. Start Download is the last
thing in the options card, so it is exactly what would go missing.

This builds the real window, transparent and against a scratch APPDATA, and
checks the two agree in both states of the Advanced section.
"""
import os
import sys
import tempfile

# a window test reads and writes the same settings.json and queue.json as the
# installed app, so point it somewhere harmless first
os.environ["APPDATA"] = os.path.join(tempfile.gettempdir(), "evd-layout-sandbox")
os.makedirs(os.environ["APPDATA"], exist_ok=True)

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from evd import theme as T, ui as U

fails = []


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg, flush=True)
    if not cond:
        fails.append(msg)


app = U.App()
# mapped, so the canvas has a real size, but fully transparent, so nothing
# appears on anybody's screen
app.root.attributes("-alpha", 0.0)
app.root.geometry("1280x800+40+40")
app.root.update()
app.root.update()

for advanced in (False, True):
    print("%d. advanced options %s" % (1 + advanced, "open" if advanced else "closed"),
          flush=True)
    app.advanced = advanced
    app.rebuild()
    app.root.update()

    ly = app.left_origin[1]
    bottom = U.HEADER_H + app._add_card_height() + T.GAP + app._options_card_height()
    start = app.b_start_dl
    start_top, start_bottom = start.y + ly, start.y + ly + start.h
    folder_bottom = app.f_outdir.y + ly + app.f_outdir.h

    ok(start_bottom <= bottom,
       "Start Download ends inside the card it is drawn on (%d <= %d)"
       % (start_bottom, bottom))
    ok(bottom - start_bottom <= 20,
       "and the card is not padded out well past it (%d px left)"
       % (bottom - start_bottom))
    ok(start_top > folder_bottom,
       "the folder the files land in is read before the button, not after it "
       "(%d > %d)" % (start_top, folder_bottom))
    ok(app.left_content_h >= start_bottom - ly,
       "the column scrolls far enough to reach the button (%d >= %d)"
       % (app.left_content_h, start_bottom - ly))

    lowest = max(w.y + w.h for w in app.left_widgets) + ly
    ok(lowest <= bottom,
       "nothing at all is left hanging past the glass (%d <= %d)" % (lowest, bottom))

app.root.destroy()
print(("\nALL PASS" if not fails else "\n%d FAILED" % len(fails)), flush=True)
sys.exit(1 if fails else 0)
