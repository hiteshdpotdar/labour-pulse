"""Write the static site: index.html, data/stories.json (every card the page shows) and feed.xml (RSS)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from . import bills, classify, jurisdictions, store
from .config import REPO_URL, SITE_DAYS, SITE_NAME, TAGLINE
from .sources import JOURNALS, SOURCES

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "index.html"
LANGS = {"en": "English", "hi": "हिन्दी", "mr": "मराठी"}


def cards(conn, days: int = SITE_DAYS) -> list[dict]:
    """Stories as the page's cards: one per event, other outlets' reports of it listed under "also"."""
    rows = store.recent(conn, days)
    tracked = store.bills(conn)
    by_id = {r["id"]: r for r in rows}
    also: dict[str, list[dict]] = {}
    for r in rows:
        if r["lead"] and r["lead"] in by_id:
            also.setdefault(r["lead"], []).append({"src": r["source"], "u": r["url"]})
    out = []
    for r in rows:
        if r["lead"] and r["lead"] in by_id:
            continue
        card = {"id": r["id"], "t": r["title"], "u": r["url"], "s": r["summary"], "src": r["source"], "l": r["lang"],
                "st": r["streams"].split(","), "tg": [t for t in r["tags"].split(",") if t],
                "p": [p for p in r["places"].split(",") if p], "d": r["date"]}
        if r["authors"]:
            card["a"] = r["authors"]
        if r["id"] in also:
            card["also"] = also[r["id"]]
        if r["bill"] and r["bill"] in tracked:
            card["bill"] = bills.lifecycle(tracked[r["bill"]])
        out.append(card)
    return out


def meta(conn, items: list[dict]) -> dict:
    health = {h["name"]: h for h in store.source_health(conn)}
    used = {p for c in items for p in c["p"]}
    places = {code: v for code, v in jurisdictions.meta().items() if code in used}
    listed = [{"name": s["name"], "url": s["url"], "stream": classify.STREAMS[s["category"]], "lang": LANGS[s["lang"]]}
              for s in SOURCES]
    listed += [{"name": j["name"], "url": f"https://api.crossref.org/journals/{j['issn']}", "stream": "Research",
                "lang": "English"} for j in JOURNALS]
    listed += [{"name": n, "url": u, "stream": "Labour law tracker", "lang": "English"} for n, u in (
        ("UK Parliament Bills API", "https://bills-api.parliament.uk"), ("Parliament of India", "https://sansad.in"))]
    for s in listed:
        h = health.get(s["name"]) or health.get(f"Journal: {s['name']}")
        s["failing"] = bool(h and h["failures"] >= store.FAILING_AFTER)
    run = store.last_run(conn)
    return {"site": SITE_NAME, "tagline": TAGLINE, "repo": REPO_URL,
            "updated": run["at"] if run else datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "streams": classify.STREAMS, "langs": LANGS, "places": places,
            "regions": {k: v[0] for k, v in jurisdictions.REGIONS.items()},
            "stages": bills.LABELS, "sources": listed}


def rss(items: list[dict], updated: str) -> str:
    entries = []
    for c in items[:80]:
        when = format_datetime(datetime.fromisoformat(c["d"]).replace(tzinfo=timezone.utc))
        entries.append(f"<item><title>{escape(c['t'])}</title><link>{escape(c['u'])}</link>"
                       f"<guid isPermaLink=\"false\">{c['id']}</guid><pubDate>{when}</pubDate>"
                       f"<description>{escape(c['s'] + ' (' + c['src'] + ')')}</description>"
                       + "".join(f"<category>{escape(classify.STREAMS[s])}</category>" for s in c["st"]) + "</item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
            f"<title>{escape(SITE_NAME)}</title><link>{escape(REPO_URL)}</link><description>{escape(TAGLINE)}</description>"
            f"<lastBuildDate>{format_datetime(datetime.fromisoformat(updated))}</lastBuildDate>"
            + "".join(entries) + "</channel></rss>\n")


def build(conn, out: str | Path = "site") -> int:
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    items = cards(conn)
    m = meta(conn, items)
    (out / "data" / "stories.json").write_text(json.dumps({"meta": m, "items": items}, ensure_ascii=False,
                                                          separators=(",", ":")), encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8").replace("{{SITE_NAME}}", escape(SITE_NAME)).replace("{{TAGLINE}}", escape(TAGLINE))
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "feed.xml").write_text(rss(items, m["updated"]), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return len(items)
