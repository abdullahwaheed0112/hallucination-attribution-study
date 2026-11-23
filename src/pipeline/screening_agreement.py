"""Screening agreement: Cohen's kappa between the two screeners, each screener's agreement with the label,
and the items where both differ from the label by more than one step.

Usage:
  python -I src/pipeline/screening_agreement.py <screener_A.csv> <screener_B.csv> <out folder>
      -> screener-versus-screener agreement only. The label file is NOT opened.
  python -I src/pipeline/screening_agreement.py A.csv B.csv <out folder> --labels <labels.json> --confirm-both-finished
      -> adds the comparison with the labels. Run this only after both screenings are finished and saved.

Input: the "Screening CSV" downloads from the app (columns screener, item, index, reserve, practice_item, chosen_step,
no_step_found, final_answer_correct, offensive_or_personal, ambiguous, comment, ...). If an item appears twice for a screener the
last row counts. Practice items (their labels were shown as practice feedback) are left out of every agreement figure.
Scored set = non-practice, non-reserve items that both screeners finished. Reserves are reported separately.
"""
import argparse
import csv
import json
import pathlib
import sys


def read(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["item"]] = r
    return rows


def truth(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def choice(r):
    """A step number, or 'none' when the screener found no step."""
    if truth(r.get("no_step_found")) or str(r.get("chosen_step", "")).strip() in ("", "nan"):
        return "none"
    return int(float(r["chosen_step"]))


def kappa(a, b):
    """Cohen's kappa for two lists of nominal labels. Returns (kappa, observed agreement, expected agreement)."""
    n = len(a)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    cats = sorted(set(a) | set(b), key=str)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((sum(x == c for x in a) / n) * (sum(y == c for y in b) / n) for c in cats)
    return (float("nan") if pe == 1 else (po - pe) / (1 - pe)), po, pe


def within1(x, y):
    return x != "none" and y != "none" and abs(x - y) <= 1


def main(a_path, b_path, out, labels_path=None):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    A, B = read(a_path), read(b_path)
    nameA = next(iter(A.values()))["screener"] if A else "A"
    nameB = next(iter(B.values()))["screener"] if B else "B"
    both = [i for i in A if i in B]
    prac = {i for i in both if truth(A[i].get("practice_item")) or truth(B[i].get("practice_item"))}
    res = {i for i in both if i not in prac and (truth(A[i].get("reserve")) or truth(B[i].get("reserve")))}
    scored = [i for i in both if i not in prac and i not in res]
    lines = ["# Screening agreement", "", "Screeners: %s and %s. Items finished by both: %d (scored: %d; reserves: %d; practice items left out: %d)." % (nameA, nameB, len(both), len(scored), len(res), len(prac)), ""]
    summary = {"screener_a": nameA, "screener_b": nameB, "n_scored": len(scored), "n_reserves": len(res), "n_practice_left_out": len(prac)}
    for label, ids in (("scored items", scored), ("reserves", sorted(res))):
        a, b = [choice(A[i]) for i in ids], [choice(B[i]) for i in ids]
        k, po, pe = kappa(a, b)
        w1 = sum(within1(x, y) for x, y in zip(a, b)) / len(ids) if ids else float("nan")
        summary[label] = dict(n=len(ids), kappa=k, exact_agreement=po, chance_agreement=pe, agreement_within_1=w1)
        lines.append("## %s versus %s on %s (n = %d)" % (nameA, nameB, label, len(ids)))
        lines.append("")
        lines.append("Cohen's kappa (exact step, 'no step found' counts as a category): %.3f; exact agreement %.3f; chance agreement %.3f; agreement within one step %.3f." % (k, po, pe, w1))
        lines.append("")
    flags = []
    for i in scored + sorted(res):
        f = [n for n, key in (("ambiguous", "ambiguous"), ("final answer appears correct", "final_answer_correct"), ("offensive or personal", "offensive_or_personal")) if truth(A[i].get(key)) or truth(B[i].get(key))]
        if f:
            flags.append((i, "; ".join(f)))
    lines += ["## Items flagged by either screener", ""] + (["- %s: %s" % x for x in flags] or ["- none"]) + [""]
    per_item = [dict(item=i, set="scored" if i in scored else "reserve", **{nameA: choice(A[i]), nameB: choice(B[i])}) for i in scored + sorted(res)]
    if labels_path:
        labels = json.loads(pathlib.Path(labels_path).read_text(encoding="utf-8"))["labels"]
        lines += ["## Agreement with the label (labels file opened after both screenings finished)", ""]
        for name, R in ((nameA, A), (nameB, B)):
            for label, ids in (("scored items", scored), ("reserves", sorted(res))):
                ids = [i for i in ids if i in labels]
                ch = [choice(R[i]) for i in ids]
                lab = [labels[i]["step"] for i in ids]
                ex = sum(c == l for c, l in zip(ch, lab)) / len(ids) if ids else float("nan")
                tol = sum(within1(c, l) for c, l in zip(ch, lab)) / len(ids) if ids else float("nan")
                k = kappa(ch, lab)[0]
                summary.setdefault("vs_label", {})["%s|%s" % (name, label)] = dict(n=len(ids), exact=ex, within_1=tol, kappa=k)
                lines.append("- %s on %s (n = %d): exact %.3f, within one step %.3f, kappa %.3f" % (name, label, len(ids), ex, tol, k))
        lines.append("")
        both_far = []
        for i in scored + sorted(res):
            if i not in labels:
                continue
            L = labels[i]["step"]
            ca, cb = choice(A[i]), choice(B[i])
            far = lambda c: c == "none" or abs(c - L) > 1
            if far(ca) and far(cb):
                both_far.append((i, L, ca, cb))
        summary["both_differ_by_more_than_1"] = [x[0] for x in both_far]
        lines += ["## Items where both screeners differ from the label by more than one step (excluded from the confirmatory analysis, not removed silently)", ""]
        lines += ["- %s: label %s, %s chose %s, %s chose %s" % (i, L, nameA, ca, nameB, cb) for i, L, ca, cb in both_far] or ["- none"]
        lines.append("")
        for r in per_item:
            r["label"] = labels.get(r["item"], {}).get("step")
    else:
        lines += ["Label comparison not run (no --labels with --confirm-both-finished).", ""]
    with open(out / "screening_agreement_items.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["item", "set", nameA, nameB] + (["label"] if labels_path else [])
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(per_item)
    (out / "screening_agreement.md").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    (out / "screening_agreement.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(chr(10).join(lines))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("screener_a"); ap.add_argument("screener_b"); ap.add_argument("out")
    ap.add_argument("--labels"); ap.add_argument("--confirm-both-finished", action="store_true")
    a = ap.parse_args()
    if a.labels and not a.confirm_both_finished:
        sys.exit("Refusing to open the label file: pass --confirm-both-finished only after both screenings are finished and saved.")
    if a.confirm_both_finished and not a.labels:
        sys.exit("--confirm-both-finished needs --labels <file>.")
    main(a.screener_a, a.screener_b, a.out, a.labels if a.confirm_both_finished else None)
