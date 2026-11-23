"""Figures. Three modes, kept apart on purpose.

  python -P -E scripts/figures.py real  <results folder> <figures/real folder>
  python -P -E scripts/figures.py pilot <results folder> <trials file> <out folder>   (descriptive only; banner PILOT)
  python -P -E scripts/figures.py sim   <results folder> <SIMULATED trials file> <figures/simulated folder>

real  : baseline accuracy by position and length strata, item-set balance, item difficulty. Read only results/ files; no participants.
pilot : the trials of the two team members, shown as individual points, no inference.
sim   : pipeline-test figures. Every one carries "SIMULATED - pipeline test only" in the title and across the plot.
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402

C = {"chance": "#999999", "step1": "#0072B2", "step3": "#E69F00", "early": "#0072B2", "later": "#D55E00", "console": "#555555", "visual": "#009E73"}
SIM = "SIMULATED - pipeline test only"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110, "savefig.dpi": 160})


def stamp(fig, text, color="red", diagonal=False):
    if diagonal:
        fig.text(0.5, 0.5, text, fontsize=34, color=color, alpha=0.18, rotation=25, ha="center", va="center", weight="bold")
    fig.text(0.01, 0.005, text, fontsize=8, color=color, ha="left", va="bottom")


def f1_baselines(results, out):
    b = pd.read_csv(pathlib.Path(results) / "baselines.csv")
    order = [("", "all"), ("|early", "step <= 3"), ("|later", "step >= 4"), ("|short", "short"), ("|long", "long")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, base, title in zip(axes, ("pool_82", "block_a_24"), ("Eligible pool (82 items)", "Block A (24 items)")):
        x = np.arange(len(order)); w = 0.26
        for k, (m, col, lab) in enumerate((("chance", C["chance"], "chance (1/n)"), ("always step 1", C["step1"], "always step 1"), ("always step 3", C["step3"], "always step 3"))):
            vals, ns = [], []
            for suf, _ in order:
                r = b[(b["item_set"] == base + suf) & (b["method"].str.startswith(m))].iloc[0]
                vals.append(r["exact_acc"] * 100); ns.append(int(r["n_items"]))
            bars = ax.bar(x + (k - 1) * w, vals, w, color=col, label=lab)
            for bx, v in zip(bars, vals):
                ax.text(bx.get_x() + bx.get_width() / 2, v + 1, "%.0f" % v, ha="center", fontsize=8)
        ax.set_xticks(x); ax.set_xticklabels(["%s\n(n = %d)" % (l, n) for (_, l), n in zip(order, ns)])
        ax.axhline(41.1, color="black", ls="--", lw=1)
        ax.text(len(order) - 0.5, 42.2, "published best LLM 41.1%\n(not item-matched)", ha="right", fontsize=8)
        ax.set_title(title); ax.set_ylim(0, 88)
    axes[0].set_ylabel("Exact step accuracy (%)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    fig.suptitle("Participant-free baselines by error position and trace length", y=1.0)
    fig.tight_layout()
    fig.savefig(pathlib.Path(out) / "F1_baseline_accuracy_by_strata.png"); plt.close(fig)


def f2_balance(results, out):
    r = pathlib.Path(results)
    pool = pd.read_csv(r / "pool.csv")
    iset = json.loads((r / "item_set.json").read_text(encoding="utf-8"))
    sel = {}
    for key, name in (("block_a", "Block A"), ("block_b", "Block B"), ("practice", "Practice"), ("reserves", "Reserves")):
        for i in iset[key]:
            sel[i["item"]] = name
    pool["set"] = pool["item"].map(sel).fillna("not selected")
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8))
    cells = pool.groupby(["set", "position_stratum", "length_stratum"]).size().unstack(["position_stratum", "length_stratum"]).fillna(0)
    sets = ["Block A", "Block B", "Practice", "Reserves", "not selected"]
    cols = [("early", "short"), ("early", "long"), ("later", "short"), ("later", "long")]
    colors = ["#56B4E9", "#0072B2", "#F0A27A", "#D55E00"]
    bottom = np.zeros(len(sets))
    for c, colr in zip(cols, colors):
        v = np.array([cells.loc[s, c] if (s in cells.index and c in cells.columns) else 0 for s in sets])
        ax[0].bar(sets, v, bottom=bottom, color=colr, label="%s, %s" % c)
        bottom += v
    ax[0].set_title("Items by set, position and length"); ax[0].set_ylabel("items"); ax[0].tick_params(axis="x", rotation=30)
    ax[0].legend(frameon=False, fontsize=7)
    a = pool[pool["set"] == "Block A"]["label_step"].value_counts().sort_index()
    allp = pool["label_step"].value_counts().sort_index()
    steps = sorted(set(allp.index))
    ax[1].bar(np.arange(len(steps)) - 0.2, [allp.get(s, 0) for s in steps], 0.4, color="#BBBBBB", label="pool (82)")
    ax[1].bar(np.arange(len(steps)) + 0.2, [a.get(s, 0) for s in steps], 0.4, color="#0072B2", label="Block A (24)")
    ax[1].axhline(6, color="black", ls=":", lw=1); ax[1].text(len(steps) - 0.5, 6.6, "cap 6", ha="right", fontsize=8)
    ax[1].set_xticks(np.arange(len(steps))); ax[1].set_xticklabels(steps); ax[1].set_xlabel("labelled step"); ax[1].set_title("Labelled step: pool vs Block A"); ax[1].legend(frameon=False, fontsize=8)
    fw = pool.groupby(["set", "framework"]).size().unstack().fillna(0).reindex(sets).fillna(0)
    bottom = np.zeros(len(sets))
    for f, colr in zip(fw.columns, ("#009E73", "#CC79A7")):
        ax[2].bar(sets, fw[f].values, bottom=bottom, color=colr, label=f); bottom += fw[f].values
    ax[2].set_title("Framework"); ax[2].tick_params(axis="x", rotation=30); ax[2].legend(frameon=False, fontsize=8)
    fig.suptitle("Item-set balance (seed %d)" % iset["seed"], y=1.0)
    fig.tight_layout()
    fig.savefig(pathlib.Path(out) / "F2_item_set_balance.png"); plt.close(fig)


def f3_difficulty(results, out):
    r = pathlib.Path(results)
    pool = pd.read_csv(r / "pool.csv")
    iset = json.loads((r / "item_set.json").read_text(encoding="utf-8"))
    sel = {}
    for key, name in (("block_a", "A"), ("block_b", "B"), ("practice", "practice"), ("reserves", "reserve")):
        for i in iset[key]:
            sel[i["item"]] = name
    pool["set"] = pool["item"].map(sel).fillna("pool")
    pool["chance"] = 1 / pool["n_steps"]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    mk = {"A": "o", "B": "s", "practice": "^", "reserve": "D", "pool": "."}
    for s, g in pool.groupby("set"):
        for pos, gg in g.groupby("position_stratum"):
            ax.scatter(gg["wc_pool"], gg["chance"] * 100, marker=mk[s], s=38 if s != "pool" else 28, color=C[pos], alpha=0.9 if s != "pool" else 0.35,
                       edgecolor="black" if s != "pool" else "none", linewidth=0.4)
    ax.axvline(iset["median_words_pool"], color="black", ls=":", lw=1); ax.text(iset["median_words_pool"] + 20, 37, "pool median\n%.0f words" % iset["median_words_pool"], fontsize=8, va="top")
    ax.set_xlabel("trace length (words, M2 measure)"); ax.set_ylabel("chance of picking the labelled step (%)"); ax.set_ylim(3, 38)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", color=C["early"], label="label at step <= 3"), Line2D([], [], marker="o", ls="", color=C["later"], label="label at step >= 4")]
    h += [Line2D([], [], marker=mk[k], ls="", color="gray", markeredgecolor="black", label=k) for k in ("A", "B", "practice", "reserve")] + [Line2D([], [], marker=".", ls="", color="gray", label="not selected")]
    ax.legend(handles=h, frameon=False, fontsize=8, ncol=2)
    ax.set_title("Chance accuracy (1 / steps) against trace length, by item set")
    fig.tight_layout(); fig.savefig(pathlib.Path(out) / "F3_item_difficulty_chance.png"); plt.close(fig)


def pilot_or_sim_figs(results, trials, out, kind):
    df = trial_io.load_trials(trials)
    err, _ = trial_io.validate(df, results)
    if err:
        sys.exit("schema errors: %s" % err[:3])
    d = trial_io.score(df, results)
    A = d[d["block"] == "A"]
    banner = SIM if kind == "sim" else "PILOT (n = %d) - descriptive only" % d["participant"].nunique()
    color = "red" if kind == "sim" else "#7a4b00"
    suffix = "_SIMULATED" if kind == "sim" else "_PILOT"
    out = pathlib.Path(out)
    p = A.groupby(["participant", "view"])["correct"].mean().unstack().dropna()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1, 1.3]})
    for _, r in p.iterrows():
        ax[0].plot([0, 1], [r["console"] * 100, r["visual"] * 100], color="#BBBBBB", lw=0.8, marker="o", ms=3)
    ax[0].plot([0, 1], [p["console"].mean() * 100, p["visual"].mean() * 100], color="black", lw=2.5, marker="o")
    ax[0].set_xticks([0, 1]); ax[0].set_xticklabels(["View A\n(console)", "View B\n(visual)"]); ax[0].set_ylabel("exact accuracy per participant (%)"); ax[0].set_ylim(-3, 103)
    ax[0].set_title("Block A, one line per participant\n(black: mean of participants; no interval)")
    e = A.groupby(["view", "error_type"]).size().unstack().fillna(0)
    order = ["correct", "right agent, too early", "right agent, too late", "wrong agent", "timeout"]
    cols = ["#009E73", "#56B4E9", "#E69F00", "#D55E00", "#999999"]
    share = e.reindex(columns=order).fillna(0)
    share = share.div(share.sum(axis=1), axis=0) * 100
    left = np.zeros(len(share))
    for c, colr in zip(order, cols):
        ax[1].barh(["View A (console)" if v == "console" else "View B (visual)" for v in share.index], share[c].values, left=left, color=colr, label=c); left += share[c].values
    ax[1].set_xlabel("% of Block A trials"); ax[1].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3); ax[1].set_title("Answer classes (Block A)")
    fig.suptitle(banner, color=color, y=1.0, weight="bold")
    fig.tight_layout()
    stamp(fig, banner, color, diagonal=(kind == "sim"))
    f = out / ("S1_accuracy_and_error_classes%s.png" % suffix if kind == "sim" else "P1_pilot_trials%s.png" % suffix)
    fig.savefig(f); plt.close(fig)
    if kind == "sim":
        fig, ax = plt.subplots(figsize=(6.5, 4))
        for v, off in (("console", -0.15), ("visual", 0.15)):
            g = A[A["view"] == v]
            ax.scatter(np.full(len(g), off) + np.random.default_rng(1).uniform(-.06, .06, len(g)), g["time_s"], s=8, alpha=0.5, color=C[v])
        ax.set_xticks([-0.15, 0.15]); ax.set_xticklabels(["View A", "View B"]); ax.set_ylabel("time per trial (s)"); ax.set_xlim(-0.5, 0.5)
        ax.set_title(banner, color=color, weight="bold", fontsize=10)
        fig.tight_layout(); stamp(fig, banner, color, diagonal=True)
        fig.savefig(out / "S2_time_by_view_SIMULATED.png"); plt.close(fig)
    return f.name


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    mode = sys.argv[1]
    if mode == "real":
        res, out = sys.argv[2], pathlib.Path(sys.argv[3])
        out.mkdir(parents=True, exist_ok=True)
        f1_baselines(res, out); f2_balance(res, out); f3_difficulty(res, out)
        print("wrote", sorted(x.name for x in out.glob("*.png")))
    elif mode in ("pilot", "sim") and len(sys.argv) == 5:
        out = pathlib.Path(sys.argv[4])
        if mode == "sim" and "simulated" not in str(out).lower():
            sys.exit("simulated figures go in a folder named simulated")
        if mode == "sim" and "SIMULATED" not in pathlib.Path(sys.argv[3]).name:
            sys.exit("input file name must contain SIMULATED")
        out.mkdir(parents=True, exist_ok=True)
        print("wrote", pilot_or_sim_figs(sys.argv[2], sys.argv[3], out, mode))
    else:
        sys.exit(__doc__)
