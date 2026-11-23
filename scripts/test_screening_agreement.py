"""Test of src/pipeline/screening_agreement.py on SYNTHETIC files written to a scratch folder (never to results/).

Usage: python -P -E scripts/test_screening_agreement.py <scratch folder>
Checks: kappa and agreement against values computed by hand-written, separate code; the both-differ list; the label gate
(the script must refuse --labels without --confirm-both-finished, and must not open a labels path in screener-only mode);
the practice and reserve handling; the real labels file is not touched.
"""
import csv
import json
import pathlib
import subprocess
import sys

scratch = pathlib.Path(sys.argv[1])
scratch.mkdir(parents=True, exist_ok=True)
script = pathlib.Path(__file__).resolve().parents[1] / "src" / "pipeline" / "screening_agreement.py"
COLS = ["screener", "item", "index", "reserve", "practice_item", "chosen_step", "no_step_found", "time_ms", "confidence", "final_answer_correct", "offensive_or_personal", "ambiguous", "comment"]

# 10 scored items, 1 practice item, 2 reserves. Synthetic labels.
labels = {"S%02d" % i: l for i, l in enumerate([1, 3, 3, 3, 1, 4, 5, 3, 6, 3], start=1)}
labels.update({"SP1": 3, "SR1": 3, "SR2": 4})
A = [1, 3, 3, 3, 1, 4, 6, 3, 2, 3]
B = [1, 3, 2, 3, 1, 4, 6, 3, 9, "none"]


def write(path, name, picks, extra):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for i, p in enumerate(picks, start=1):
            w.writerow(dict(screener=name, item="S%02d" % i, index=i, reserve=False, practice_item=False, chosen_step="" if p == "none" else p, no_step_found=p == "none",
                            time_ms=1000, confidence=3, final_answer_correct=False, offensive_or_personal=False, ambiguous=(name == "AA" and i == 2), comment=""))
        for item, p, res, prac in extra:
            w.writerow(dict(screener=name, item=item, index=99, reserve=res, practice_item=prac, chosen_step=p, no_step_found=False, time_ms=1000, confidence=3,
                            final_answer_correct=False, offensive_or_personal=False, ambiguous=False, comment=""))


write(scratch / "screen_AA.csv", "AA", A, [("SP1", 3, False, True), ("SR1", 3, True, False), ("SR2", 9, True, False)])
write(scratch / "screen_BB.csv", "BB", B, [("SP1", 1, False, True), ("SR1", 3, True, False), ("SR2", 4, True, False)])
(scratch / "labels_SYNTHETIC.json").write_text(json.dumps({"labels": {k: {"step": v} for k, v in labels.items()}}), encoding="utf-8")

# ---- independent expectations (separate code from the script under test)
n = len(A)
agree = sum(1 for x, y in zip(A, B) if x == y)
cats = set(A) | set(B)
pa = {c: A.count(c) / n for c in cats}
pb = {c: B.count(c) / n for c in cats}
po = agree / n
pe = sum(pa[c] * pb[c] for c in cats)
kap = (po - pe) / (1 - pe)
within = sum(1 for x, y in zip(A, B) if isinstance(y, int) and abs(x - y) <= 1) / n
lab = [labels["S%02d" % i] for i in range(1, 11)]
exA = sum(1 for x, l in zip(A, lab) if x == l) / n
exB = sum(1 for y, l in zip(B, lab) if y == l) / n
tolA = sum(1 for x, l in zip(A, lab) if abs(x - l) <= 1) / n
tolB = sum(1 for y, l in zip(B, lab) if y != "none" and abs(y - l) <= 1) / n
both = [i for i in range(10) if abs(A[i] - lab[i]) > 1 and (B[i] == "none" or abs(B[i] - lab[i]) > 1)]
print("hand-computed: kappa %.4f, exact agreement %.2f, chance %.4f, within 1 %.2f; vs label A %.2f/%.2f B %.2f/%.2f; both differ: %s" % (kap, po, pe, within, exA, tolA, exB, tolB, ["S%02d" % (i + 1) for i in both]))

fails = []
def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)

run = lambda *args: subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True, text=True)
# 1. screener-versus-screener only, with a labels path that does not exist: must not try to open it
r = run(str(scratch / "screen_AA.csv"), str(scratch / "screen_BB.csv"), str(scratch / "out1"))
check("screener-only run succeeds", r.returncode == 0)
s = json.loads((scratch / "out1" / "screening_agreement.json").read_text())
check("kappa equals hand computation", abs(s["scored items"]["kappa"] - kap) < 1e-9)
check("exact agreement equals hand computation", abs(s["scored items"]["exact_agreement"] - po) < 1e-9)
check("chance agreement equals hand computation", abs(s["scored items"]["chance_agreement"] - pe) < 1e-9)
check("agreement within 1 equals hand computation", abs(s["scored items"]["agreement_within_1"] - within) < 1e-9)
check("practice item left out, reserves separate", s["n_practice_left_out"] == 1 and s["n_scored"] == 10 and s["n_reserves"] == 2)
check("no label section in screener-only output", "both_differ_by_more_than_1" not in s and "vs_label" not in s)
# 2. gate: --labels without the confirm flag must refuse, even for a path that does not exist
r = run(str(scratch / "screen_AA.csv"), str(scratch / "screen_BB.csv"), str(scratch / "out2"), "--labels", str(scratch / "does_not_exist.json"))
check("--labels without --confirm-both-finished is refused", r.returncode != 0 and "Refusing to open the label file" in (r.stderr + r.stdout) and not (scratch / "out2").exists())
# 3. with the flag: reads the synthetic labels
r = run(str(scratch / "screen_AA.csv"), str(scratch / "screen_BB.csv"), str(scratch / "out3"), "--labels", str(scratch / "labels_SYNTHETIC.json"), "--confirm-both-finished")
check("run with labels and confirm flag succeeds", r.returncode == 0)
s = json.loads((scratch / "out3" / "screening_agreement.json").read_text())
check("agreement with label (screener AA) equals hand computation", abs(s["vs_label"]["AA|scored items"]["exact"] - exA) < 1e-9 and abs(s["vs_label"]["AA|scored items"]["within_1"] - tolA) < 1e-9)
check("agreement with label (screener BB) equals hand computation", abs(s["vs_label"]["BB|scored items"]["exact"] - exB) < 1e-9 and abs(s["vs_label"]["BB|scored items"]["within_1"] - tolB) < 1e-9)
check("both-differ list equals hand computation", s["both_differ_by_more_than_1"] == ["S%02d" % (i + 1) for i in both])
check("reserve SR2 (A differs, B matches) is not in the both-differ list", "SR2" not in s["both_differ_by_more_than_1"])
check("ambiguous flag from screener AA is reported", "S02: ambiguous" in (scratch / "out3" / "screening_agreement.md").read_text())
# 4. the real label file is not named anywhere in the script
check("script never mentions labels_PRIVATE", "labels_PRIVATE" not in script.read_text(encoding="utf-8"))
print("\nALL PASS" if not fails else "\nFAILED: %s" % fails)
sys.exit(1 if fails else 0)
