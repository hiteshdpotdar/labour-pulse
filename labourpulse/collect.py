"""One collection run: every feed, every journal, the law tracker; then regroup duplicates."""

from __future__ import annotations

import re
import time
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import bills, classify, crossref, feeds, jurisdictions, store
from .sources import JOURNALS, SOURCES


def _summary(text: str, title: str, limit: int = 320) -> str:
    """The publisher's own description, trimmed to a couple of sentences; empty if it only repeats the title."""
    text = re.sub(r"\s*(The post .{0,200} appeared first on .{0,80}\.?|Continue reading.*|Read more.*|\[…\]|\[\.\.\.\])\s*$",
                  "", text or "", flags=re.I).strip()
    if not text or text.lower().startswith(title.lower()[:60]) and len(text) < len(title) + 20:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("। "), cut.rfind("? "), cut.rfind("! "))
    return (cut[: end + 1] if end > limit * 0.4 else cut.rsplit(" ", 1)[0] + "…").strip()


def make_item(entry: dict, source: dict) -> dict | None:
    """A story ready to store, or None if it should be left out."""
    title = (entry.get("title") or "").strip()
    url = (entry.get("url") or "").strip()
    if not title or not url.startswith("http"):
        return None
    if source.get("skip") and re.search(source["skip"], title):
        return None
    summary = _summary(entry.get("summary", ""), title)
    if source.get("filter") and not classify.is_labour(title, summary):
        return None
    default = source.get("category", "news")
    published = entry.get("published") or datetime.now(timezone.utc)
    places = jurisdictions.detect(title, summary)
    places += jurisdictions.in_states(title, summary) if "IN" in places else []
    return {"title": title, "url": url, "summary": summary, "source": entry.get("journal") or source["name"],
            "lang": classify.language(title, source.get("lang", "en")),
            "streams": classify.categorize(title, summary, default),
            "tags": classify.tags_for(title, summary), "places": places, "authors": entry.get("authors", []),
            "date": published.date().isoformat()}


def _fresh(entry: dict, max_age_days: int) -> bool:
    when = entry.get("published")
    return when is None or when >= datetime.now(timezone.utc) - timedelta(days=max_age_days)


def collect_feeds(conn, sources=SOURCES, max_age_days: int = 3, fetcher=feeds.fetch, log=print) -> tuple[int, list[str]]:
    added, errors = 0, []
    for src in sources:
        try:
            parse = feeds.PARSERS[src.get("format", "feed")]
            url = src["url"]
            try:
                parsed = parse(fetcher(url))
            except (urllib.error.HTTPError, ET.ParseError) as first:
                # A moved feed (404) or a page that isn't a feed: look for the feed the homepage advertises.
                if src.get("format", "feed") != "feed" or (isinstance(first, urllib.error.HTTPError) and first.code != 404):
                    raise
                found = feeds.discover(url, fetcher)
                if not found or found == url:
                    raise
                url = found
                parsed = parse(fetcher(url))
                log(f"  {src['name']}: feed found at {url} (update sources.py)")
            entries = [e for e in parsed if _fresh(e, max_age_days)]
            n = 0
            for e in entries:
                item = make_item(e, src)
                if item and not store.exists(conn, item["url"]) and not store.title_seen(conn, item["title"]):
                    n += store.insert(conn, item)
            store.record_source(conn, src["name"], url, True, count=n)
            added += n
            log(f"  {src['name']}: {n} new")
        except Exception as e:  # a broken feed mustn't stop the run
            errors.append(f"{src['name']}: {e}")
            store.record_source(conn, src["name"], src["url"], False, str(e))
            log(f"  {src['name']} failed: {e}")
        conn.commit()
        time.sleep(0.3)
    return added, errors


def collect_journals(conn, journals=JOURNALS, max_age_days: int = 3, fetcher=feeds.fetch, log=print) -> tuple[int, list[str]]:
    added, errors = 0, []
    for j in journals:
        src = {"name": j["name"], "category": "research", "lang": "en", "filter": j.get("filter", False)}
        try:
            n = 0
            # Crossref records appear days after a journal publishes online, so look back at least two weeks.
            for e in crossref.fetch_journal(j, max(max_age_days, 14), fetcher):
                item = make_item(e, src)
                if item and not store.exists(conn, item["url"]):
                    n += store.insert(conn, item)
            store.record_source(conn, f"Journal: {j['name']}", crossref.url_for(j["issn"], 14), True, count=n)
            added += n
            log(f"  {j['name']}: {n} new")
        except Exception as e:
            errors.append(f"{j['name']}: {e}")
            store.record_source(conn, f"Journal: {j['name']}", crossref.url_for(j["issn"], 14), False, str(e))
            log(f"  {j['name']} failed: {e}")
        conn.commit()
    return added, errors


# --- Grouping: the same event reported by several outlets becomes one card ---
_WORD = re.compile(r"[^\W\d_]{3,}|\d{2,}")
_STOP = set("""the and for with from that this into over after about amid their they have has are was were will
not but how why what who when its his her new says said say more than just also out off per via
के की का में है और से को पर ने एक यह कि लिए भी हैं था थी आणि आहे च्या ला ने हे ही तो""".split())


def _tokens(title: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(title) if w.lower() not in _STOP}


def regroup(conn, days: int = 14, threshold: float = 0.5) -> int:
    """Link stories published within 3 days of each other whose headlines share most of their words (and the
    same language) under the earliest one. Returns how many stories were grouped under another."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, lang, date, source, bill FROM items WHERE date >= ? ORDER BY date, added_at", (since,))]
    leads: list[dict] = []
    grouped = 0
    for r in rows:
        r["tok"] = _tokens(r["title"])
        lead = None
        if not r["bill"] and len(r["tok"]) >= 3:
            for L in reversed(leads[-400:]):
                if L["lang"] != r["lang"] or L["source"] == r["source"] or L["bill"]:
                    continue
                if (datetime.fromisoformat(r["date"]) - datetime.fromisoformat(L["date"])).days > 3:
                    break
                shared = len(r["tok"] & L["tok"])
                if shared >= 3 and shared / min(len(r["tok"]), len(L["tok"])) >= threshold:
                    lead = L
                    break
        conn.execute("UPDATE items SET lead = ? WHERE id = ?", (lead["id"] if lead else None, r["id"]))
        if lead:
            grouped += 1
        else:
            leads.append(r)
    conn.commit()
    return grouped


def reclassify(conn) -> int:
    """Re-run the current sorting and tagging rules over every stored story (after you change classify.py)."""
    by_name = {s["name"]: s for s in SOURCES} | {j["name"]: {"category": "research"} for j in JOURNALS}
    changed = 0
    for r in conn.execute("SELECT url, title, summary, source, lang, streams, tags, bill FROM items").fetchall():
        if r["bill"]:
            continue
        src = by_name.get(r["source"], {"category": r["streams"].split(",")[0]})
        streams = ",".join(classify.categorize(r["title"], r["summary"], src.get("category", "news")))
        tags = ",".join(classify.tags_for(r["title"], r["summary"]))
        if (streams, tags) != (r["streams"], r["tags"]):
            store.update(conn, r["url"], streams=streams, tags=tags)
            changed += 1
    conn.commit()
    return changed


def collect(conn, max_age_days: int = 3, log=print) -> int:
    if store.is_empty(conn):
        max_age_days = max(max_age_days, 30)  # first run: a month of history, so the site isn't empty
        log(f"Empty database: reading the last {max_age_days} days.")
    a, e1 = collect_feeds(conn, max_age_days=max_age_days, log=log)
    b, e2 = collect_journals(conn, max_age_days=max_age_days, log=log)
    c, e3 = bills.sync(conn, log=log)
    log(f"Grouped {regroup(conn)} stories under another outlet's card.")
    store.log_run(conn, a + b + c, e1 + e2 + e3)
    conn.commit()
    return a + b + c
