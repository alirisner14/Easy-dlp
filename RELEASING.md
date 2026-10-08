# Releasing Easy-dlp

Everything between a working build and something a stranger can pay for and
install. Read **Before you sell it** first — two items there decide whether the
rest is worth doing.

## Before you sell it

### The app cannot work alone

Easy-dlp drives `yt-dlp`, and `yt-dlp` needs `ffmpeg` to merge streams, embed
thumbnails and convert audio. On your machine both came from WinGet. A customer
has neither, and without them the window opens and every download fails with
`yt-dlp was not found on PATH`.

A release build therefore carries both inside it. Put them in `vendor/` and
`build_exe.py` bundles them:

```bash
mkdir -p vendor
```

- **yt-dlp** — `yt-dlp.exe` from <https://github.com/yt-dlp/yt-dlp/releases/latest>
  (~17 MB). Licence: Unlicense, public domain. No obligations.
- **ffmpeg** — a Windows build from <https://www.gyan.dev/ffmpeg/builds/> or
  <https://github.com/BtbN/FFmpeg-Builds/releases>. Take `ffmpeg.exe` only
  (~80 MB); you do not need `ffplay` or `ffprobe`.

`vendor/` is in `.gitignore` — these are fetched per release, not committed.

**Which ffmpeg build matters.** The common builds are GPL, because they include
GPL-licensed encoders. Shipping a GPL ffmpeg alongside your code makes the
combined work GPL, which is incompatible with selling it under a closed
licence. Two ways out:

1. Ship an **LGPL** build (BtbN publishes these as `*-lgpl`). LGPL lets you
   distribute a proprietary app beside it, provided ffmpeg stays a separate
   executable — which it is here, since yt-dlp shells out to it — and you
   include the LGPL text and say where to get the source.
2. Do not bundle ffmpeg; detect it and offer a download link on first run.
   Simpler legally, worse as a product.

Either way, put the licence texts for yt-dlp and ffmpeg in the installer and in
an **About → Licences** screen. That is a condition of distributing them, not
a nicety.

### The Microsoft Store is a real risk for this app

I checked the current policies rather than guessing. Three apply directly:

- **10.2.4** — an app may depend on non-integrated software only if the
  dependency is disclosed at the top of the description *and that software is
  in the Store*. yt-dlp is not. The way to comply is what we now do: bundle it
  so it is "fully contained in your app package".
- **10.1.6 / 10.2** — if your product "uses, accesses, monetizes access to, or
  displays content from a third-party service, ensure that you are specifically
  permitted to do so under the service's terms of use."
- **11.2** — all content must be created by you, licensed, or otherwise
  permitted by the rights holder.

A paid tool whose purpose is saving video from subscription sites sits
squarely in the path of the second one, and Microsoft has pulled comparable
downloaders before. Certification is discretionary and the outcome is not
predictable from the policy text alone.

That does not make it unpublishable, and your own use — content you have paid
for, saved locally because a browser player is hard on your eyes — is exactly
the case the tool is good at. Certification is discretionary, so the only way
to know is to submit.

**Submit to the Store first.** Not because it is more likely to pass, but
because finding out is now free: no registration fee, no code-signing
certificate, no hosting. Direct download is the expensive path — a certificate
alone is $200–700 a year — so spending that before you know whether the Store
will have you is the wrong order. A rejection costs days; starting with the
paid route costs money you may not have needed to spend.

If you do submit, lead the description with what it is for: your own purchased
and licensed material, offline and accessible.

### Smaller things worth doing first

| | Why |
|---|---|
| An EULA, and a licence that is not MIT | MIT lets anyone resell your binary. Your own terms need to say what the customer may do, and disclaim liability. |
| An About box with versions and licences | Required for the bundled tools; also the first thing you will ask a customer for when something breaks. |
| A real support address | The Store requires one, and so does anyone paying. |
| A privacy policy | The Store requires one even though the app makes no network calls of its own. One honest paragraph: nothing is collected, nothing is sent, cookies stay local. |
| A way to update | Direct-download builds do not update themselves. At minimum, have the app check a version file and say when it is out of date. |
| Pin yt-dlp's version in the About box | When a site changes and downloads break, the first question is which yt-dlp is inside. |

## Building the release

```bash
python build_exe.py
```

Produces `dist/Easy-dlp.exe`. With both tools in `vendor/` expect roughly
115 MB; without them, 19 MB and a build only a developer can use. The script
prints which it bundled — read that line before shipping.

Check the result on a machine that has never had yt-dlp or ffmpeg installed.
A spare VM is the honest test; `where yt-dlp` returning nothing is the
condition you are trying to reproduce.

## Option A — direct download

### 1. Make an installer

The bare `.exe` works, but customers expect Start Menu entries, an uninstaller,
and Add/Remove Programs. [Inno Setup](https://jrsoftware.org/isinfo.php) is
free, scriptable and the standard choice. A minimal script:

```
[Setup]
AppName=Easy-dlp
AppVersion=1.4.1
AppPublisher=Your Name
DefaultDirName={autopf}\Easy-dlp
DefaultGroupName=Easy-dlp
UninstallDisplayIcon={app}\Easy-dlp.exe
OutputBaseFilename=Easy-dlp-Setup-1.4.1
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
LicenseFile=EULA.txt

[Files]
Source: "dist\Easy-dlp.exe"; DestDir: "{app}"
Source: "licences\*"; DestDir: "{app}\licences"; Flags: recursesubdirs

[Icons]
Name: "{group}\Easy-dlp"; Filename: "{app}\Easy-dlp.exe"
Name: "{autodesktop}\Easy-dlp"; Filename: "{app}\Easy-dlp.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"
```

`PrivilegesRequired=lowest` installs per-user and avoids a UAC prompt, which
is the right default for a tool like this.

### 2. Sign it, or customers will not install it

This applies to direct download only. If you are going through the Store with
an MSIX, Microsoft signs it for you and you can skip this section and its cost
entirely — see Option B.

Nothing requires you to sign — Windows will run an unsigned exe, and a
storefront will sell one. What it costs is the first run: a full-screen
SmartScreen block reading *"Windows protected your PC"*, where "Don't run" is
the obvious button and "Run anyway" is hidden behind **More info**. Some
managed environments refuse it outright. For something people have paid for,
that is a refund generator.

**No certificate buys a clean first run.** Signed or not, a new publisher gets
SmartScreen warnings until reputation accumulates — Microsoft puts that at
several weeks and hundreds of clean installs. What signing buys is a milder
warning that names you, and reputation that carries across releases instead of
resetting with every new build, because it attaches to your identity rather
than to one file's hash.

| Option | Cost | First run |
|---|---|---|
| Store (MSIX) | free | no warning, ever |
| Azure Artifact Signing | ~$9.99/month | warning until reputation builds |
| OV certificate | $150–300/year | same |
| EV certificate | $400+/year | same as OV — no advantage |
| Unsigned | free | strong block; enterprises may refuse |

**Azure Artifact Signing** (renamed from Trusted Signing) is Microsoft's own
service and what they recommend for non-Store distribution: about $120 a year,
no USB token, and it works from GitHub Actions. Eligibility is organisations in
the USA, Canada, EU and UK, and **individual developers in the USA and Canada
only**. Organisations additionally need three or more years of verifiable tax
history — so a company incorporated for this product would be turned down,
while the same person applying as an individual would not.

**EV is not worth buying.** It used to bypass SmartScreen on first download;
Microsoft removed that in 2024, and their own guidance now says paying the EV
premium for SmartScreen reasons is no longer justified. It still carries
stricter identity checks, which only matters for enterprise procurement.

If you cannot use Artifact Signing, an OV certificate from DigiCert, Sectigo or
GlobalSign is the fallback. Since June 2023 the private key must live on an HSM
or hardware token, which the CA supplies. Identity validation takes several
business days, so start it early.

**If the project stays open source**, [SignPath Foundation](https://signpath.io)
signs qualifying open-source projects free at OV level. Worth checking before
you move off MIT, not after.

```bash
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "Easy-dlp-Setup-1.4.1.exe"
```

Always timestamp (`/tr`). Without it, every signature stops validating the day
the certificate expires.

### 3. Sell and deliver it

You need a checkout that issues a licence key and a download link. Paddle and
Lemon Squeezy act as merchant of record, which means they handle VAT and sales
tax worldwide — worth a great deal for a one-person product. Gumroad is the
simplest to start. Stripe alone is cheapest but leaves the tax to you.

Licence enforcement is its own project. For a first release, a key the app
checks against a simple endpoint is enough; perfect enforcement is not
achievable and not where the time pays off.

## Option B — the Microsoft Store

Read **Before you sell it** first.

### What you get

The whole route is free. No registration fee, and for an MSIX no code-signing
certificate either: Microsoft strips any signature and re-signs the package
with its own certificate once it passes certification. Hosting is Microsoft's,
and the OS checks for updates every 24 hours.

The bigger difference is not the money. **A Store install never shows a
SmartScreen warning**, and no amount of certificate buys that anywhere else —
every self-distributed app, signed or not, warns new users until the publisher
builds reputation over weeks. If a clean first run on day one matters, the
Store is the only way to get it.

The one thing to get right is the package format. **MSIX is signed and hosted
for you; an EXE/MSI listing is not** — that route still requires your own CA
certificate, your own hosting and your own update mechanism, which is every
cost of Option A with none of its independence.

### Two routes

**MSIX (recommended).** Free signing, free hosting, automatic updates, works on
Windows in S-mode, and you may use the Store's own commerce platform for the
payment. Build it with the
[MSIX Packaging Tool](https://apps.microsoft.com/detail/9n5lw3jbcxkf) — install
it from the Store, point it at your Inno Setup installer, and it records what
the installer does and produces an `.msix`.

**Listing your EXE/MSI.** Allowed since 2021, but you keep every cost: you host
the installer, you Authenticode-sign it yourself with a CA certificate before
submission — the Store does not re-sign EXE or MSI files — and you handle
updates. It exists mainly for apps that cannot be packaged. Skip it: if the
Store is worth doing, free signing is most of the reason.

### Steps

1. **Register** — start at <https://storedeveloper.microsoft.com>, and only
   there. Registration is **free** for both account types through that flow;
   going in via Partner Center, Visual Studio or Xbox lands you in the legacy
   flow that still charges $19/$99. Verification is a government ID and a
   selfie, and can take up to 30 minutes to propagate.

   Choose **Company**, not Individual. Microsoft's split is whether the
   distribution relates to your business, trade or profession — selling the app
   does — and Partner Center **cannot convert an Individual account to a
   Company one.** Getting it wrong means starting over with a new account.
2. **Reserve the name** "Easy-dlp" in the dashboard. Free, immediate, and it
   stops anyone else taking it.
3. **Package as MSIX** with the tool above. It needs a clean VM to record in —
   recording on your dev machine captures whatever else is installed.
4. **Run the
   [Windows App Certification Kit](https://learn.microsoft.com/windows/uwp/debug-test-perf/windows-app-certification-kit)**
   against the `.msix` before submitting. It catches most mechanical failures
   locally, where the turnaround is minutes rather than days.
5. **Submit**: packages, store listing, screenshots, age rating questionnaire,
   privacy policy URL, support contact. Under 10.2.4 you must disclose the
   bundled yt-dlp and ffmpeg **at the start of the description**.
6. **Certification** takes a few days. Rejections cite the policy number, which
   is the useful part — fix and resubmit, or stop if it is 10.1.6.

### Things that will bite

- `%APPDATA%` is redirected under MSIX. Settings and queue still work, but they
  land somewhere else — so an MSIX install does not see a direct-download
  install's queue, and vice versa.
- The packaged app cannot write beside its own executable. Nothing in Easy-dlp
  does, but keep it that way.
- Downloading to a network share still works; MSIX does not sandbox file
  dialogs.
- Keep the Store build's version number ahead of the direct-download one, or
  customers who have both get confusing results.

## A release checklist

```
[ ] tests pass:  layout paste packaging resources playlist cookies parallel resume resilience
[ ] version bumped in evd/__init__.py and CHANGELOG.md has an entry
[ ] vendor/ holds yt-dlp.exe and an LGPL ffmpeg.exe
[ ] build prints "bundling" for both
[ ] installed and run on a machine with neither tool present
[ ] a real download finishes, to a local folder and to a share
[ ] licence texts included, About box shows versions
[ ] installer signed (direct download only), verified with signtool verify /pa
[ ] tag the commit, attach the installer to a GitHub release
```
