"""E2 representation ablation without an LLM (definition: docs/ablation_definitions.md).

Usage: python -I src/pipeline/ablation_representation.py <AgentHallu folder> <results folder>
Reads the data with the standard library only (so -I works) and writes results/ablation_E2_representation.csv,
ablation_E2_identifiability.csv and ablation_E2_representation.md.
R1 = console format (step numbers and agent names). R2 = plain text (step boundaries, no numbers, no agent names).
"""
import csv
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

SCOPE = ("E2: 82 eligible pool items; simple rules on a text format; not language models and not people; "
         "says nothing about how a human reads either view; no p-values")
COORD = {"MagenticOneOrchestrator", "Planner", "Coordinator"}
NUM = re.compile(r"\d+(?:\.\d+)?")


def rules(item, steps):
    q = set(NUM.findall(item["question"]))
    first = lambda pred: next((s["step"] for s in steps if pred(s)), None)
    return {
        "always step 1": ("R1 only (needs step numbers)", 1),
        "always step 3": ("R1 only (needs step numbers)", 3),
        "first step by a non-coordinating agent": ("R1 only (needs agent names)", first(lambda s: s["agent"] not in COORD)),
        "first step with a tool call": ("R1 and R2", first(lambda s: s["tool_calls"])),
        "first step with tool output": ("R1 and R2", first(lambda s: s["tool_output"])),
        "first step with a number not in the question": ("R1 and R2", first(lambda s: any(n not in q for n in NUM.findall(s["text"])))),
    }


def tally(subset):
    tallies, ident = {}, {"label step message empty (tool-only step)": 0, "label step message duplicated by another step": 0,
                          "responsible agent also wrote the previous step (speaker change lost in R2)": 0}
    for item, steps in subset:
        lab, resp = item["label_step"], item["responsible_agent"]
        for name, (avail, pick) in rules(item, steps).items():
            t = tallies.setdefault(name, dict(avail=avail, exact=0, agent=0, tol=0, none=0))
            if pick is None:
                t["none"] += 1
                continue
            t["exact"] += pick == lab
            t["agent"] += steps[pick - 1]["agent"] == resp
            t["tol"] += abs(pick - lab) <= 1
        text = steps[lab - 1]["text"].strip()
        ident["label step message empty (tool-only step)"] += text == ""
        ident["label step message duplicated by another step"] += text != "" and any(s["step"] != lab and s["text"].strip() == text for s in steps)
        ident["responsible agent also wrote the previous step (speaker change lost in R2)"] += lab > 1 and steps[lab - 2]["agent"] == steps[lab - 1]["agent"]
    return tallies, ident


def main(root, out):
    import json
    out = pathlib.Path(out)
    pool, _, _ = common.build_pool(root)
    iset = json.loads((out / "item_set.json").read_text(encoding="utf-8"))
    ids = lambda k: {i["item"] for i in iset[k]}
    sets = {"pool_82": pool, "block_a_24": [p for p in pool if p[0]["item"] in ids("block_a")], "block_b_8": [p for p in pool if p[0]["item"] in ids("block_b")]}
    rows, irows, md = [], [], ["# E2 representation ablation (no LLM)", "", "SCOPE: " + SCOPE, ""]
    for sname, sub in sets.items():
        tallies, ident = tally(sub)
        n = len(sub)
        chance = sum(1 / it["n_steps"] for it, _ in sub) / n
        r_ = [dict(scope=SCOPE, item_set=sname, rule=k, available_in=v["avail"], n_items=n, exact=round(v["exact"] / n, 3), agent=round(v["agent"] / n, 3),
                   tolerant_pm1=round(v["tol"] / n, 3), rule_found_no_step=v["none"], mean_chance_exact=round(chance, 3)) for k, v in tallies.items()]
        rows += r_
        irows += [dict(scope=SCOPE, item_set=sname, measure=k, items=v, of=n, share=round(v / n, 3)) for k, v in ident.items()]
        md += ["## " + sname + " (n = %d, mean chance %.3f)" % (n, chance), "", "| rule | available in | exact | agent | tolerant (+-1) | found no step |", "|---|---|---|---|---|---|"]
        md += ["| %s | %s | %.3f | %.3f | %.3f | %d |" % (r["rule"], r["available_in"], r["exact"], r["agent"], r["tolerant_pm1"], r["rule_found_no_step"]) for r in r_]
        md += ["", "| identifiability in plain text (R2) | items | share |", "|---|---|---|"]
        md += ["| %s | %d of %d | %.3f |" % (r["measure"], r["items"], r["of"], r["share"]) for r in irows if r["item_set"] == sname]
        md += [""]
    for name, rr in (("ablation_E2_representation.csv", rows), ("ablation_E2_identifiability.csv", irows)):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
    (out / "ablation_E2_representation.md").write_text(chr(10).join(md) + chr(10), encoding="utf-8")
    print(chr(10).join(md))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
