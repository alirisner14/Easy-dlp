# Privacy Policy

**Easy-dlp** — On the Rise Digital
Last updated [DATE]

> This must be reachable at a public URL before you can submit to the
> Microsoft Store. Publish it at `[WEBSITE]/privacy` and give that URL in
> Partner Center.

---

## The short version

**Easy-dlp collects nothing, sends nothing, and contains no tracking,
analytics, telemetry, advertising or bundled extra software of any kind.**

It has no account, no login, no cloud component and no server. It makes no
network connection of its own. We cannot see what you download, because
nothing reaches us. We never sell data, because we never have any.

The rest of this document says the same thing at greater length, because that
is what a privacy policy is for.

## 1. What the application collects

**Nothing.** There is no analytics library, no crash reporter that phones
home, no usage metrics, no unique identifier, no advertising ID, and no
"anonymous statistics" switch — because there is nothing behind it.

## 2. What stays on your computer

Easy-dlp writes a few files, all local, all yours. None are transmitted
anywhere. You can read, edit and delete any of them.

| What | Where | Why |
|---|---|---|
| Settings | `%APPDATA%\EasyVideoDownloader\settings.json` | download folder, quality, your switch choices |
| Download queue | `%APPDATA%\EasyVideoDownloader\queue.json` | so a restart resumes instead of starting over |
| Activity log | `%APPDATA%\EasyVideoDownloader\activity.log` | the raw output of `yt-dlp`, for when something fails |
| Batch lists | `%APPDATA%\EasyVideoDownloader\batches\` | a copy of each batch, so one can be re-queued |
| Crash report | `%APPDATA%\EasyVideoDownloader\crash.log` | written locally when something goes wrong; **never sent** |
| Part-downloaded files | `%TEMP%\EasyVideoDownloader\work\` | fragments in progress, removed when a download finishes |
| Your videos | the folder you chose | the point of the application |

The activity log contains the addresses you gave the application. It is on
your machine and nowhere else. Delete the folder above at any time; the
application will make a fresh one.

## 3. Your sign-in cookies

If you point Easy-dlp at a `cookies.txt` file exported from your browser, it
passes the file path to `yt-dlp` on your computer so that a site recognises
you as signed in.

**We never receive this file, its contents, or anything derived from it.** It
is not copied, uploaded or logged. The only thing stored is the file path, in
your settings, so you do not have to pick it again.

Treat that file as you would a password. Delete it when you no longer need it.

## 4. Network connections

Easy-dlp itself makes none.

The bundled `yt-dlp` connects to the addresses **you** give it, and only
those. That traffic goes from your computer to that site directly. It does
not pass through us and we have no visibility of it. Those sites will see
your connection as they would any other, subject to their own privacy
policies.

If you enable a feature that checks for a new version, it requests a single
version file from [WEBSITE] and sends nothing but the request itself.
*(Remove this paragraph if you do not ship update checking.)*

## 5. Purchase information

Buying Easy-dlp is handled by our payment provider, not by us. They collect
what they need for the sale — name, email, billing details, tax location —
under their own privacy policy.

We receive your **email address and order record**, and use them only to send
your licence key and receipt, to answer support requests, and to notify you
of an update or a security issue affecting the product you bought. We do not
sell, rent or share this with anyone, and we do not send marketing unless you
ask us to.

> **Fill in:** name your payment provider here and link their privacy policy.
> If you sell through the Microsoft Store, Microsoft is the merchant and
> their privacy statement applies to the transaction.

## 6. Support correspondence

If you email us, we keep the message so we can answer it and recognise a
follow-up. Please do not send us log files containing addresses you would
rather we did not see — and if you do send a log, we treat it as
confidential, use it only to diagnose your problem, and delete it when done.

## 7. Children

Easy-dlp is not directed at children and we do not knowingly collect anything
from anyone. Since we collect nothing at all, there is nothing to delete.

## 8. Your rights

Privacy laws including the GDPR (EU/UK) and the CCPA (California) give you
rights to access, correct, export and delete personal information held about
you, and not to be discriminated against for exercising them.

In practice the only personal information we hold is your purchase record and
any support emails. To see, correct or delete it, write to [SUPPORT EMAIL]
and we will respond within 30 days.

**We have never sold personal information and have no plans to.** There is no
"do not sell" switch because there is nothing to switch off.

## 9. Data retention and security

We keep purchase records as long as needed to support the licence and to meet
tax and accounting obligations, then delete them. Support emails are kept
while the matter is open and for a reasonable period after.

Anything we hold is held with our payment provider and our email provider,
under their security arrangements. We do not run a server, a database or a
cloud service of our own, which removes most of the ways this sort of
information gets lost.

## 10. No bundled software

Easy-dlp installs exactly one application and the two open-source tools it
needs to work (`yt-dlp` and `FFmpeg`). It installs no toolbar, no browser
extension, no "offer", no partner software, no background service and no
scheduled task. It does not modify your browser or your system settings.

## 11. Changes

If this policy changes, the updated version will be published at
[WEBSITE]/privacy with a new date at the top. If a change ever meant we
started collecting something, we would say so plainly and ask first.

## 12. Contact

[LEGAL NAME], trading as On the Rise Digital
[SUPPORT EMAIL]
[WEBSITE]
