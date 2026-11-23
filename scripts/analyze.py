"""M2 metrics, models and error classification for any trial-level file in the app schema.

Usage: python -P -E scripts/analyze.py <trials.csv|all.json> <results folder> <out folder> [--tlx file] [--seed 20261201]

Modes (decided from the data_label column, never from a flag):
  SIMULATED  -> full inference, every output named *SIMULATED* and stamped "SIMULATED - pipeline test only"
  anything else (PILOT, TEST, ...) -> descriptive only: no p-values, no intervals, no model fits
Model fallback order (fixed in docs/decisions_log.md before any run):
  1 BinomialBayesMixedGLM with participant, participant-by-view and item terms; 2 the same without the slope term; 3 GEE by participant.
"""
import argparse
import json
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402

SIM_BANNER = "SIMULATED - pipeline test only"
BOOT = 5000


def mode_of(df):
    labels = set(df["data_label"].astype(str))
    if labels == {"SIMULATED"}:
        return "simulated"
    return "descriptive"


# ---------------------------------------------------------------- metrics
def brier(g):
    g = g[g["conf01"].notna()]
    return float(((g["conf01"] - g["correct"]) ** 2).mean()) if len(g) else np.nan


def summarize(g):
    return pd.Series({
        "n_trials": len(g), "n_participants": g["participant"].nunique(),
        "exact_acc": g["correct"].mean(), "agent_acc": g["agent_correct"].mean(), "tolerant_acc": g["tolerant"].mean(),
        "mean_signed_error": g["signed_error"].mean(), "median_time_s": g["time_s"].median(), "brier": brier(g),
        "timeouts": int((g["error_type"] == "timeout").sum()), "mean_confidence": g["confidence"].mean(),
    })


def metrics_tables(d):
    A = d[d["block"] == "A"]
    out = {}
    out["metrics_by_view"] = A.groupby("view").apply(summarize, include_groups=False).reset_index()
    parts = []
    for col in ("position", "length"):
        t = A.groupby([col, "view"]).apply(summarize, include_groups=False).reset_index().rename(columns={col: "stratum"})
        t.insert(0, "stratum_type", col)
        parts.append(t)
    out["metrics_by_view_and_stratum"] = pd.concat(parts, ignore_index=True)
    B = d[d["block"] == "B"]
    if len(B):
        rows = []
        for (v, sc), g in B.groupby(["view", "suggestion_correct"]):
            rows.append(dict(view=v, suggestion="correct" if sc == 1 else "incorrect", n=len(g), accuracy_exact=g["correct"].mean(),
                             chose_suggested=g["accepted"].mean()))
        t = pd.DataFrame(rows)
        t["measure_note"] = np.where(t["suggestion"] == "incorrect", "chose_suggested = overreliance (copied a wrong suggestion)", "chose_suggested = agreement; 1 - this = rejected a right suggestion")
        out["block_b_agreement"] = t
    E = d[d["block"].isin(["A", "B"])]
    e = E.groupby(["block", "view", "error_type"]).size().rename("n").reset_index()
    e["share_of_trials_in_cell"] = e["n"] / e.groupby(["block", "view"])["n"].transform("sum")
    out["error_classes"] = e
    sig = E[E["signed_error"].notna() & (E["correct"] == 0)]
    out["signed_error_wrong_answers"] = sig.groupby("view")["signed_error"].describe().reset_index() if len(sig) else pd.DataFrame()
    return out


def participant_table(A):
    """Per participant x view accuracy and other outcomes (Block A), wide."""
    g = A.groupby(["participant", "view"])
    t = pd.DataFrame({"exact": g["correct"].mean(), "agent": g["agent_correct"].mean(), "tolerant": g["tolerant"].mean(),
                      "logtime": g["time_s"].apply(lambda x: np.log(x).mean()), "brier": g.apply(brier, include_groups=False)}).unstack("view")
    return t


# ---------------------------------------------------------------- inference
def fit_primary(A):
    """Fallback order: 1 VB mixed GLM with slope, 2 without slope, 3 GEE. Returns a dict describing the fit used."""
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    tried = []
    for name, vc in (("1: VB mixed GLM, participant + participant-by-view + item", {"participant": "0 + C(participant)", "pv": "0 + C(participant):view_visual", "item": "0 + C(item)"}),
                     ("2: VB mixed GLM, participant + item (no slope)", {"participant": "0 + C(participant)", "item": "0 + C(item)"})):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = BinomialBayesMixedGLM.from_formula("correct ~ view_visual", vc, A).fit_vb()
            names = list(r.model.exog_names)
            m, s = float(r.fe_mean[names.index("view_visual")]), float(r.fe_sd[names.index("view_visual")])
            if not (np.isfinite(m) and np.isfinite(s) and s > 0):
                raise ValueError("non-finite estimate")
            return dict(model=name, interval_type="posterior (variational Bayes), not a frequentist confidence interval", log_odds=m, sd=s,
                        odds_ratio=float(np.exp(m)), or_low=float(np.exp(m - 1.96 * s)), or_high=float(np.exp(m + 1.96 * s)), tried=tried)
        except Exception as ex:
            tried.append("%s failed: %s" % (name, str(ex)[:80]))
    r = smf.gee("correct ~ view_visual", "participant", A, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    m, s = float(r.params["view_visual"]), float(r.bse["view_visual"])
    return dict(model="3: GEE (binomial, exchangeable, by participant)", interval_type="robust 95% confidence interval", log_odds=m, sd=s, odds_ratio=float(np.exp(m)),
                or_low=float(np.exp(m - 1.96 * s)), or_high=float(np.exp(m + 1.96 * s)), tried=tried)


def paired_block(A, seed):
    w = A.groupby(["participant", "view"])["correct"].mean().unstack("view").dropna()
    diff = (w["visual"] - w["console"]).to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([rng.choice(diff, len(diff), replace=True).mean() for _ in range(BOOT)])
    out = dict(n_participants=int(len(diff)), mean_diff_visual_minus_console=float(diff.mean()), bootstrap_95ci=[float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
               bootstrap_seed=seed, bootstrap_resamples=BOOT)
    t = stats.ttest_rel(w["visual"], w["console"])
    out.update(paired_t=float(t.statistic), paired_t_p=float(t.pvalue))
    try:
        out["wilcoxon_p"] = float(stats.wilcoxon(diff, zero_method="wilcox").pvalue)
    except ValueError as ex:
        out["wilcoxon_p"] = None
        out["wilcoxon_note"] = str(ex)[:80]
    return out


def secondary(A, tlx):
    wide = participant_table(A)
    rows = []
    for key, label in (("agent", "agent accuracy"), ("tolerant", "tolerant accuracy"), ("logtime", "mean log time (s)"), ("brier", "Brier score")):
        v = wide[key].dropna()
        if len(v) > 2:
            t = stats.ttest_rel(v["visual"], v["console"])
            rows.append(dict(outcome=label, mean_console=float(v["console"].mean()), mean_visual=float(v["visual"].mean()), paired_t_p=float(t.pvalue)))
    if tlx is not None and len(tlx):
        w = tlx.groupby(["participant", "view"])["raw_tlx"].mean().unstack("view").dropna()
        if len(w) > 2:
            t = stats.ttest_rel(w["visual"], w["console"])
            rows.append(dict(outcome="raw NASA-TLX", mean_console=float(w["console"].mean()), mean_visual=float(w["visual"].mean()), paired_t_p=float(t.pvalue)))
    df = pd.DataFrame(rows)
    if len(df):
        from statsmodels.stats.multitest import multipletests
        df["holm_p"] = multipletests(df["paired_t_p"], method="holm")[1]
    return df


def exploratory(d):
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    out = {}
    A = d[d["block"] == "A"].copy()
    A["later"] = (A["position"] == "later").astype(int)
    A["words_z"] = (A["words"] - A["words"].mean()) / A["words"].std()
    try:
        r = smf.gee("correct ~ view_visual * later + view_visual * words_z", "participant", A, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        out["H3_gee_view_x_position_and_length"] = {k: dict(log_odds=float(r.params[k]), se=float(r.bse[k]), p=float(r.pvalues[k])) for k in r.params.index}
    except Exception as ex:
        out["H3_gee_view_x_position_and_length"] = "failed: " + str(ex)[:80]
    try:
        with warnings.catch_warnings(record=True) as wl:
            warnings.simplefilter("always")
            r = smf.mixedlm("np.log(time_s) ~ view_visual", A, groups=A["participant"]).fit()
        out["log_time_mixedlm"] = dict(view_coef=float(r.params["view_visual"]), se=float(r.bse["view_visual"]), p=float(r.pvalues["view_visual"]),
                                       converged=bool(r.converged), warnings=sorted({str(w.message)[:70] for w in wl}))
    except Exception as ex:
        out["log_time_mixedlm"] = "failed: " + str(ex)[:80]
    B = d[d["block"] == "B"].copy()
    if len(B) > 20:
        try:
            r = smf.gee("correct ~ suggestion_correct * view_visual", "participant", B, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
            out["block_B_gee_suggestion_x_view"] = {k: dict(log_odds=float(r.params[k]), se=float(r.bse[k]), p=float(r.pvalues[k])) for k in r.params.index}
        except Exception as ex:
            out["block_B_gee_suggestion_x_view"] = "failed: " + str(ex)[:80]
    return out


# ---------------------------------------------------------------- main
def main(trials, results, outdir, tlx_path=None, seed=20261201):
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    df = trial_io.load_trials(trials)
    err, warn = trial_io.validate(df, results)
    if err:
        print("SCHEMA ERRORS - stopping:")
        [print("  " + e) for e in err]
        return 1
    mode = mode_of(df)
    stem = pathlib.Path(trials).stem
    if mode == "simulated" and "SIMULATED" not in stem:
        print("simulated data must be in a file whose name contains SIMULATED")
        return 1
    d = trial_io.score(df, results)
    tlx = trial_io.load_tlx(tlx_path) if tlx_path else None
    banner = SIM_BANNER if mode == "simulated" else "%s (n = %d) - descriptive only: no p-values, no intervals" % ("/".join(sorted(set(df["data_label"].astype(str)))), df["participant"].nunique())
    tables = metrics_tables(d)
    written = []
    for name, t in tables.items():
        if mode == "simulated":
            t = t.copy(); t.insert(0, "label", SIM_BANNER)
        f = out / ("%s__%s.csv" % (stem, name))
        t.to_csv(f, index=False)
        written.append(f.name)
    if tlx is not None and len(tlx):
        t = tlx.groupby("view")[["mental", "physical", "temporal", "performance", "effort", "frustration", "raw_tlx"]].mean().reset_index()
        if mode == "simulated":
            t.insert(0, "label", SIM_BANNER)
        t.to_csv(out / ("%s__tlx_by_view.csv" % stem), index=False)
        written.append("%s__tlx_by_view.csv" % stem)
    res = {"banner": banner, "mode": mode, "input": pathlib.Path(trials).name, "schema_warnings": warn[:20]}
    if mode == "simulated":
        A = d[d["block"] == "A"]
        res["primary_model"] = fit_primary(A)
        res["paired_and_bootstrap"] = paired_block(A, seed)
        res["secondary_outcomes_holm"] = secondary(A, tlx).to_dict("records")
        res["exploratory"] = exploratory(d)
        if (out / "dummy").exists():
            pass
    else:
        res["inference"] = "switched off: data_label is not SIMULATED, so no model, p-value or interval is computed (the project instructions rule 3)"
    (out / ("%s__results.json" % stem)).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    written.append("%s__results.json" % stem)
    md = ["# " + banner, "", "Input: %s. Tables written: %s." % (pathlib.Path(trials).name, ", ".join(written)), "", "## Block A by view", "", trial_io.md_table(tables["metrics_by_view"].round(3))]
    if mode == "simulated":
        pm = res["primary_model"]
        md += ["", "## Primary model (%s)" % pm["model"], "", "Odds ratio visual vs console: %.2f (%s %.2f to %.2f). Interval type: %s." % (pm["odds_ratio"], "95%", pm["or_low"], pm["or_high"], pm["interval_type"])]
    (out / ("%s__summary.md" % stem)).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(banner)
    print(tables["metrics_by_view"].round(3).to_string(index=False))
    if mode == "simulated":
        print(json.dumps({k: res[k] for k in ("primary_model", "paired_and_bootstrap")}, indent=1, default=str))
    else:
        print(res["inference"])
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trials"); ap.add_argument("results"); ap.add_argument("out")
    ap.add_argument("--tlx"); ap.add_argument("--seed", type=int, default=20261201)
    a = ap.parse_args()
    sys.exit(main(a.trials, a.results, a.out, a.tlx, a.seed))
