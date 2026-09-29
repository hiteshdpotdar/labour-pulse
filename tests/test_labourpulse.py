"""Tests: python -m pytest -q   (no network: every fetch is answered from the fixtures below)"""

import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from labourpulse import bills, build, classify, collect, crossref, jurisdictions, store

NOW = datetime.now(timezone.utc)
DAY = lambda n: NOW - timedelta(days=n)


def rss(items):
    body = "".join(f"<item><title>{t}</title><link>{u}</link><description>{d}</description>"
                   f"<pubDate>{format_datetime(when)}</pubDate></item>" for t, u, d, when in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


FEEDS = {
    "https://labour.example/feed": rss([
        ("Delivery riders strike against Zomato pay cut in Bengaluru", "https://labour.example/1",
         "Hundreds of riders logged off across the city.", DAY(1)),
        ("Garment workers in Dhaka walk out over unpaid wages", "https://labour.example/2",
         "Factory workers in Bangladesh stopped work on Monday.", DAY(2)),
        ("Old story from last year", "https://labour.example/old", "", DAY(400)),
    ]),
    "https://general.example/feed": rss([
        ("Garment workers in Dhaka walk out over unpaid wages, unions say", "https://general.example/a",
         "Unions in Bangladesh said thousands joined.", DAY(1)),
        ("Stock markets rally on tech earnings", "https://general.example/b", "Shares rose.", DAY(1)),
        ("BJP workers clash with police in Kolkata", "https://general.example/c", "", DAY(1)),
    ]),
    "https://hindi.example/feed": rss([
        ("श्रम संहिता के ख़िलाफ़ मज़दूरों की देशव्यापी हड़ताल", "https://hindi.example/1",
         "दिल्ली में ट्रेड यूनियनों ने प्रदर्शन किया।", DAY(1)),
    ]),
    "https://marathi.example/feed": rss([
        ("मुंबईत घरकामगारांचा संप; किमान वेतनाची मागणी", "https://marathi.example/1", "", DAY(1)),
        ("संपूर्ण राज्यात पावसाचा जोर", "https://marathi.example/2", "", DAY(1)),
    ]),
}
SOURCES = [
    {"name": "Labour Wire", "url": "https://labour.example/feed", "category": "news", "lang": "en"},
    {"name": "General Daily", "url": "https://general.example/feed", "category": "news", "lang": "en", "filter": True},
    {"name": "हिंदी मज़दूर", "url": "https://hindi.example/feed", "category": "news", "lang": "hi"},
    {"name": "मराठी दैनिक", "url": "https://marathi.example/feed", "category": "news", "lang": "mr", "filter": True},
]
CROSSREF = json.dumps({"message": {"items": [
    {"type": "journal-article", "title": ["The reproductive limits of platform control in paid domestic work"],
     "URL": "https://doi.org/10.1111/anti.99999", "DOI": "10.1111/anti.99999",
     "author": [{"given": "A", "family": "Author"}], "abstract": "<jats:p>We study platforms in Mumbai.</jats:p>",
     "published-online": {"date-parts": [[DAY(3).year, DAY(3).month, DAY(3).day]]}},
    {"type": "journal-article", "title": ["Issue Information"], "URL": "https://doi.org/10.1111/x"},
]}}).encode()


def fake_fetch(url, *a, **k):
    if url in FEEDS:
        return FEEDS[url]
    if url.startswith("https://api.crossref.org"):
        return CROSSREF
    raise OSError(f"no fixture for {url}")


@pytest.fixture
def conn(tmp_path):
    c = store.connect(tmp_path / "t.db")
    yield c
    c.close()


def test_collect_sort_group_and_build(conn, tmp_path):
    added, errors = collect.collect_feeds(conn, SOURCES, max_age_days=30, fetcher=fake_fetch, log=lambda *_: None)
    assert errors == []
    rows = {r["url"]: dict(r) for r in conn.execute("SELECT * FROM items")}
    # the general feed keeps labour stories only, and not party "workers"
    assert "https://general.example/b" not in rows and "https://general.example/c" not in rows
    assert "https://labour.example/old" not in rows  # too old
    assert rows["https://labour.example/1"]["streams"] == "platform"
    assert "IN-KA" in rows["https://labour.example/1"]["places"]
    assert rows["https://hindi.example/1"]["lang"] == "hi" and "Strike" in rows["https://hindi.example/1"]["tags"]
    assert rows["https://marathi.example/1"]["streams"] == "platform" and rows["https://marathi.example/1"]["lang"] == "mr"
    assert "https://marathi.example/2" not in rows  # "संपूर्ण" is not a strike
    # the same walk-out from two outlets becomes one card
    assert collect.regroup(conn) == 1
    j_added, j_errors = collect.collect_journals(conn, [{"name": "Antipode", "issn": "1467-8330"}], fetcher=fake_fetch,
                                                 log=lambda *_: None)
    assert j_added == 1 and not j_errors
    paper = conn.execute("SELECT * FROM items WHERE source = 'Antipode'").fetchone()
    assert paper["streams"] == "research,platform" and paper["authors"] == "A Author"
    n = build.build(conn, tmp_path / "site")
    data = json.loads((tmp_path / "site" / "data" / "stories.json").read_text(encoding="utf-8"))
    assert n == len(data["items"]) == 5  # six stories, the walk-out twice
    walkout = next(c for c in data["items"] if "Dhaka" in c["t"])
    assert len(walkout["also"]) == 1
    assert (tmp_path / "site" / "index.html").read_text(encoding="utf-8").count("Labour Pulse") >= 1
    assert "<rss" in (tmp_path / "site" / "feed.xml").read_text(encoding="utf-8")


def test_broken_feed_is_recorded_not_fatal(conn):
    added, errors = collect.collect_feeds(conn, [{"name": "Gone", "url": "https://gone.example/feed", "category": "news",
                                                  "lang": "en"}], fetcher=fake_fetch, log=lambda *_: None)
    assert added == 0 and errors
    assert store.source_health(conn)[0]["failures"] == 1


def test_uk_bill_stages_and_card(conn):
    stages = [{"description": "1st reading", "house": "Commons", "stageSittings": [{"date": "2024-10-10T00:00:00"}]},
              {"description": "3rd reading", "house": "Commons", "stageSittings": [{"date": "2025-03-12T00:00:00"}]},
              {"description": "3rd reading", "house": "Lords", "stageSittings": [{"date": "2025-10-20T00:00:00"}]},
              {"description": "Royal Assent", "house": "Unassigned", "stageSittings": [{"date": "2025-12-18T00:00:00"}]}]
    history = bills.uk_history({}, stages)
    assert [h["stage"] for h in history] == ["introduced", "passed_chamber", "passed_legislature", "signed"]
    assert bills.upsert(conn, {"key": "GB-1", "jurisdiction": "GB", "title": "Employment Rights Bill (2024)",
                               "url": "https://bills.parliament.uk/bills/1", "source": "UK Parliament", "history": history})
    life = bills.lifecycle(store.bills(conn)["GB-1"])
    assert life["current"] == "signed" and life["law"]
    card = conn.execute("SELECT * FROM items WHERE bill = 'GB-1'").fetchone()
    assert card["streams"] == "law" and card["places"] == "GB"


def test_india_history():
    h = bills.in_history({"billIntroducedDate": "2019-07-23", "billIntroducedInHouse": "Lok Sabha",
                          "billPassedInLSDate": "2019-07-30", "billPassedInRSDate": "2019-08-02",
                          "billAssentedDate": "2019-08-08"})
    assert [x["stage"] for x in h] == ["introduced", "passed_chamber", "passed_legislature", "signed"]


def test_manual_laws_skip_example(conn, tmp_path):
    f = tmp_path / "laws.json"
    f.write_text(json.dumps({"laws": [
        {"example": True, "title": "Example", "jurisdiction": "IN-KA", "url": "https://x", "stages": []},
        {"title": "State Platform-based Gig Workers Act", "jurisdiction": "IN-RJ", "url": "https://gazette.example/1",
         "stages": [{"date": "2023-07-24", "stage": "passed_legislature", "text": "Passed"}]}]}), encoding="utf-8")
    assert bills.sync_manual(conn, f) == 1
    card = conn.execute("SELECT * FROM items WHERE bill LIKE 'MANUAL-%'").fetchone()
    assert card["streams"] == "law,platform" and card["places"] == "IN,IN-RJ"


@pytest.mark.parametrize("title,default,streams", [
    ("Karnataka passes Platform-based Gig Workers Bill", "news", ["platform", "law"]),
    ("UK Employment Rights Act: what changes for zero-hours workers", "news", ["law"]),
    ("Supreme Court rules on contract labour regularisation", "news", ["policy"]),
    ("Nurses strike against new labour law", "news", ["news"]),
    ("Leaders must act on wages, unions say", "news", ["news"]),
    ("Rethinking real subsumption in platform capitalism", "theory", ["theory", "platform"]),
    ("Ministry notifies draft rules under Code on Wages", "policy", ["law"]),
])
def test_categorize(title, default, streams):
    assert classify.categorize(title, "", default) == streams


def test_places_and_languages():
    assert jurisdictions.detect("ILO adopts platform work standard") == ["INTL"]
    assert jurisdictions.in_states("पुण्यात कामगारांचा मोर्चा") == ["IN-MH"]
    assert classify.language("कामगारांचा मोर्चा निघाला आणि आंदोलन सुरू आहे", "en") == "mr"
    assert classify.language("मज़दूरों की हड़ताल जारी है और", "en") == "hi"


def test_crossref_parse_skips_housekeeping():
    items = crossref.parse(CROSSREF, "Antipode")
    assert len(items) == 1 and items[0]["summary"] == "We study platforms in Mumbai."
