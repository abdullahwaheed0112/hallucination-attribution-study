"""Generate SIMULATED trial data in the app's schema, to test the analysis pipeline. Not a finding of any kind.

Usage: python -P -E scripts/simulate_trials.py <results folder> <out folder> [n_participants] [seed] [view_effect_logit]
Writes trials_SIMULATED.csv and tlx_SIMULATED.csv (data_label = SIMULATED) and sim_truth_SIMULATED.json (the injected parameters).
The out folder must be named simulated (or contain "simulated") so that simulated data cannot be mixed up with real data.
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402

DEFAULTS = dict(base=0.40, sd_participant=0.8, sd_item=1.0, sd_slope=0.3, later_effect=-0.5, timeout_p=0.03, follow_wrong=0.35, follow_shift_visual=0.0)


def simulate(results, n=32, seed=20261201, beta=0.8, **kw):
    """Returns (trials DataFrame, tlx DataFrame, truth dict). beta = injected effect of the visual view on the logit scale."""
    P = dict(DEFAULTS, **kw)
    rng = np.random.default_rng(seed)
    iset, labels, agents, info = trial_io.load_design(results)
    items = list(info)
    item_eff = {i: rng.normal(0, P["sd_item"]) for i in items}
    logit = lambda p: np.log(p / (1 - p))
    sig = lambda x: 1 / (1 + np.exp(-x))
    rows, tlx = [], []
    for k in range(1, n + 1):
        code = "P%02d" % k
        a = trial_io.assign(code)
        u = rng.normal(0, P["sd_participant"])
        slope = beta + rng.normal(0, P["sd_slope"])
        first_visual = a["view_order"] == "B_first"
        lst = iset["block_a_lists"][str(a["list"])]
        seq = []   # (block, item, view, suggestion_step, suggestion_key)
        for j, it in enumerate(iset["practice"]):
            seq.append(("practice", it["item"], "visual" if (j == 0) == first_visual else "console", None, None))
        order = ["visual", "console"] if first_visual else ["console", "visual"]
        for v in order:
            its = list(lst[v]); rng.shuffle(its)
            seq += [("A", i, v, None, None) for i in its]
        brows = iset["block_b_lists"][str(a["list"])]
        brows = sorted(brows, key=lambda r: (r["view"] != order[0], rng.random()))
        for r in brows:
            lab = labels[r["item"]]
            sug = trial_io.json.loads((pathlib.Path(results) / "labels_PRIVATE.json").read_text(encoding="utf-8"))["block_b_suggestions"][r["item"]]
            step = sug["correct"] if r["suggestion"] == "correct" else sug["incorrect"]
            seq.append(("B", r["item"], r["view"], step, "X" if r["suggestion"] == "correct" else "Y"))
        counters = {"practice": 0, "A": 0, "B": 0}
        for block, item, view, sstep, skey in seq:
            counters[block] += 1
            vis = view == "visual"
            n_steps, lab = info[item]["n_steps"], labels[item]["step"]
            eta = logit(P["base"]) + u + item_eff[item] + (slope if vis else 0) + (P["later_effect"] if info[item]["position_stratum"] == "later" else 0)
            p = sig(eta)
            timed = rng.random() < P["timeout_p"]
            follow = False
            if sstep is not None:
                if sstep == lab:
                    p = min(0.95, p + 0.25)
                else:
                    follow = rng.random() < max(0.0, P["follow_wrong"] + (P["follow_shift_visual"] if vis else 0))
            if timed:
                chosen = None
            elif follow:
                chosen = sstep
            elif rng.random() < p:
                chosen = lab
            else:
                others = [s for s in range(1, n_steps + 1) if s != lab]
                near = [s for s in others if abs(s - lab) == 1]
                chosen = int(rng.choice(near)) if near and rng.random() < 0.4 else int(rng.choice(others))
            correct = chosen == lab
            tms = 240000 if timed else int(min(239000, rng.lognormal(np.log(80000) + (-0.1 if vis else 0), 0.45)))
            conf = None if timed else int(np.clip(round(3 + 0.9 * correct + rng.normal(0, 0.9)), 1, 5))
            nsearch = int(rng.poisson(1.0)); ndet = int(rng.poisson(4)) if vis else 0
            rows.append(dict(participant=code, data_label="SIMULATED", session_id="SIM%d" % seed, list=a["list"], view_order=a["view_order"], block=block,
                             trial_index=counters[block], item=item, view=view, chosen_step=chosen if chosen is not None else np.nan, timed_out=timed, time_ms=tms,
                             confidence=conf if conf is not None else np.nan, suggestion_key=skey, suggestion_step=sstep if sstep is not None else np.nan,
                             suggestion_shown=sstep is not None, suggestion_accepted=(None if sstep is None or chosen is None else chosen == sstep),
                             n_search=nsearch, n_details=ndet, n_filter=int(rng.poisson(0.2)), n_scroll=int(rng.poisson(3)), n_expand=int(rng.poisson(0.5)),
                             events=json.dumps([]), app_version="SIMULATED", timestamp="SIMULATED"))
        for v in ("console", "visual"):
            vis = v == "visual"
            sc = {d: int(np.clip(round(rng.normal(55 - (6 if vis else 0), 18) / 5) * 5, 0, 100)) for d in ("mental", "physical", "temporal", "performance", "effort", "frustration")}
            tlx.append(dict(participant=code, data_label="SIMULATED", session_id="SIM%d" % seed, view=v, block="A", **sc, raw_tlx=sum(sc.values()) / 6, timestamp="SIMULATED"))
    truth = dict(SIMULATED=True, seed=seed, n_participants=n, view_effect_logit=beta, **P)
    return pd.DataFrame(rows)[trial_io.TRIAL_COLS], pd.DataFrame(tlx)[trial_io.TLX_COLS], truth


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    res, out = sys.argv[1], pathlib.Path(sys.argv[2])
    if "simulated" not in str(out).lower():
        sys.exit("refusing to write simulated data outside a folder named simulated")
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 20261201
    beta = float(sys.argv[5]) if len(sys.argv) > 5 else 0.8
    out.mkdir(parents=True, exist_ok=True)
    t, x, truth = simulate(res, n, seed, beta)
    t.to_csv(out / "trials_SIMULATED.csv", index=False)
    x.to_csv(out / "tlx_SIMULATED.csv", index=False)
    (out / "sim_truth_SIMULATED.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    print("SIMULATED: %d participants, %d trials, injected view effect %.2f logit, seed %d" % (n, len(t), beta, seed))
