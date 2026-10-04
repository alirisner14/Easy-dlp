# Third-party licences

Easy-dlp includes and relies on the work of others. Each component below
keeps its own licence, which governs that component regardless of anything in
the Easy-dlp EULA. Nothing in our EULA takes away a right these licences give
you.

**This file must ship with the application** — in the installer, in the
install folder, and reachable from the About box. Including the licence text
is a condition of distributing these components, not a courtesy.

> **Before release:** download the full licence text for each entry into
> `legal/licences/` and confirm the version numbers match what you bundled.
> `yt-dlp --version` and `ffmpeg -version` print them.

---

## yt-dlp

Performs the downloads. Version bundled: **[VERSION]**
<https://github.com/yt-dlp/yt-dlp>

Released into the public domain under **the Unlicense**. No obligations, no
attribution required. It is credited here because it does the real work.

---

## FFmpeg

Joins video and audio streams, converts audio, embeds thumbnails and
metadata. Version bundled: **[VERSION]**
<https://ffmpeg.org>

Licensed under the **GNU Lesser General Public License, version 2.1 or
later**.

Three things we must state, and do:

1. **FFmpeg is unmodified.** We ship an official build exactly as published.
2. **FFmpeg runs as a separate program.** Easy-dlp does not link against it;
   `yt-dlp` launches `ffmpeg.exe` as its own process.
3. **You are entitled to the source code.** It is at
   <https://ffmpeg.org/download.html>, and we will supply the exact source
   for the build we ship on request to [SUPPORT EMAIL], at no charge.

You may replace the `ffmpeg.exe` we supply with your own build. Put it in the
install folder, or on your `PATH`, and the application will use it.

> ⚠️ **Ship an LGPL build, not a GPL one.** The widely-linked FFmpeg builds
> are GPL because they include GPL-licensed encoders. Distributing a GPL
> FFmpeg with a paid, closed-source application is a licence violation.
> BtbN publishes LGPL builds marked `-lgpl`:
> <https://github.com/BtbN/FFmpeg-Builds/releases>
> Verify with `ffmpeg -version` — the banner prints the configuration, and an
> LGPL build will not list `--enable-gpl`.

---

## Python

Runs the application. Version bundled: **[VERSION]**
<https://www.python.org>

Licensed under the **Python Software Foundation License Version 2**, a
permissive licence compatible with commercial distribution. Requires that the
PSF copyright notice be retained.

---

## Pillow

Draws the interface — the frosted panels, the icons, the logo.
Version bundled: **[VERSION]** — <https://python-pillow.org>

Licensed under the **MIT-CMU licence**. Permissive; requires the copyright
notice and permission notice be included.

---

## Tcl/Tk

Provides the window and the canvas everything is drawn on.
Version bundled: **[VERSION]** — <https://www.tcl.tk>

Licensed under a **BSD-style licence**. Permissive; requires the copyright
notice be retained.

---

## PyInstaller

Used to build the single-file executable. Its bootloader is included in the
shipped binary.
<https://pyinstaller.org>

The bootloader is **GPL v2 with a linking exception** that explicitly permits
bundling proprietary applications. The exception is what makes commercial
PyInstaller distribution lawful — PyInstaller itself is not otherwise part of
the product.

---

## Easy-dlp itself

Copyright © 2026 Alison Risner, trading as On the Rise Digital.
All rights reserved. Licensed, not sold — see [EULA.md](EULA.md).
