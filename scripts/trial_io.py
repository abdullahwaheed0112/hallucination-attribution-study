"""Load a trial-level file written by the study app, validate it against the app schema, and score it offline.

Usage (validate only): python -P -E scripts/trial_io.py <trials.csv or all.json> <results folder>
Reads results/item_set.json, results/labels_PRIVATE.json and results/step_table.csv. Never reads the data/ folder.
Scoring needs the labels, so do not run this on real participant data before both team members finished blind screening.
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

CAP_MS = 240000
TRIAL_COLS = ["participant", "data_label", "session_id", "list", "view_order", "block", "trial_index", "item", "view", "chosen_step", "timed_out",
              "time_ms", "confidence", "suggestion_key", "suggestion_step", "suggestion_shown", "suggestion_accepted", "n_search", "n_details",
              "n_filter", "n_scroll", "n_expand", "events", "app_version", "timestamp"]
TLX_COLS = ["participant", "data_label", "session_id", "view", "block", "mental", "physical", "temporal", "performance", "effort", "frustration", "raw_tlx", "timestamp"]


def md_table(df):
    """Markdown table without the optional tabulate package."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(x) for x in r.tolist()) + " |")
    return chr(10).join(lines)


def assign(code):
    """Same rule as the app: participant number n -> cell (n-1) mod 8, list = cell//2 + 1, console first when cell is even."""
    import re
    m = re.search(r"(\d+)", str(code))
    if not m or int(m.group(1)) < 1:
        return None
    cell = (int(m.group(1)) - 1) % 8
    return {"list": cell // 2 + 1, "view_order": "A_first" if cell % 2 == 0 else "B_first"}


def load_trials(path):
    p = pathlib.Path(path)
    if p.suffix.lower() == ".json":
        recs = json.loads(p.read_text(encoding="utf-8"))["records"]
        df = pd.DataFrame([r for r in recs if r.get("type") == "trial"])
        if "events" in df:
            df["events"] = df["events"].map(json.dumps)
    else:
        df = pd.read_csv(p, encoding="utf-8")
    return df


def load_tlx(path):
    p = pathlib.Path(path)
    if p.suffix.lower() == ".json":
        recs = [r for r in json.loads(p.read_text(encoding="utf-8"))["records"] if r.get("type") == "tlx"]
        rows = [dict(r, **r.get("scores", {})) for r in recs]
        return pd.DataFrame(rows)
    return pd.read_csv(p, encoding="utf-8")


def load_design(results):
    r = pathlib.Path(results)
    iset = json.loads((r / "item_set.json").read_text(encoding="utf-8"))
    labels = json.loads((r / "labels_PRIVATE.json").read_text(encoding="utf-8"))["labels"]
    steps = pd.read_csv(r / "step_table.csv", usecols=["item", "step", "agent"], encoding="utf-8")
    agents = {k: dict(zip(g["step"], g["agent"])) for k, g in steps.groupby("item")}
    info = {}
    for key in ("practice", "block_a", "block_b", "reserves"):
        for i in iset[key]:
            info[i["item"]] = i
    return iset, labels, agents, info


def validate(df, results):
    """Return (errors, warnings). Errors mean the file does not follow the app schema."""
    iset, labels, agents, info = load_design(results)
    err, warn = [], []
    miss = [c for c in TRIAL_COLS if c not in df.columns]
    if miss:
        return ["missing columns: " + ", ".join(miss)], warn
    if df.empty:
        return ["no trial rows"], warn
    for c, ok in (("view", {"console", "visual"}), ("block", {"practice", "A", "B"})):
        bad = set(df[c].dropna().unique()) - ok
        if bad:
            err.append("%s has unexpected values %s" % (c, sorted(bad)))
    if err:
        return err, warn
    unknown = set(df["item"]) - set(info)
    if unknown:
        err.append("unknown items: %s" % sorted(unknown)[:5])
    df = df[df["item"].isin(info)]
    for i, r in df.iterrows():
        n = info[r["item"]]["n_steps"]
        timed = bool(r["timed_out"])
        if pd.isna(r["chosen_step"]) != timed:
            err.append("row %d: chosen_step empty must equal timed_out" % i)
        elif not pd.isna(r["chosen_step"]) and not (1 <= r["chosen_step"] <= n):
            err.append("row %d: chosen_step %s outside 1..%d" % (i, r["chosen_step"], n))
        if timed != pd.isna(r["confidence"]):
            err.append("row %d: confidence must be empty exactly when timed out" % i)
        elif not pd.isna(r["confidence"]) and not (1 <= r["confidence"] <= 5):
            err.append("row %d: confidence outside 1..5" % i)
        if not (0 <= r["time_ms"] <= CAP_MS + 2000):
            err.append("row %d: time_ms %s outside 0..cap" % (i, r["time_ms"]))
        if r["block"] == "B" and pd.isna(r["suggestion_step"]):
            err.append("row %d: Block B trial without a suggestion" % i)
        if r["block"] != "B" and not pd.isna(r["suggestion_step"]):
            err.append("row %d: suggestion outside Block B" % i)
        if len(err) > 40:
            err.append("... stopping after 40 errors")
            return err, warn
    for who, g in df.groupby("participant"):
        a = assign(who)
        if a is None:
            warn.append("%s: code has no number, cannot check the list" % who)
        elif g["list"].iloc[0] != a["list"] or g["view_order"].iloc[0] != a["view_order"]:
            warn.append("%s: list/view order differ from the code rule (manual override?)" % who)
        for blk, expect, per in (("practice", 2, None), ("A", 12, 6), ("B", 4, 2)):
            b = g[g["block"] == blk]
            if len(b) != expect:
                warn.append("%s: %d trials in block %s (expected %d)" % (who, len(b), blk, expect))
            elif per:
                vc = b["view"].value_counts()
                if any(vc.get(v, 0) != per for v in ("console", "visual")):
                    warn.append("%s: block %s views not %d/%d" % (who, blk, per, per))
        la = iset["block_a_lists"].get(str(g["list"].iloc[0]))
        if la:
            for _, r in g[g["block"] == "A"].iterrows():
                if r["item"] not in la.get(r["view"], []):
                    warn.append("%s: item %s not in list %s for view %s" % (who, r["item"], g["list"].iloc[0], r["view"]))
        if g["session_id"].nunique() != 1:
            warn.append("%s: %d sessions share this code (%s); analyse sessions separately" % (who, g["session_id"].nunique(), ", ".join(sorted(map(str, g["session_id"].unique())))))
        if g["data_label"].nunique() != 1:
            warn.append("%s: more than one data_label" % who)
    return err, warn


def score(df, results):
    """Add offline scoring columns. Timeouts are wrong on every accuracy measure (M2 Step 7)."""
    iset, labels, agents, info = load_design(results)
    d = df.copy()
    d["label_step"] = d["item"].map(lambda i: labels[i]["step"])
    d["resp_agent"] = d["item"].map(lambda i: labels[i]["agent"])
    d["n_steps"] = d["item"].map(lambda i: info[i]["n_steps"])
    d["words"] = d["item"].map(lambda i: info[i]["words"])
    d["n_agents"] = d["item"].map(lambda i: info[i]["n_agents"])
    d["position"] = d["item"].map(lambda i: info[i]["position_stratum"])
    d["length"] = d["item"].map(lambda i: info[i]["length_stratum"])
    d["chosen_agent"] = [agents[i].get(int(s)) if not pd.isna(s) else None for i, s in zip(d["item"], d["chosen_step"])]
    ok = d["chosen_step"].notna()
    d["correct"] = (ok & (d["chosen_step"] == d["label_step"])).astype(int)
    d["agent_correct"] = (ok & (d["chosen_agent"] == d["resp_agent"])).astype(int)
    d["tolerant"] = (ok & ((d["chosen_step"] - d["label_step"]).abs() <= 1)).astype(int)
    d["signed_error"] = np.where(ok, d["chosen_step"] - d["label_step"], np.nan)
    et = []
    for _, r in d.iterrows():
        if pd.isna(r["chosen_step"]):
            et.append("timeout")
        elif r["correct"] == 1:
            et.append("correct")
        elif r["agent_correct"] == 0:
            et.append("wrong agent")
        else:
            et.append("right agent, too early" if r["chosen_step"] < r["label_step"] else "right agent, too late")
    d["error_type"] = et
    d["conf01"] = (d["confidence"] - 1) / 4.0
    d["view_visual"] = (d["view"] == "visual").astype(int)
    d["time_s"] = d["time_ms"] / 1000.0
    d["suggestion_correct"] = np.where(d["suggestion_step"].notna(), (d["suggestion_step"] == d["label_step"]).astype(float), np.nan)
    d["accepted"] = np.where(d["suggestion_step"].notna(), (d["chosen_step"] == d["suggestion_step"]).astype(float), np.nan)
    return d


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    df = load_trials(sys.argv[1])
    e, w = validate(df, sys.argv[2])
    print("rows: %d, participants: %d, labels: %s" % (len(df), df["participant"].nunique(), sorted(df["data_label"].unique())))
    print("ERRORS (%d):" % len(e)); [print("  " + x) for x in e]
    print("WARNINGS (%d):" % len(w)); [print("  " + x) for x in w[:20]]
    sys.exit(1 if e else 0)
