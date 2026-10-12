"""python -m georevive.demo  snapshot-clean [--force] | reset | build-scenario | load-scenario | status"""

from __future__ import annotations

import argparse
import sys

from . import scenario, snapshots


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m georevive.demo")
    ap.add_argument("command", choices=["snapshot-clean", "reset", "build-scenario", "load-scenario", "status"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    from ..api.app import startup

    startup()
    if a.command == "snapshot-clean":
        if scenario.demo_data_present() and not a.force:
            print(
                "Demo data (documents, runs, claims or shares) exists - not saving it as 'clean'. "
                "Use 'reset' first, or --force."
            )
            return 1
        print("Saved clean snapshot:", snapshots.save("clean", "after ingestion"))
    elif a.command == "reset":
        snapshots.restore("clean")
        print("Restored the clean state (after ingestion).")
    elif a.command == "build-scenario":
        log = scenario.build()
        snapshots.restore("clean")
        print("Built the complete scenario:", log)
        print("The app is back in the clean state; use 'load-scenario' (or Presenter Mode) to jump to the end state.")
    elif a.command == "load-scenario":
        snapshots.restore("complete")
        print("Loaded the complete scenario.")
    else:
        for n in snapshots.NAMES:
            print(n, snapshots.info(n) or "missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
