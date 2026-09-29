"""The labour law tracker: bills and laws with their stages, from official records.

  * UK Parliament Bills API (Open Parliament Licence v3.0)
  * Parliament of India's legislation API (sansad.in, the one its own bill pages use; no key)
  * data/laws.json: laws you add by hand, for places with no readable official record (Indian state gig and
    domestic worker laws, for instance). See the example in that file.

News of a bill or law anywhere else reaches the tracker through the classifier (classify.LAW).
The UK and India readers are adapted from AI Pulse by shru14 (https://github.com/shru14/ai-pulse).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import classify, feeds, jurisdictions, store

STAGES = ["introduced", "passed_chamber", "passed_legislature", "signed", "in_force"]
ENDED = ["defeated", "withdrawn", "lapsed"]
LABELS = {"introduced": "Introduced", "passed_chamber": "Passed one House", "passed_legislature": "Passed both Houses",
          "signed": "Assent", "in_force": "In force", "defeated": "Defeated", "withdrawn": "Withdrawn", "lapsed": "Lapsed"}

# A labour bill, judged by its title.
LABOUR_TITLE = re.compile(
    r"employment|employee|\bworkers?\b|workmen|labou?r|wages?\b|trade unions?|industrial (relations|disputes|tribunals?)|"
    r"social security|occupational safety|working conditions|\bgig\b|platform|domestic work|minimum wage|"
    r"(equal|holiday|sick|statutory|maternity|paternity) pay|strikes?\b|redundanc|apprentice|factories|"
    r"contract labour|bonded labour|child labour|modern slavery|provident fund|gratuity|shops and establishments|"
    r"fire and rehire|zero hours|agency workers|unfair dismissal|trade dispute", re.I)

LAWS_FILE = Path(__file__).resolve().parent.parent / "data" / "laws.json"


def current(history: list[dict]) -> dict | None:
    ended = [h for h in history if h["stage"] in ENDED]
    if ended:
        return ended[-1]
    reached = [h for h in history if h["stage"] in STAGES]
    return max(reached, key=lambda h: STAGES.index(h["stage"])) if reached else None


def lifecycle(bill: dict) -> dict:
    """What a tracker card shows: each stage with its date (or none yet), and where the bill is now."""
    when = {h["stage"]: h["date"] for h in bill["history"]}
    now = current(bill["history"])
    steps = [{"stage": s, "label": LABELS[s], "date": when.get(s)} for s in STAGES]
    ended = [h for h in bill["history"] if h["stage"] in ENDED]
    if ended:
        steps.append({"stage": ended[-1]["stage"], "label": LABELS[ended[-1]["stage"]], "date": ended[-1]["date"]})
    return {"current": now["stage"] if now else None, "steps": steps,
            "law": any(h["stage"] in ("signed", "in_force") for h in bill["history"])}


def upsert(conn, bill: dict) -> bool:
    """Save a bill and its tracker card. Returns True if it is new or its stage changed."""
    now = current(bill["history"])
    if not now:
        return False
    prev = conn.execute("SELECT history FROM bills WHERE key = ?", (bill["key"],)).fetchone()
    changed = not prev or current(json.loads(prev[0])) != now
    conn.execute("INSERT OR REPLACE INTO bills (key, jurisdiction, title, url, source, summary, history, updated_at)"
                 " VALUES (?,?,?,?,?,?,?,?)",
                 (bill["key"], bill["jurisdiction"], bill["title"], bill["url"], bill["source"], bill.get("summary", ""),
                  json.dumps(bill["history"]), store.now()))
    streams = ["law"] + (["platform"] if classify._hit(classify.PLATFORM, bill["title"]) else [])
    places = [bill["jurisdiction"].split("-")[0]] + ([bill["jurisdiction"]] if "-" in bill["jurisdiction"] else [])
    item = {"title": bill["title"], "summary": bill.get("summary", ""), "url": bill["url"], "source": bill["source"],
            "lang": "en", "streams": streams, "tags": classify.tags_for(bill["title"], bill.get("summary", "")),
            "places": places, "date": now["date"], "bill": bill["key"]}
    if store.exists(conn, bill["url"]):
        store.update(conn, bill["url"], title=item["title"], summary=item["summary"], date=item["date"],
                     streams=streams, bill=bill["key"])
    else:
        store.insert(conn, item)
    return changed


def _get_json(url: str, fetcher=feeds.fetch) -> dict:
    return json.loads(fetcher(url))


# --- UK Parliament ---
UK_API = "https://bills-api.parliament.uk/api/v1"
UK_SEARCHES = ("employment", "workers", "trade union", "wage", "strikes", "pay", "redundancy", "social security")


def uk_history(bill: dict, stages: list[dict]) -> list[dict]:
    """Lifecycle from a bill's stages: first reading, third reading in each House, Royal Assent."""
    reached: dict[str, dict] = {}
    third: dict[str, str] = {}
    for st in stages:
        dates = sorted(s["date"][:10] for s in st.get("stageSittings") or [] if s.get("date"))
        if not dates:
            continue
        what, house = st.get("description", ""), st.get("house", "")
        if what == "1st reading":
            reached.setdefault("introduced", {"date": dates[0], "stage": "introduced", "text": f"1st reading, {house}"})
        elif what == "3rd reading":
            third.setdefault(house, dates[-1])
        elif what == "Royal Assent":
            reached["signed"] = {"date": dates[0], "stage": "signed", "text": "Royal Assent"}
    if third:
        reached["passed_chamber"] = {"date": min(third.values()), "stage": "passed_chamber", "text": "3rd reading"}
        if len(third) == 2:
            reached["passed_legislature"] = {"date": max(third.values()), "stage": "passed_legislature",
                                             "text": "3rd reading in both Houses"}
    if bill.get("billWithdrawn"):
        reached["withdrawn"] = {"date": bill["billWithdrawn"][:10], "stage": "withdrawn", "text": "Withdrawn"}
    elif bill.get("isDefeated"):
        reached["defeated"] = {"date": (bill.get("lastUpdate") or "")[:10], "stage": "defeated", "text": "Defeated"}
    return sorted(reached.values(), key=lambda h: (h["date"], (STAGES + ENDED).index(h["stage"])))


def sync_uk(conn, fetcher=feeds.fetch, log=print) -> int:
    found: dict[int, dict] = {}
    for term in UK_SEARCHES:
        data = _get_json(f"{UK_API}/Bills?SearchTerm={term.replace(' ', '%20')}&SortOrder=DateUpdatedDescending&Take=50",
                         fetcher)
        for b in data.get("items", []):
            if LABOUR_TITLE.search(b.get("shortTitle") or ""):
                found[b["billId"]] = b
        time.sleep(0.5)
    changed = 0
    for bill_id, b in found.items():
        stages = _get_json(f"{UK_API}/Bills/{bill_id}/Stages?Take=100", fetcher).get("items", [])
        long_title = (_get_json(f"{UK_API}/Bills/{bill_id}", fetcher) or {}).get("longTitle") or ""
        history = uk_history(b, stages)
        year = next((h["date"][:4] for h in history if h["stage"] == "introduced"), "")
        short = re.sub(r"\s*\[HL\]$", "", b["shortTitle"])
        changed += upsert(conn, {"key": f"GB-{bill_id}", "jurisdiction": "GB",
                                 "title": f"{short} ({year})" if year else short,
                                 "url": f"https://bills.parliament.uk/bills/{bill_id}", "source": "UK Parliament",
                                 "history": history, "summary": feeds.clean_text(long_title, 400)})
        conn.commit()
        time.sleep(0.5)
    return changed


# --- India (sansad.in) ---
IN_API = "https://sansad.in/api_rs/legislation/getBills"
IN_SEARCHES = ("labour", "wages", "workers", "employment", "social security", "industrial relations", "domestic workers",
               "gig", "occupational safety", "trade unions")
_IN_QUERY = ("loksabha=&sessionNo=&house=&ministryName=&billType=&billCategory=&billStatus=&introductionDateFrom="
             "&introductionDateTo=&passedInLsDateFrom=&passedInLsDateTo=&passedInRsDateFrom=&passedInRsDateTo="
             "&page=1&size=50&locale=en&sortOn=billIntroducedDate&sortBy=desc")


def in_history(b: dict) -> list[dict]:
    day = lambda k: (b.get(k) or "")[:10]
    history = []
    if day("billIntroducedDate"):
        history.append({"date": day("billIntroducedDate"), "stage": "introduced",
                        "text": f"Introduced in {b.get('billIntroducedInHouse') or 'Parliament'}"})
    passed = sorted(d for d in (day("billPassedInLSDate"), day("billPassedInRSDate")) if d)
    if passed:
        history.append({"date": passed[0], "stage": "passed_chamber", "text": "Passed one House"})
    if len(passed) == 2:
        history.append({"date": passed[1], "stage": "passed_legislature", "text": "Passed both Houses"})
    if day("billAssentedDate"):
        history.append({"date": day("billAssentedDate"), "stage": "signed", "text": "Assent"})
    return history


def sync_india(conn, fetcher=feeds.fetch, log=print) -> int:
    get = (lambda u: feeds.fetch(u, timeout=120)) if fetcher is feeds.fetch else fetcher  # the API answers slowly
    found = {}
    for term in IN_SEARCHES:
        data = _get_json(f"{IN_API}?billName={term.replace(' ', '%20')}&{_IN_QUERY}", get)
        for b in data.get("records") or []:
            if LABOUR_TITLE.search(b.get("billName") or ""):
                house = "LS" if (b.get("billIntroducedInHouse") or "").startswith("Lok") else "RS"
                found[f"IN-{house}-{b.get('billYear')}-{b.get('billNumber')}"] = b
        time.sleep(1)
    changed = 0
    for key, b in found.items():
        url = (b.get("billIntroducedFile") or "https://sansad.in/ls/legislation/bills").replace(" ", "%20")
        bill = {"key": key, "jurisdiction": "IN", "title": (b["billName"] or "").strip().rstrip("."), "url": url,
                "source": "Parliament of India", "history": in_history(b)}
        if bill["history"]:
            changed += upsert(conn, bill)
    conn.commit()
    return changed


# --- Laws kept by hand (data/laws.json) ---
def sync_manual(conn, path: Path = LAWS_FILE, log=print) -> int:
    if not path.exists():
        return 0
    changed = 0
    for law in json.loads(path.read_text(encoding="utf-8")).get("laws", []):
        if law.get("example"):
            continue
        code = law["jurisdiction"]
        if code.split("-")[0] not in jurisdictions.JURISDICTIONS:
            log(f"data/laws.json: unknown place {code!r} in {law.get('title')!r}; skipped")
            continue
        changed += upsert(conn, {"key": "MANUAL-" + re.sub(r"[^a-z0-9]+", "-", law["title"].lower()).strip("-"),
                                 "jurisdiction": code, "title": law["title"], "url": law["url"],
                                 "source": law.get("source", "Hand-kept record"), "summary": law.get("summary", ""),
                                 "history": sorted(law["stages"], key=lambda h: h["date"])})
    conn.commit()
    return changed


SYNCS = {"uk": sync_uk, "india": sync_india, "manual": sync_manual}


def sync(conn, only: str | None = None, log=print) -> tuple[int, list[str]]:
    total, errors = 0, []
    for name, fn in SYNCS.items():
        if only and name != only:
            continue
        try:
            n = fn(conn, log=log)
            total += n
            store.record_source(conn, f"Law tracker: {name}", name, True, count=n)
            log(f"  law tracker ({name}): {n} new or changed")
        except Exception as e:  # one parliament's API being down mustn't stop the others
            errors.append(f"law tracker ({name}): {e}")
            store.record_source(conn, f"Law tracker: {name}", name, False, str(e))
            log(f"  law tracker ({name}) failed: {e}")
    conn.commit()
    return total, errors
