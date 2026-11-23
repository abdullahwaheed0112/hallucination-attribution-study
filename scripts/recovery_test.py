"""Simulator recovery test: does the primary model recover a known injected view effect? Run this before any model touches real or pilot data.

Usage: python -P -E scripts/recovery_test.py <results folder> <simulated out folder>
Pass rule, fixed before the first run (written in docs/decisions_log.md):
  Large-sample check: N = 200 simulated participants, 5 seeds, for injected effects 0.0 and 0.8 logit.
    PASS if the mean estimate is within 0.15 of the truth AND the 95% interval covers the truth in at least 4 of 5 seeds.
  Planned-size check (reported, no pass rule): N = 32, 20 seeds, same two effects: how often the interval covers the truth,
    how often it excludes 0, and which model of the fallback order was used.
All output is SIMULATED and written only to the simulated folder.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze  # noqa: E402
import simulate_trials  # noqa: E402
import trial_io  # noqa: E402

BANNER = "SIMULATED - pipeline test only"


def one(results, n, seed, beta):
    t, _, _ = simulate_trials.simulate(results, n=n, seed=seed, beta=beta)
    d = trial_io.score(t, results)
    A = d[d["block"] == "A"]
    r = analyze.fit_primary(A)
    return dict(n=n, seed=seed, truth=beta, estimate=r["log_odds"], sd=r["sd"], low=np.log(r["or_low"]), high=np.log(r["or_high"]), model=r["model"][:1])


def main(results, out):
    out = pathlib.Path(out)
    if "simulated" not in str(out).lower():
        sys.exit("write only to the simulated folder")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for beta in (0.0, 0.8):
        for s in range(5):
            rows.append(one(results, 200, 777000 + s, beta))
    big = pd.DataFrame(rows)
    verdicts = []
    for beta, g in big.groupby("truth"):
        mean_est = g["estimate"].mean()
        cover = int(((g["low"] <= beta) & (beta <= g["high"])).sum())
        ok = abs(mean_est - beta) <= 0.15 and cover >= 4
        verdicts.append(dict(truth=beta, mean_estimate=mean_est, abs_error=abs(mean_est - beta), covered_of_5=cover, models_used="".join(sorted(set(g["model"]))), verdict="PASS" if ok else "FAIL"))
    v = pd.DataFrame(verdicts)
    rows = []
    for beta in (0.0, 0.8):
        for s in range(20):
            rows.append(one(results, 32, 888000 + s, beta))
    small = pd.DataFrame(rows)
    summ = []
    for beta, g in small.groupby("truth"):
        summ.append(dict(truth=beta, mean_estimate=g["estimate"].mean(), sd_of_estimates=g["estimate"].std(),
                         interval_covers_truth=int(((g["low"] <= beta) & (beta <= g["high"])).sum()), interval_excludes_zero=int(((g["low"] > 0) | (g["high"] < 0)).sum()), of=len(g),
                         models_used="".join(sorted(set(g["model"])))))
    s = pd.DataFrame(summ)
    for name, t in (("large", big), ("small", small)):
        t.insert(0, "label", BANNER)
        t.to_csv(out / ("recovery_%s_runs_SIMULATED.csv" % name), index=False)
    text = ["# " + BANNER, "", "## Large-sample check (N = 200, 5 seeds per truth; pass rule in the script header)", "", trial_io.md_table(v.round(3)), "",
            "## Planned-size check (N = 32, 20 seeds per truth)", "", trial_io.md_table(s.round(3)), "",
            "Estimates are log odds of the visual view. Intervals are posterior intervals from the model that was used (1 = VB mixed GLM with slope, 2 = without slope, 3 = GEE)."]
    (out / "recovery_test_SIMULATED.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0 if (v["verdict"] == "PASS").all() else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
