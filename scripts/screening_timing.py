"""Timing of each screening file. Usage: python -P -E scripts/screening_timing.py <out md> <screening csv> [<screening csv> ...]
Reads only the screening exports (no labels). Writes screener, items, minutes from first to last item, median seconds per item."""
import pathlib
import sys

import pandas as pd

if len(sys.argv) < 3:
    sys.exit(__doc__)
rows = []
for f in sys.argv[2:]:
    d = pd.read_csv(f)
    t = pd.to_datetime(d["timestamp"])
    rows.append({"screener": d["screener"].iloc[0], "items": len(d), "minutes_first_to_last": round((t.max() - t.min()).total_seconds() / 60, 1),
                 "median_seconds_per_item": round(d["time_ms"].median() / 1000, 1)})
out = pd.DataFrame(rows)
lines = ["| screener | items | minutes first to last | median seconds per item |", "|---|---|---|---|"]
for _, r in out.iterrows():
    lines.append("| %s | %d | %s | %s |" % (r["screener"], r["items"], r["minutes_first_to_last"], r["median_seconds_per_item"]))
pathlib.Path(sys.argv[1]).write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
print(out.to_string(index=False))
