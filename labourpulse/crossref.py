"""New journal articles from Crossref's open REST API (https://api.crossref.org), by journal ISSN."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from . import feeds
from .config import CROSSREF_MAILTO

API = "https://api.crossref.org/journals/{issn}/works"
# Not research articles: a journal's housekeeping.
NOT_ARTICLES = re.compile(r"^(issue information|front matter|back matter|editorial board|masthead|cover|table of contents|"
                          r"erratum|errata|corrigendum|correction|retraction|publisher'?s note|index|contents|"
                          r"notes on contributors|books received|call for papers)\b", re.I)


def _date(work: dict) -> str | None:
    for key in ("published-online", "published-print", "published", "issued", "created"):
        parts = (work.get(key) or {}).get("date-parts") or [[]]
        if parts[0] and parts[0][0]:
            y, m, d = (parts[0] + [1, 1])[:3]
            return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _authors(work: dict) -> list[str]:
    out = []
    for a in work.get("author") or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name") or ""
        if name:
            out.append(name)
    return out


def parse(json_bytes: bytes, journal: str) -> list[dict]:
    """Crossref works as entries like feeds.parse(), plus the journal's name."""
    entries = []
    for w in (json.loads(json_bytes).get("message") or {}).get("items") or []:
        title = feeds.clean_text(" ".join(w.get("title") or []), 250)
        if not title or NOT_ARTICLES.match(title) or w.get("type") not in (None, "journal-article"):
            continue
        day = _date(w)
        abstract = re.sub(r"^\s*(Abstract|Summary)[:.]?\s*", "", feeds.clean_text(w.get("abstract") or "", 1200), flags=re.I)
        entries.append({"title": title, "url": w.get("URL") or f"https://doi.org/{w.get('DOI', '')}",
                        "summary": abstract, "authors": _authors(w)[:8], "journal": journal,
                        "published": datetime.fromisoformat(day).replace(tzinfo=timezone.utc) if day else None})
    return entries


def url_for(issn: str, since_days: int) -> str:
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
    url = (API.format(issn=quote(issn)) + f"?filter=from-created-date:{since},type:journal-article"
           "&sort=created&order=desc&rows=60&select=DOI,URL,title,author,abstract,type,published-online,"
           "published-print,published,issued,created")
    return url + (f"&mailto={quote(CROSSREF_MAILTO)}" if CROSSREF_MAILTO else "")


def fetch_journal(journal: dict, since_days: int, fetcher=feeds.fetch) -> list[dict]:
    body = fetcher(url_for(journal["issn"], since_days))
    time.sleep(1)  # serial and unhurried
    return parse(body, journal["name"])
