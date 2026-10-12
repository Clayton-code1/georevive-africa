"""python -m georevive.ingest --all | --source <id> [--source <id> ...] [--force] [--list]"""

from __future__ import annotations

import argparse
import sys
import time

from .. import audit
from ..config import ensure_dirs, get_settings
from ..db import init_db, session_scope
from ..seed import seed_users
from .connectors import ALL_CONNECTORS, BY_ID
from .http import PoliteHttp
from .report import generate, terminal_summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m georevive.ingest", description="Download and register open data.")
    ap.add_argument("--all", action="store_true", help="run every connector")
    ap.add_argument("--source", action="append", default=[], help="run one connector (repeatable)")
    ap.add_argument("--force", action="store_true", help="ignore the cache and download again")
    ap.add_argument("--list", action="store_true", help="list connector ids and exit")
    ap.add_argument("--report-only", action="store_true", help="only regenerate the Data Report")
    a = ap.parse_args(argv)

    if a.list:
        for c in ALL_CONNECTORS:
            print(f"{c.id:<26} {c.name}")
        return 0
    s = get_settings()
    ensure_dirs(s)
    init_db()
    with session_scope() as db:
        seed_users(db)

    if not a.report_only:
        if a.all:
            todo = ALL_CONNECTORS
        elif a.source:
            unknown = [x for x in a.source if x not in BY_ID]
            if unknown:
                print(f"Unknown source(s): {unknown}. Use --list to see ids.", file=sys.stderr)
                return 2
            todo = [BY_ID[x] for x in a.source]
        else:
            ap.print_help()
            return 2
        ing = s.section("ingest")
        http = PoliteHttp(
            ing.get("user_agent", "GeoRevive"),
            ing.get("request_timeout_s", 60),
            ing.get("min_seconds_between_requests", 1.0),
        )
        for cls in todo:
            t0 = time.time()
            print(f"-> {cls.id}: {cls.name}", flush=True)
            http.log = []
            conn = cls(s, http=http, force=a.force)
            with session_scope() as db:
                out = conn.run(db)
                audit.log(db, "system", "admin", "ingest", "source", cls.id, {"status": out.status})
            msg = f"   {out.status}"
            if out.error:
                msg += f" - {out.error[:160]}"
            print(f"{msg}  ({time.time() - t0:.0f}s)", flush=True)

    with session_scope() as db:
        md, js = generate(db)
        print(terminal_summary(db))
    print(f"Wrote {md} and {js}")

    # Presenter tools: the state right after ingestion is the 'clean' demo state
    from ..demo import scenario, snapshots

    if scenario.demo_data_present():
        print(
            "Note: demo data exists, so the 'clean' snapshot was not updated "
            "(run: python -m georevive.demo reset, then re-run ingestion)."
        )
    else:
        snapshots.save("clean", "after ingestion")
        print("Saved the clean demo state (Presenter Mode > Reset returns here).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
