"""Fetching (robots.txt first, polite retries) and feed parsing.

Adapted from AI Pulse by shru14 (https://github.com/shru14/ai-pulse).
"""
from __future__ import annotations

import gzip
import html
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

from .config import REPO_URL

USER_AGENT = f"LabourPulse/1.0 (+{REPO_URL}; non-commercial news reader)"
ROBOT_NAME = "LabourPulse"  # the name robots.txt rules are matched against
ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
GZIP_MAGIC = bytes([0x1F, 0x8B])

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


# Rate limits and temporary server errors are retried; anything else (404, 403, bad XML) fails at once.
RETRY_STATUS = {429, 500, 502, 503, 504}
ATTEMPTS = 3
BACKOFF = 2.0  # seconds before the 2nd attempt; each later wait is 3x longer (2s, 6s)
MAX_WAIT = 60.0


def _retry_after(err: urllib.error.HTTPError) -> float | None:
    value = err.headers.get("Retry-After") if err.headers else None
    try:
        return float(value) if value else None
    except ValueError:
        return None  # an HTTP date; fall back to our own backoff


# ---------- Only what a site allows ----------
# Every request first checks the site's robots.txt, and a URL it disallows is never fetched. The only
# exception is an official API whose published terms invite programmatic use:
#   api.crossref.org  Crossref's REST API (https://www.crossref.org/documentation/retrieve-metadata/rest-api/):
#                     built for scripts; bibliographic metadata is openly reusable. Requests are serial and
#                     identify themselves (User-Agent, plus a mailto when CROSSREF_MAILTO is set).
API_HOSTS = {"api.crossref.org"}


class Disallowed(Exception):
    """The site's robots.txt doesn't allow fetching this URL."""


_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_robots_lock = threading.Lock()


def _rules(scheme: str, host: str) -> urllib.robotparser.RobotFileParser:
    rules = urllib.robotparser.RobotFileParser()
    req = urllib.request.Request(f"{scheme}://{host}/robots.txt", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20, context=TLS) as resp:
            body = resp.read()
        body = gzip.decompress(body) if body.startswith(GZIP_MAGIC) else body
        rules.parse(body.decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):  # no robots.txt: no rules
            rules.parse([])
        else:  # 401/403 mean "keep out"; 5xx: can't tell, so don't fetch this time
            rules.parse(["User-agent: *", "Disallow: /"])
            if e.code >= 500:
                return rules  # not remembered: asked again on the next run
    _robots[host] = rules
    return rules


def allowed(url: str) -> bool:
    """May Labour Pulse fetch this URL? (robots.txt, fetched once per site per run; see API_HOSTS)"""
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host in API_HOSTS:
        return True
    with _robots_lock:
        rules = _robots.get(host) or _rules(parts.scheme or "https", host)
    return rules.can_fetch(ROBOT_NAME, url)


INTERMEDIATES = Path(__file__).resolve().parent / "certs" / "intermediates.pem"


def _tls() -> ssl.SSLContext:
    """Certificates are always verified. Mozilla's CA list (certifi) is used when installed: Windows' store
    lacks some roots and intermediates that official sites rely on (e.g. digital.gov.my). certs/ holds public
    intermediate certificates that some servers forget to send (parlimen.gov.my), as browsers fetch them;
    a chain must still end at a trusted root."""
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    if INTERMEDIATES.exists():
        context.load_verify_locations(cafile=str(INTERMEDIATES))
    return context


TLS = _tls()


def fetch(url: str, timeout: int = 20, attempts: int = ATTEMPTS) -> bytes:
    """GET a URL the site allows (see allowed), retrying rate limits (429), 5xx errors and network
    timeouts with backoff."""
    if not allowed(url):
        raise Disallowed(f"robots.txt of {urlsplit(url).netloc} doesn't allow fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=TLS) as resp:
                body = resp.read()
            # Some hosts (e.g. deepmind.google) send gzip even when it wasn't requested.
            return gzip.decompress(body) if body.startswith(GZIP_MAGIC) else body
        except urllib.error.HTTPError as err:
            if err.code not in RETRY_STATUS or attempt == attempts - 1:
                raise
            wait = _retry_after(err) or BACKOFF * 3 ** attempt
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == attempts - 1:
                raise
            wait = BACKOFF * 3 ** attempt
        time.sleep(min(wait, MAX_WAIT))
    raise AssertionError("unreachable")


def clean_text(raw: str | None, limit: int = 3000) -> str:
    """Strip HTML, unescape entities, collapse whitespace, trim to a sentence. (Summaries are shortened later,
    by brief.py; a paper's whole abstract is kept so its contribution sentence can be found.)"""
    if not raw:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", raw))
    text = _WS_RE.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: end + 1] if end > limit * 0.5 else cut.rsplit(" ", 1)[0] + "…").strip()


def parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))  # ISO 8601 (Atom)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def parse(xml_bytes: bytes) -> list[dict]:
    """Return entries as dicts: title, url, summary, published (datetime|None), authors (list)."""
    root = ET.fromstring(xml_bytes)
    entries: list[dict] = []

    if root.tag == f"{ATOM}feed":
        for e in root.findall(f"{ATOM}entry"):
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            summary = _text(e.find(f"{ATOM}summary")) or _text(e.find(f"{ATOM}content"))
            published = _text(e.find(f"{ATOM}published")) or _text(e.find(f"{ATOM}updated"))
            entries.append({
                "title": clean_text(_text(e.find(f"{ATOM}title")), 200),
                "url": link,
                "summary": clean_text(summary),
                "published": parse_date(published),
                "authors": [n for a in e.findall(f"{ATOM}author") if (n := clean_text(_text(a.find(f"{ATOM}name")), 80))],
            })
        return entries

    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall(".//item")
    for it in items:
        summary = _text(it.find("description")) or _text(it.find(f"{CONTENT}encoded"))
        published = _text(it.find("pubDate")) or _text(it.find(f"{DC}date"))
        entries.append({
            "title": clean_text(_text(it.find("title")), 200),
            "url": _text(it.find("link")) or _text(it.find("guid")),
            "summary": clean_text(summary),
            "published": parse_date(published),
            "authors": [n for a in it.findall(f"{DC}creator") if (n := clean_text(_text(a), 80))],
        })
    return entries


def parse_federal_register(json_bytes: bytes) -> list[dict]:
    """Federal Register API (documents.json): US federal rules, proposed rules, notices and presidential
    documents, each with its official abstract."""
    return [{"title": clean_text(d.get("title"), 200), "url": d.get("html_url") or "",
             "summary": clean_text(d.get("abstract") or ""), "published": parse_date(d.get("publication_date")),
             "authors": []}
            for d in json.loads(json_bytes).get("results") or []]


def parse_govuk(json_bytes: bytes) -> list[dict]:
    """GOV.UK search API: UK government news, policy papers, consultations and guidance."""
    return [{"title": clean_text(r.get("title"), 200),
             "url": r["link"] if r.get("link", "").startswith("http") else "https://www.gov.uk" + r.get("link", ""),
             "summary": clean_text(r.get("description") or ""), "published": parse_date(r.get("public_timestamp")),
             "authors": []}
            for r in json.loads(json_bytes).get("results") or [] if r.get("link")]



PARSERS = {"feed": parse, "federal_register": parse_federal_register, "govuk": parse_govuk}


# A feed link a page advertises in its <head>: <link rel="alternate" type="application/rss+xml" href="...">
_ALTERNATE = re.compile(r"<link\b[^>]*>", re.I)


def discover(url: str, fetcher=None) -> str | None:
    """The feed a site's homepage advertises, for a feed address that has moved. robots.txt still applies
    (the homepage is fetched with fetch()). Comment feeds are skipped."""
    parts = urlsplit(url)
    home = f"{parts.scheme}://{parts.netloc}/"
    page = (fetcher or fetch)(home).decode("utf-8", "replace")
    for tag in _ALTERNATE.findall(page):
        if re.search(r"rel=[\"']?alternate", tag, re.I) and re.search(r"type=[\"']?application/(rss|atom)\+xml", tag, re.I):
            href = re.search(r"href=[\"']([^\"']+)", tag, re.I)
            if href and "comment" not in href.group(1).lower():
                return urllib.parse.urljoin(home, html.unescape(href.group(1)))
    return None
