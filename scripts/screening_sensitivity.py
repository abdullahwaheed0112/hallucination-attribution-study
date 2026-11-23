"""Sensitivity of Block A and B accuracy to the screening flags (decision D10: flagged items stay in the item set).

Usage: python -P -E scripts/screening_sensitivity.py <trials.csv> <results folder> <screening_agreement_items.csv> <out folder>
Flagged = both screeners differ from the label by more than one step (or chose no step). Writes a table with all items and with flagged items removed.
Descriptive only for any file whose data_label is not SIMULATED: no p-values, no intervals.
"""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402


def flagged_items(path):
    d = pd.read_csv(path)
    out = set()
    for _, r in d.iterrows():
        lab = pd.to_numeric(r["label"], errors="coerce")
        far = []
        for c in ("AW", "AM"):
            v = pd.to_numeric(r[c], errors="coerce")
            far.append(pd.isna(v) or abs(v - lab) > 1)
        if all(far):
            out.add(r["item"])
    return out


def main(trials, results, items_csv, out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    df = trial_io.load_trials(trials)
    d = trial_io.score(df, results)
    d = d[d["block"].isin(["A", "B"])].copy()
    flag = flagged_items(items_csv)
    d["flagged"] = d["item"].isin(flag)
    rows = []
    for name, sub in [("all items", d), ("flagged items removed", d[~d["flagged"]]), ("flagged items only", d[d["flagged"]])]:
        for (blk, view), g in sub.groupby(["block", "view"]):
            rows.append({"item set": name, "block": blk, "view": view, "n_trials": len(g), "exact": round(g["correct"].mean(), 3),
                         "agent": round(g["agent_correct"].mean(), 3), "tolerant": round(g["tolerant"].mean(), 3)})
    t = pd.DataFrame(rows)
    label = ", ".join(sorted(df["data_label"].unique()))
    name = pathlib.Path(trials).stem
    t.to_csv(out / (name + "__screening_sensitivity.csv"), index=False)
    note = "Data label: %s. Descriptive only (no p-values, no intervals). Flagged items in the item set: %d of the Block A and B items shown to this participant: %d trials." % (
        label, len(flag), int(d["flagged"].sum()))
    (out / (name + "__screening_sensitivity.md")).write_text("# Screening sensitivity\n\n" + note + "\n\n" + trial_io.md_table(t) + "\n", encoding="utf-8")
    print(note)
    print(t.to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
