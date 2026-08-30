#!/usr/bin/env python3
"""Find the named Sentry links in a converted USD and emit a mapping report.
Does not modify the USD.
"""
from pathlib import Path
import argparse, json, re

here = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--usd", default=str(here / "output" / "Sentry_raw.usd"))
ap.add_argument("--rules", default=str(here / "config" / "link_rules.json"))
ap.add_argument("--report", default=str(here / "output" / "link_mapping.json"))
args = ap.parse_args()

from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
try:
    from pxr import Usd
    usd = Path(args.usd).resolve()
    rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    stage = Usd.Stage.Open(str(usd))
    if stage is None:
        raise RuntimeError(f"Cannot open USD: {usd}")

    all_prims = list(stage.Traverse())
    rows = []
    found = {}
    for semantic, aliases in rules["links"].items():
        matches = []
        alias_l = [a.lower() for a in aliases]
        for prim in all_prims:
            name = prim.GetName()
            display = prim.GetMetadata("displayName") or ""
            text = (name + " " + str(display)).lower()
            if any(a in text for a in alias_l):
                matches.append(str(prim.GetPath()))
        found[semantic] = sorted(set(matches))

    report = {
        "usd": str(usd),
        "prim_count": len(all_prims),
        "semantic_matches": found,
        "warning": "This report is name-based. Verify joint axes/origins before authoring physics."
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    app.close()
