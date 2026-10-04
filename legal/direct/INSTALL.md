# Installing Easy-dlp

> Use this text in three places: the purchase confirmation email, the
> download page, and as `READ-ME-FIRST.txt` beside the installer. Customers
> who are told about the warning *before* they see it treat it as expected.
> Customers who meet it cold assume they have been sold malware.

---

## Windows will warn you about this. Here is why, and what to do.

When you run the installer, Windows will probably show a blue box saying
**"Windows protected your PC"** or **"Microsoft Defender SmartScreen prevented
an unrecognised app from starting"**.

**This is expected, and it does not mean anything is wrong.**

SmartScreen shows that warning for any application it has not seen many
people install yet. It is a popularity check, not a virus scan. Easy-dlp is
made by one person rather than a large company, so it starts with no
installation history and gets flagged until enough people have installed it.
The warning will stop appearing on its own as that history builds.

### How to continue

1. Click **More info** in the blue box.
2. Click **Run anyway**.

![More info, then Run anyway]

That is all. The installer then runs normally and takes about a minute.

### If you would rather check first

Reasonable — you should be suspicious of software that asks you to click past
a security warning. Two ways to satisfy yourself:

- **Check the file hash.** The SHA-256 for this release is published at
  https://ontherisedigital.lemonsqueezy.com/downloads. In PowerShell:
  ```powershell
  Get-FileHash .\Easy-dlp-Setup-1.1.0.exe -Algorithm SHA256
  ```
  If it matches, the file you have is the file we published.

- **Scan it.** Upload the installer to [VirusTotal](https://www.virustotal.com).
  A handful of engines may flag it; that is normal for installers that bundle
  `yt-dlp`, which some vendors flag purely because downloaders are sometimes
  misused. The majority verdict is the one that matters.

### What gets installed

- **Easy-dlp** itself.
- **yt-dlp** — the open-source tool that performs the downloads.
- **FFmpeg** — the open-source tool that joins video and audio together.

Nothing else. No toolbar, no browser extension, no background service, no
scheduled task, no bundled "offers". Easy-dlp makes no network connection of
its own and sends nothing anywhere. See our
[Privacy Policy](https://ontherisedigital.lemonsqueezy.com/privacy).

It installs to your user folder, so it does not need an administrator
password.

### Uninstalling

Settings → Apps → Installed apps → Easy-dlp → Uninstall. Or use the shortcut
in the Start Menu folder. Your downloaded videos are never touched; they are
in whatever folder you chose.

To remove your settings and queue as well, delete:
```
%APPDATA%\EasyVideoDownloader
```

---

## System requirements

- Windows 10 version 1809 or later, or Windows 11
- 64-bit
- About 150 MB of disk space for the application
- Enough free space wherever you save videos — a course can be many gigabytes

## First run

Easy-dlp opens with an empty staging list. Paste a link, choose where files
should land, and press **Start Download**. The **Save to** folder sits
directly above the button on purpose — set it before you press Start.

Full instructions are in the help documentation, and the collector scripts
for gathering a whole course at once are in the `tools` folder.

## If something does not work

Email ontherisedigital@gmail.com with:

- what you were trying to download (the kind of site, not necessarily the link)
- what the queue row said
- the contents of **Activity**, which is the raw output of the downloader

That log is the thing that identifies the problem fastest. It lives at
`%APPDATA%\EasyVideoDownloader\activity.log`.
