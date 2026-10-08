"""Say how to get the videos out of whatever the user copied.

A course site, a lesson page, a YouTube playlist and a bare file all need a
different route in: paste the link, paste the page source, or run one of the
collector snippets in the browser. Working out which is the step people get
stuck on, so the app reads a sample of what they have and names the route.

Nothing here touches the network - it reads the text it is given, nothing
more - so it answers instantly and works for pages behind a sign-in.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import downloader as D
from . import pagescan

# the snippets travel inside the app, so a buyer never needs the tools folder
SNIPPETS = {
    "bunny": "BunnyCollectionScript.js",
    "vimeo": "VimeoCollectionScript.js",
    "cloudflare": "CloudflareCollectionScript.js",
}

PASTE_LINK = "link"        # paste the link(s) as they are
PASTE_PAGE = "page"        # paste the page source
SNIPPET = "snippet"        # run a collector snippet in DevTools
COPY_SOURCE = "source"     # need the page source to say more
UNKNOWN = "unknown"


@dataclass
class Advice:
    kind: str
    headline: str           # one line, the answer
    detail: str             # the steps
    snippet: str = ""       # a key of SNIPPETS, when one is needed


def snippet_text(key: str) -> str:
    """The snippet's source, from inside a build or from the tools folder."""
    name = SNIPPETS[key]
    roots = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        roots.append(meipass)
    roots.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for root in roots:
        path = os.path.join(root, "tools", name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                return fh.read()
    raise FileNotFoundError(name)


_URL = re.compile(r"https?://[^\s\"'<>|]+", re.I)
_DEVTOOLS = ("Open the course in your browser, signed in. Press F12, open the "
             "Console tab, click the Copy button below and paste it there, then "
             "press Enter. (The first time, Chrome asks you to type "
             "\"allow pasting\".) When its panel appears, click Copy, then "
             "Paste in Easy-dlp.")
_GET_SOURCE = ("Open the lesson page, press Ctrl+U to view its source, then "
               "Ctrl+A and Ctrl+C. Paste that here and press Identify again.")

_COURSE_HOSTS = {
    # sites whose own address already says which route they need
    "freya.courses": "bunny",
    "freya.academy": "bunny",
}
_LINK_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
               "twitch.tv", "tiktok.com", "instagram.com", "facebook.com",
               "x.com", "twitter.com", "soundcloud.com", "bandcamp.com",
               "reddit.com", "bilibili.com", "rumble.com")
_DIRECT = re.compile(r"\.(mp4|m4v|mov|webm|mkv|mp3|m4a|wav|flac|m3u8|mpd)$", re.I)


def _host(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower().split(":")[0]
    except ValueError:
        return ""


def _ends(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _snippet(key: str, why: str) -> Advice:
    return Advice(SNIPPET, "Use the %s snippet in DevTools." % SNIPPETS[key],
                  why + "\n\n" + _DEVTOOLS, key)


def identify(text: str, playlists_on: bool = True) -> Advice:
    text = (text or "").strip()
    if not text:
        return Advice(UNKNOWN, "Paste something first.",
                      "Copy a video's link, or a page's source, and paste it in the box.")

    is_page = pagescan.looks_like_page(text) or "<" in text[:2000]
    if is_page:
        return _from_page(text)
    return _from_links(text, playlists_on)


def _from_page(text: str) -> Advice:
    low = text.lower()
    # Cloudflare first: its pages also mention other players in passing
    if "cloudflarestream.com" in low or "videodelivery.net" in low:
        return _snippet("cloudflare",
                        "This page plays its videos from Cloudflare Stream, whose "
                        "links are signed while each lesson plays and are never in "
                        "the page source.")
    if "b-cdn.net" in low:
        locked = pagescan.locked_lessons(text)
        lessons = pagescan.lessons_from_page(text)
        if locked:
            return _snippet("bunny",
                            "This page's videos are locked: it only unlocks the "
                            "lesson open on it (%d other%s can't be taken from it)."
                            % (locked, "" if locked == 1 else "s"))
        if lessons:
            return Advice(PASTE_PAGE, "Paste this page source into Easy-dlp.",
                          "It lists %d lesson%s, named and numbered. Press Paste "
                          "with the source on the clipboard and they are staged."
                          % (len(lessons), "" if len(lessons) == 1 else "s"))
    if "player.vimeo.com" in low or re.search(r"vimeo\.com/(?:video/)?\d{6,}", low):
        return _snippet("vimeo",
                        "This page embeds Vimeo, and each lesson's video id is only "
                        "added to its page after it loads.")
    if "wistia" in low:
        return Advice(PASTE_LINK, "Paste the lesson page's address.",
                      "This page plays from Wistia. Paste the address of each "
                      "lesson page (not its source). Wistia needs your sign-in: "
                      "set Cookies in Options to your browser first.")
    if re.search(r"youtube(?:-nocookie)?\.com/embed/", low):
        return Advice(PASTE_LINK, "Paste the YouTube link(s).",
                      "This page embeds YouTube. Right-click the video, Copy "
                      "video URL, and paste that.")
    extras = pagescan.resources_from_page(text)
    if extras:
        return Advice(PASTE_PAGE, "Paste this page source into Easy-dlp.",
                      "No video was recognised, but it has %d handout%s "
                      "(worksheets, brushes, project files) Easy-dlp can collect."
                      % (len(extras), "" if len(extras) == 1 else "s"))
    return Advice(UNKNOWN, "No video player recognised on this page.",
                  "If the video plays on the page, try this: press F12, open the "
                  "Network tab, play the video, type m3u8 in the filter box, and "
                  "copy the address that appears. Paste that into Easy-dlp.")


def _from_links(text: str, playlists_on: bool) -> Advice:
    urls = _URL.findall(text)
    if not urls:
        return Advice(UNKNOWN, "That doesn't look like a link or a page.",
                      "Copy the video's address from the address bar, or the "
                      "page source (Ctrl+U, then Ctrl+A, Ctrl+C).")
    url = urls[0]
    host = _host(url)
    path = urlsplit(url).path

    for domain, key in _COURSE_HOSTS.items():
        if _ends(host, domain):
            return _snippet(key, "Freya locks each video to its own lesson page, "
                                 "so the course's links have to be collected in "
                                 "your signed-in browser.")
    if _ends(host, "b-cdn.net") and "bcdn_token=" not in url and "/playlist.m3u8" in path:
        return Advice(PASTE_LINK, "Paste the video link(s).",
                      "If the download fails with 403 Forbidden, the site signs "
                      "its videos: use the BunnyCollectionScript.js snippet instead.",
                      "bunny")
    if _ends(host, "cloudflarestream.com") or _ends(host, "videodelivery.net"):
        return Advice(PASTE_LINK, "Paste the video link(s).",
                      "Signed Cloudflare links last about six hours. For a whole "
                      "course, use the CloudflareCollectionScript.js snippet.", "cloudflare")
    if _ends(host, "player.vimeo.com") or (_ends(host, "vimeo.com") and re.search(r"/\d{6,}", path)):
        return Advice(PASTE_LINK, "Paste the video link(s).",
                      "For a whole course that embeds Vimeo, use the "
                      "VimeoCollectionScript.js snippet on the course page.", "vimeo")
    if _DIRECT.search(path) or pagescan_resource(url):
        return Advice(PASTE_LINK, "Paste the link(s).",
                      "That's a direct file address; Easy-dlp downloads it as it is.")
    if D.looks_like_playlist(url):
        note = ("Playlists is on, so every video in it is downloaded."
                if playlists_on else
                "Turn on Playlists in Options first. With it off, only the one "
                "video the link points at is downloaded.")
        return Advice(PASTE_LINK, "Paste the playlist link.", note)
    if any(_ends(host, d) for d in _LINK_HOSTS):
        return Advice(PASTE_LINK, "Paste the video link(s).",
                      "Easy-dlp reads this site directly. Paste one link per line.")
    return Advice(COPY_SOURCE, "Paste the link(s) - or identify the page source.",
                  "Many sites work from their link alone, so try pasting it. If "
                  "it fails, the video is embedded from somewhere else: "
                  + _GET_SOURCE)


def pagescan_resource(url: str) -> bool:
    return bool(D.resource_ext(url, ""))
