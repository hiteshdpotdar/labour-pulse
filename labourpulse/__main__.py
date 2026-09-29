"""Command line: python -m labourpulse {collect,build,serve,reclassify,regroup,bills,sources,status,prune}"""

import argparse
import functools
import http.server
from datetime import datetime

from . import bills, store
from .build import build
from .collect import collect, reclassify, regroup


def main():
    p = argparse.ArgumentParser(prog="labourpulse", description="Collect labour news, law and research; build the site.")
    p.add_argument("--db", default="labourpulse.db", help="SQLite database file (default: labourpulse.db)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="read every source once and store new stories")
    c.add_argument("--max-age-days", type=int, default=3)
    b = sub.add_parser("build", help="write the static site")
    b.add_argument("--out", default="site")
    s = sub.add_parser("serve", help="build the site and open it at http://127.0.0.1:8000")
    s.add_argument("--port", type=int, default=8000)
    sub.add_parser("reclassify", help="re-sort and re-tag stored stories with the current rules")
    sub.add_parser("regroup", help="regroup duplicate stories into single cards")
    bl = sub.add_parser("bills", help="sync the law tracker only")
    bl.add_argument("--only", choices=list(bills.SYNCS))
    sub.add_parser("sources", help="each source's health: last success, failures in a row, last error")
    sub.add_parser("status", help="Markdown summary for the GitHub Actions run page")
    pr = sub.add_parser("prune", help="delete stories older than N days (law-tracker records are kept)")
    pr.add_argument("--keep-days", type=int, default=730)
    a = p.parse_args()
    conn = store.connect(a.db)

    if a.cmd == "collect":
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] Collecting")
        print(f"Added {collect(conn, a.max_age_days)} new stories.")
    elif a.cmd == "build":
        print(f"Built {build(conn, a.out)} cards into {a.out}/")
    elif a.cmd == "serve":
        n = build(conn, "site")
        print(f"Built {n} cards. Open http://127.0.0.1:{a.port} (Ctrl+C to stop)")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory="site")
        http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler).serve_forever()
    elif a.cmd == "reclassify":
        print(f"Re-sorted {reclassify(conn)} stories.")
    elif a.cmd == "regroup":
        print(f"{regroup(conn, days=3650)} stories grouped under another card.")
    elif a.cmd == "bills":
        n, errors = bills.sync(conn, a.only)
        print(f"{n} bills new or changed." + (f" Errors: {errors}" if errors else ""))
    elif a.cmd == "sources":
        for h in store.source_health(conn):
            flag = "FAILING" if h["failures"] >= store.FAILING_AFTER else ("ok" if h["failures"] == 0 else f"{h['failures']} failed")
            print(f"{flag:>9}  {h['name']:<45} last ok: {h['last_ok'] or 'never':<26} {h['last_error'][:90]}")
    elif a.cmd == "status":
        run = store.last_run(conn)
        total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        print(f"### {total} stories stored" + (f"; last run added {run['added']}" if run else ""))
        from .sources import SOURCES
        configured = {x["name"]: x["url"] for x in SOURCES}
        moved = [h for h in store.source_health(conn) if h["name"] in configured and h["failures"] == 0
                 and h["url"] != configured[h["name"]]]
        if moved:
            print("\n**Feeds found at a new address** (put these in labourpulse/sources.py):\n")
            for h in moved:
                print(f"- {h['name']}: `{h['url']}`")
        bad = [h for h in store.source_health(conn) if h["failures"] > 0]
        if bad:
            print("\n| Source | Failures in a row | Last error |\n|---|---|---|")
            for h in bad:
                print(f"| {h['name']} | {h['failures']} | {h['last_error'][:120].replace('|', '/')} |")
        else:
            print("\nEvery source answered.")
    elif a.cmd == "prune":
        print(f"Deleted {store.prune(conn, a.keep_days)} old stories.")
        conn.commit()


if __name__ == "__main__":
    main()
