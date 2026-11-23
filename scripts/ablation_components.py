"""E3 pilot component use (definition: docs/ablation_definitions.md). Correlational, descriptive, no inference.

Usage: python -P -E scripts/ablation_components.py <trials file> <results folder> <out folder>
Block A trials in the visual view. 'used search' = n_search > 0; 'opened more than one step' = n_details >= 2 (answering in the
visual view needs one step open, so one opening is not a use of the panel beyond the answer); 'used filter' = n_filter > 0.
If the data are SIMULATED the output names carry SIMULATED and the banner; otherwise output is a plain descriptive table.
"""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trial_io  # noqa: E402

SCOPE = "E3: visual-view Block A trials; correlational only (people who use a component may be those who found the trial hard); descriptive, no p-values, no intervals"


def main(trials, results, out):
    df = trial_io.load_trials(trials)
    err, _ = trial_io.validate(df, results)
    if err:
        sys.exit("schema errors: %s" % err[:3])
    sim = set(df["data_label"].astype(str)) == {"SIMULATED"}
    d = trial_io.score(df, results)
    V = d[(d["block"] == "A") & (d["view"] == "visual")]
    rows = []
    for name, flag in (("used search", V["n_search"] > 0), ("opened more than one step", V["n_details"] >= 2), ("used agent filter", V["n_filter"] > 0)):
        for used, g in V.groupby(flag):
            rows.append(dict(label=("SIMULATED - pipeline test only" if sim else "descriptive"), scope=SCOPE, component=name, used=bool(used), n_trials=len(g),
                             n_participants=g["participant"].nunique(), exact_acc=round(g["correct"].mean(), 3) if len(g) else None,
                             median_time_s=round(g["time_s"].median(), 1) if len(g) else None))
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    name = "ablation_E3_components_SIMULATED.csv" if sim else "ablation_E3_components_%s.csv" % "_".join(sorted(set(df["data_label"].astype(str))))
    pd.DataFrame(rows).to_csv(out / name, index=False)
    print(name); print(pd.DataFrame(rows).drop(columns=["scope"]).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    if "SIMULATED" in sys.argv[1] and "simulated" not in sys.argv[3].lower():
        sys.exit("simulated input must write to the simulated folder")
    main(*sys.argv[1:])
