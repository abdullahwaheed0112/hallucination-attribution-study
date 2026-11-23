"""Check the numbers in paper/paper.tex against saved result files.

Part 1: explicit checks (each claim in the paper recomputed from a results file).
Part 2: every other number in the paper text is searched for in results/ and docs/;
        numbers with no match are listed for manual review.
Run:  python -P -E scripts/check_paper.py   (from the project folder)
Reads only our own files (results/, docs/, paper/), never data/.
"""
import csv, json, pathlib, re, statistics, sys

ROOT = pathlib.Path(".")
R = ROOT / "results"
fails, passes = [], 0


def check(name, got, want, tol=0.0006):
    global passes
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if ok:
        passes += 1
    else:
        fails.append("%s: paper says %s, files give %s" % (name, want, got))
    print(("PASS " if ok else "FAIL ") + name, got)


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---- baselines (Table III, text) ----
base = {(r["item_set"], r["method"].split(" (")[0]): r for r in rows(R / "baselines.csv")}
want = {  # item_set: {method: (exact, agent, tolerant) in %}
    "pool_82": {"chance": (16.5, 50.9, 43.5), "always step 1": (22.0, 29.3, 23.2), "always step 3": (56.1, 69.5, 62.2)},
    "block_a_24": {"chance": (16.3, 56.1, 39.5), "always step 1": (25.0, 41.7, 29.2), "always step 3": (20.8, 54.2, 37.5)},
    "block_b_8": {"chance": (12.2, 45.4, 34.3), "always step 1": (25.0, 37.5, 25.0), "always step 3": (25.0, 62.5, 37.5)},
    "selected_34": {"chance": (15.3, 51.7, 38.3), "always step 1": (26.5, 41.2, 29.4), "always step 3": (23.5, 55.9, 38.2)},
}
for s, d in want.items():
    for m, vals in d.items():
        r = base[(s, m)]
        got = tuple(100 * float(r[k]) for k in ("exact_acc", "agent_acc", "tolerant_acc_pm1"))
        # baselines.csv stores 4 decimals (0.2195 for 18/82 = 21.95%), so allow 0.06 points
        ok = all(abs(g - v) <= 0.06 for g, v in zip(got, vals))
        check("baseline %s %s" % (s, m), ok, True)
pub = [r for r in rows(R / "baselines.csv") if r["item_set"] == "published"][0]
check("published LLM exact", round(100 * float(pub["exact_acc"]), 1), 41.1)
for (s, m), ex in {("block_a_24|early", "always step 1"): 50.0, ("block_a_24|early", "always step 3"): 41.7,
                   ("block_a_24|later", "always step 1"): 0.0, ("block_a_24|later", "always step 3"): 0.0}.items():
    check("stratum %s %s" % (s, m), round(100 * float(base[(s, m)]["exact_acc"]), 1), ex)

# ---- pool and selection ----
pc = (R / "pool_check.txt").read_text(encoding="utf-8")
for key, v in [("hallucination present = ", 111), ("<= 20 steps = ", 104), ("<= 3000 words = ", 83),
               ("responsible role known = ", 82), ("unique question = ", 82)]:
    check("pool filter " + key, int(re.search(re.escape(key) + r"(\d+)", pc).group(1)), v)
for label, v in [("Magentic_One", 47), ("Camel", 35), ("step 3 labels", 46), ("later items below median", 6), ("later items", 17)]:
    check("pool " + label, int(re.search(re.escape(label) + r"\s+M2 (\d+)", pc).group(1)), v)
check("pool median words", float(re.search(r"median words\s+M2 ([\d.]+)", pc).group(1)), 1135.5)
sc = (R / "selection_check.txt").read_text(encoding="utf-8")
check("Block A frameworks Camel", int(re.search(r"'Camel': (\d+)", sc).group(1)), 8)
check("Block A frameworks Magentic", int(re.search(r"'Magentic_One': (\d+)", sc).group(1)), 16)
check("Block A step cap max count", max(int(x) for x in re.findall(r": (\d+)[,}]", re.search(r"Block A step numbers: (\{.*?\})", sc).group(1))), 6)
check("Block B wrong suggestion distances", re.search(r"distance \(suggested - label\): (\[.*?\])", sc).group(1), "[-3, -2, -2, -2, 2, 2, 3, 3]")
item_set = json.loads((R / "item_set.json").read_text(encoding="utf-8"))
print("item_set keys:", list(item_set)[:12])

# ---- screening ----
sa = json.loads((R / "screening" / "screening_agreement.json").read_text(encoding="utf-8"))
s = sa["scored items"]
check("kappa AW-AM scored", round(s["kappa"], 3), 0.261)
check("exact agreement", round(s["exact_agreement"], 3), 0.375)
check("chance agreement", round(s["chance_agreement"], 3), 0.154)
check("within one", round(s["agreement_within_1"], 3), 0.594)
check("kappa reserves", round(sa["reserves"]["kappa"], 3), 0.238)
check("AW exact", round(sa["vs_label"]["AW|scored items"]["exact"], 3), 0.250)
check("AW within1", round(sa["vs_label"]["AW|scored items"]["within_1"], 3), 0.375)
check("AM exact", round(sa["vs_label"]["AM|scored items"]["exact"], 3), 0.125)
check("AM within1", round(sa["vs_label"]["AM|scored items"]["within_1"], 3), 0.281)
items = rows(R / "screening" / "screening_agreement_items.csv")
sc_rows = [r for r in items if r["set"] == "scored"]
rs_rows = [r for r in items if r["set"] == "reserve" or r["set"].startswith("res")]
check("scored items", len(sc_rows), 32)
check("reserve items", len(rs_rows), 11)
flag = set(sa["both_differ_by_more_than_1"])
check("both differ scored", sum(r["item"] in flag for r in sc_rows), 18)
check("both differ reserves", sum(r["item"] in flag for r in rs_rows), 5)
def num(v):
    try:
        return int(v)
    except ValueError:
        return None
for who in ("AW", "AM"):
    later = sum(1 for r in sc_rows if num(r[who]) is not None and num(r[who]) > int(r["label"]))
    earlier = sum(1 for r in sc_rows if num(r[who]) is not None and num(r[who]) < int(r["label"]))
    print("  %s later=%d earlier=%d" % (who, later, earlier))
    check("%s later than label" % who, later, {"AW": 16, "AM": 21}[who])
    check("%s earlier than label" % who, earlier, 7)
tm = (R / "screening" / "screening_timing.md").read_text(encoding="utf-8")
check("timing AW median s", float(re.search(r"\| AW \| 45 \| [\d.]+ \| ([\d.]+)", tm).group(1)), 85.8)
check("timing AM median s", float(re.search(r"\| AM \| 45 \| [\d.]+ \| ([\d.]+)", tm).group(1)), 119.1)

# ---- pilot ----
mv = {r["view"]: r for r in rows(R / "pilot" / "analysis" / "pilot_P01_trials__metrics_by_view.csv")}
check("P01 console exact x6", round(6 * float(mv["console"]["exact_acc"])), 2)
check("P01 visual exact x6", round(6 * float(mv["visual"]["exact_acc"])), 1)
check("P01 console tolerant x6", round(6 * float(mv["console"]["tolerant_acc"])), 4)
check("P01 visual tolerant x6", round(6 * float(mv["visual"]["tolerant_acc"])), 1)
check("P01 console median s", round(float(mv["console"]["median_time_s"]), 1), 75.9)
check("P01 visual median s", round(float(mv["visual"]["median_time_s"]), 1), 52.8)
tl = {r["view"]: r for r in rows(R / "pilot" / "analysis" / "pilot_P01_trials__tlx_by_view.csv")}
check("P01 TLX console", round(float(tl["console"]["raw_tlx"]), 1), 56.7)
check("P01 TLX visual", round(float(tl["visual"]["raw_tlx"]), 1), 43.3)
p1 = rows(R / "pilot" / "pilot_P01_trials.csv")
check("P01 trials", len(p1), 18)
check("P01 confidence 5 count", sum(r["confidence"] == "5" for r in p1), 17)
p2 = rows(R / "pilot" / "pilot_p02_trials.csv")
check("P02 median time s", round(statistics.median(float(r["time_ms"]) for r in p2) / 1000, 1), 4.6)
e3 = rows(R / "pilot" / "ablation_E3_components_PILOT.csv")
for r in e3:
    print("  E3:", r["component"], r["used"], r["n_trials"])
p1v = [r for r in p1 if r["block"] == "A" and r["view"] == "visual"]
check("P01 visual Block A trials", len(p1v), 6)
check("P01 visual: used search", sum(int(r["n_search"]) > 0 for r in p1v), 0)
check("P01 visual: used filter", sum(int(r["n_filter"]) > 0 for r in p1v), 0)
check("P01 visual: opened >1 step every trial", sum(int(r["n_details"]) > 1 for r in p1v), 6)

# ---- ablations ----
e2 = {(r["item_set"], r["rule"]): r for r in rows(R / "ablation_E2_representation.csv")}
for (sname, rule), v in {("pool_82", "always step 3"): 56.1, ("pool_82", "first step by a non-coordinating agent"): 57.3,
                         ("pool_82", "first step with tool output"): 36.6, ("pool_82", "first step with a number not in the question"): 18.3,
                         ("block_a_24", "always step 3"): 20.8, ("block_a_24", "first step by a non-coordinating agent"): 25.0,
                         ("block_a_24", "first step with tool output"): 8.3, ("block_a_24", "first step with a number not in the question"): 16.7}.items():
    check("E2 %s %s" % (sname, rule), round(100 * float(e2[(sname, rule)]["exact"]), 1), v)
e1 = (R / "ablation_E1_item_features.md").read_text(encoding="utf-8")
check("E1 category alone, step1", float(re.search(r"always step 1 hits.*?\| category \| ([\d.]+)", e1, re.S).group(1)), 0.81)
check("E1 category alone, step3", float(re.search(r"always step 3 hits the label.*?\| category \| ([\d.]+)", e1, re.S).group(1)), 0.43, 0.006)
check("E1 position alone, step3", float(re.search(r"always step 3 hits the label.*?\| position \| ([\d.]+)", e1, re.S).group(1)), 0.33, 0.006)
check("E1 corr words vs 1/steps", float(re.search(r"corr\(words, 1/steps\) = (-?[\d.]+)", e1).group(1)), -0.64)
e2md = (R / "ablation_E2_representation.md").read_text(encoding="utf-8")
check("E2 empty-message steps", "35 of 82" in e2md, True)
check("E2 speaker change lost", "4 of 82" in e2md, True)

# ---- self-test, power, seeds, versions ----
st = (R / "selftest_output.txt").read_text(encoding="utf-8")
check("selftest 6,439 checks", "6439" in st or "6,439" in st, True)
check("selftest failed 0", bool(re.search(r"failed:\s*0", st)), True)
mt = (R / "selftest_mutation_test.txt").read_text(encoding="utf-8")
check("mutation test 175", "175" in mt, True)
p2o = (R / "power2_rerun_output.txt").read_text(encoding="utf-8")
for v in ("0.51", "0.62", "0.74", "0.75", "0.86", "0.93"):
    check("power value " + v, v in p2o, True)
ri = json.loads((R / "run_info.json").read_text(encoding="utf-8"))
for k, v in {"item_selection_seed": 20261113, "suggestion_key_seed": 20261114, "screening_order_seed": 20261114,
             "reserves_order_seed": 20261115, "power2_seed": 7, "power_seed": 20261113, "bootstrap_seed": 20261201}.items():
    check("seed " + k, ri["seeds"][k], v)
for k, v in {"python": "3.15.0", "numpy": "2.5.4", "scipy": "1.18.1", "pandas": "3.0.6", "statsmodels": "0.15.0", "matplotlib": "3.11.2"}.items():
    check("version " + k, ri["versions"][k], v)

# ---- Part 2: other numbers in the paper ----
tex = (ROOT / "paper" / "paper.tex").read_text(encoding="utf-8")
body = tex.split(r"\bibliographystyle")[0]
body = re.sub(r"\\cite\{[^}]*\}|\\label\{[^}]*\}|\\ref\{[^}]*\}|\\includegraphics.*?\}|%.*", "", body)
corpus = ""
for p in list(R.rglob("*")) + list((ROOT / "docs").glob("*.md")):
    if p.is_file() and p.suffix in (".md", ".txt", ".csv", ".json") and "PRIVATE" not in p.name:
        try:
            corpus += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except OSError:
            pass
toks = sorted(set(re.findall(r"(?<![\w.])\d[\d,]*\.?\d*", body)))
unmatched = []
for t in toks:
    t2 = t.rstrip(".").replace(",", "")
    if not t2 or len(t2.replace(".", "")) < 2:
        continue
    cands = {t2}
    if "." in t2:
        f = float(t2)
        cands |= {"%.3f" % (f / 100), "%.4f" % (f / 100), "%g" % (f / 100)}
    if not any(c in corpus.replace(",", "") for c in cands):
        unmatched.append(t)
print("\nNumbers in the paper text with no match in results/ or docs/ (review by hand):")
print(", ".join(unmatched))

print("\nRESULT: %d passed, %d failed" % (passes, len(fails)))
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
