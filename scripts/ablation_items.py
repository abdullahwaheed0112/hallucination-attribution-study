"""E1 item-feature analysis (definition: docs/ablation_definitions.md). Descriptive, 82 pool items, no p-values.

Usage: python -P -E scripts/ablation_items.py <results folder>
Reads results/pool.csv and results/step_table.csv. Writes results/ablation_E1_item_features.csv, ablation_E1_position_by_category.csv and ablation_E1_item_features.md.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402

SCOPE = "E1: 82 eligible pool items; simple rules only; descriptive (no p-values, no intervals); position and category are confounded; not a model of human or LLM difficulty"


def design(d):
    cols = {"position": [(d["position_stratum"] == "later").astype(float).rename("later")],
            "length": [((d["wc_pool"] - d["wc_pool"].mean()) / d["wc_pool"].std()).rename("words_z")],
            "n_agents": [(d["n_agents"] == k).astype(float).rename("agents_%d" % k) for k in (3, 4)],
            "category": [(d["category"] == c).astype(float).rename("cat_" + c.split()[0]) for c in sorted(d["category"].unique())[1:]],
            "framework": [(d["framework"] == "Camel").astype(float).rename("camel")]}
    return {k: pd.concat(v, axis=1) for k, v in cols.items()}


def adj_r2(y, X):
    n = len(y)
    A = np.column_stack([np.ones(n), X.to_numpy(float)]) if X is not None and X.shape[1] else np.ones((n, 1))
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    ss_res = float(((y - A @ beta) ** 2).sum()); ss_tot = float(((y - y.mean()) ** 2).sum())
    p = A.shape[1] - 1
    if ss_tot == 0:
        return np.nan
    return 1 - (ss_res / (n - p - 1)) / (ss_tot / (n - 1))


def main(results):
    r = pathlib.Path(results)
    pool = pd.read_csv(r / "pool.csv")
    st = pd.read_csv(r / "step_table.csv", usecols=["item", "step", "agent"])
    ag3 = st[st["step"] == 3].set_index("item")["agent"]
    pool["step3_agent_ok"] = [int(ag3.get(i) == a) for i, a in zip(pool["item"], pool["responsible_agent"])]
    pool["step1_hit"] = (pool["label_step"] == 1).astype(float)
    pool["step3_hit"] = (pool["label_step"] == 3).astype(float)
    pool["chance"] = 1.0 / pool["n_steps"]
    D = design(pool)
    full = pd.concat(D.values(), axis=1)
    outs = {"always step 1 hits the label": "step1_hit", "always step 3 hits the label": "step3_hit",
            "always step 3 names the responsible agent": "step3_agent_ok", "chance accuracy 1/steps": "chance"}
    rows = []
    for name, col in outs.items():
        y = pool[col].to_numpy(float)
        a_full = adj_r2(y, full)
        rows.append(dict(scope=SCOPE, outcome=name, view="all features together", feature="all", adj_r2=a_full, change_if_dropped=np.nan))
        for f, X in D.items():
            rest = pd.concat([v for k, v in D.items() if k != f], axis=1)
            rows.append(dict(scope=SCOPE, outcome=name, view="feature alone", feature=f, adj_r2=adj_r2(y, X), change_if_dropped=np.nan))
            rows.append(dict(scope=SCOPE, outcome=name, view="drop one from full model", feature=f, adj_r2=adj_r2(y, rest), change_if_dropped=adj_r2(y, rest) - a_full))
    out = pd.DataFrame(rows)
    out.to_csv(r / "ablation_E1_item_features.csv", index=False)
    cross = pd.crosstab(pool["position_stratum"], pool["category"])
    cross.insert(0, "scope", SCOPE)
    cross.to_csv(r / "ablation_E1_position_by_category.csv")
    step_bin = pool["label_step"].map(lambda v: "4+" if v >= 4 else str(v)).rename("label_step")
    cs = pd.crosstab([pool["framework"], pool["category"]], step_bin)
    cs.insert(0, "scope", SCOPE)
    cs.to_csv(r / "ablation_E1_category_by_label_step.csv")
    rates = pool.groupby("position_stratum")[["step1_hit", "step3_hit", "step3_agent_ok", "chance"]].mean().round(3)
    lines = ["# E1 item-feature analysis", "", "SCOPE: " + SCOPE, "",
             "Adjusted R-squared of a linear probability model (outcome ~ features). 'alone' = one feature; 'drop one' = all features except that one; the last column is the change from the full model (negative = that feature carried explanatory share).", ""]
    for name in outs:
        g = out[out["outcome"] == name]
        lines.append("## " + name)
        lines.append("")
        lines.append("Full model adjusted R2: %.3f" % g[g["view"] == "all features together"]["adj_r2"].iloc[0])
        lines.append("")
        t = g[g["view"] != "all features together"].pivot(index="feature", columns="view", values=["adj_r2", "change_if_dropped"])
        tt = pd.DataFrame({"alone": t[("adj_r2", "feature alone")], "full minus this feature": t[("adj_r2", "drop one from full model")], "change when dropped": t[("change_if_dropped", "drop one from full model")]}).round(3).reset_index()
        lines.append(trial_io.md_table(tt))
        lines.append("")
    lines += ["## Position by category (counts)", "", trial_io.md_table(pd.crosstab(pool["position_stratum"], pool["category"]).reset_index()), "",
              "## Framework and category by labelled step (counts)", "", trial_io.md_table(pd.crosstab([pool["framework"], pool["category"]], step_bin).reset_index()), "",
              "## Rates by position (share of items)", "", trial_io.md_table(rates.reset_index()), "",
              "Correlation in the pool: corr(words, 1/steps) = %.2f; corr(words, steps) = %.2f." % (np.corrcoef(pool["wc_pool"], 1 / pool["n_steps"])[0, 1], np.corrcoef(pool["wc_pool"], pool["n_steps"])[0, 1]), "",
              "Reading note: outcomes 1 to 3 depend on the label position by definition, so position is expected to explain them; the table does not show what makes an item hard for people."]
    (r / "ablation_E1_item_features.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
