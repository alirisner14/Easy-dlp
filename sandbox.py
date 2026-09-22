"""Point the tests at a scratch %APPDATA% before anything reads the real one.

`evd.config` works out where settings.json, queue.json and activity.log live
at import time, so this has to run first - import it above `from evd import
...` and nothing a test does can reach the installed app's files.

This used to be a line in each test's docstring saying to set APPDATA first,
which is exactly as much protection as it sounds: a test run without it
overwrites a real queue, and a queue overwritten while the app is closed is
the record of what was still to download.
"""
import os
import tempfile

DIR = os.path.join(tempfile.gettempdir(), "evd-test-sandbox")
os.makedirs(DIR, exist_ok=True)
os.environ["APPDATA"] = DIR
# on anything but Windows, config falls back to ~/.config
os.environ["XDG_CONFIG_HOME"] = DIR
os.environ["HOME"] = DIR
