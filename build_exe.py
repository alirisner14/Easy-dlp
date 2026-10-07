"""Package the app into a single double-clickable .exe.

    python build_exe.py

Produces dist/Easy-dlp.exe.  Build files are kept out of the
project folder; only dist/ is written here.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "Easy-dlp"
LOGO = ROOT / "docs" / "Easy-dlp_Logo.ico"     # the real logo, when there is one
ICON = ROOT / "docs" / "app.ico"               # otherwise one drawn from code


def ensure_icon() -> Path:
    """The icon for the executable: the logo if present, else drawn from code.

    This used to redraw app.ico on every build, which quietly threw away any
    icon put there by hand - so a proper logo lives under its own name and is
    never overwritten.
    """
    if LOGO.is_file():
        return LOGO
    ICON.parent.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    from evd import graphics as G

    sizes = [16, 24, 32, 48, 64, 128, 256]
    G.app_icon(256).save(ICON, format="ICO", sizes=[(s, s) for s in sizes])
    return ICON


VENDOR = ROOT / "vendor"        # yt-dlp.exe and ffmpeg.exe for a release build
NEEDED = ("yt-dlp.exe", "ffmpeg.exe")


def collect_tools() -> list[str]:
    """The command line tools a release build carries inside it.

    Someone who downloads the app has no reason to already have yt-dlp and
    ffmpeg, and "install these two command line programs first" is not a
    product. Drop them in vendor/ and they travel inside the exe; leave it
    empty and the build still works, falling back to whatever is on PATH -
    which is what you want while developing, and not what you want to sell.
    """
    if not VENDOR.is_dir():
        print("vendor/ is empty - this build will need yt-dlp and ffmpeg on "
              "PATH. See RELEASING.md before shipping it to anyone.")
        return []
    args = []
    for name in NEEDED:
        path = VENDOR / name
        if path.is_file():
            args += ["--add-binary", "%s%s." % (path, os.pathsep)]
            print("bundling %s (%.1f MB)" % (name, path.stat().st_size / 1048576))
        else:
            print("vendor/%s is missing - the build will fall back to PATH "
                  "for it" % name)
    return args


def main() -> int:
    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("PyInstaller is needed:  pip install pyinstaller", file=sys.stderr)
            input("\nPress Enter to exit...")
            return 2

    icon = ensure_icon()
    work = Path(tempfile.mkdtemp(prefix="evd-build-"))
    tools = collect_tools()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",          # a single file to double-click
        "--windowed",         # no console window behind the GUI
        "--name", NAME,
        "--icon", str(icon),
        # the window and taskbar icon are drawn from this at run time, so it
        # has to travel inside the packaged app as well
        "--add-data", "%s%sdocs" % (ROOT / "docs" / "Easy-dlp_Logo.png", os.pathsep),
        *tools,
        # the collector snippets, which the Identify window copies out
        *[arg for js in sorted((ROOT / "tools").glob("*.js"))
          for arg in ("--add-data", "%s%stools" % (js, os.pathsep))],
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(work / "build"),
        "--specpath", str(work),
        str(ROOT / "app.py"),
    ]
    print(" ".join(cmd))
    
    # Force the subprocess to run in the project directory, not System32
    result = subprocess.run(cmd, cwd=str(ROOT))
    
    shutil.rmtree(work, ignore_errors=True)

    exe = ROOT / "dist" / (NAME + ".exe")
    if result.returncode == 0 and exe.exists():
        print("\nBuilt %s (%.1f MB)" % (exe, exe.stat().st_size / 1048576))
        input("\nPress Enter to exit...")
        return 0
    print("\nBuild failed", file=sys.stderr)
    input("\nPress Enter to exit...")
    return result.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())