"""Step A1: rebuild the eligible pool, check it against the M2 numbers, write the step table.

Usage: python -I src/pipeline/build_pool.py <AgentHallu folder> <results folder>
Writes: pool.csv (item features and labels, researcher-side only), step_table.csv (no label fields),
        pool_check.txt. Exits with status 1 if any M2 number differs.
"""
import collections
import csv
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

M2 = {
    "pool size": 82, "Magentic_One": 47, "Camel": 35, "step 3 labels": 46, "median words": 1135.5,
    "later items below median": 6, "later items": 17, "step 1 labels": 18, "step 2 labels": 1,
}


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s.]", "", str(s).lower())).strip()


def main(root, out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pool, log, med = common.build_pool(root)
    items = [p[0] for p in pool]
    lines = ["Filter counts: " + "; ".join("%s = %d" % x for x in log)]
    got = {
        "pool size": len(items),
        "Magentic_One": sum(i["framework"] == "Magentic_One" for i in items),
        "Camel": sum(i["framework"] == "Camel" for i in items),
        "step 3 labels": sum(i["label_step"] == 3 for i in items),
        "step 1 labels": sum(i["label_step"] == 1 for i in items),
        "step 2 labels": sum(i["label_step"] == 2 for i in items),
        "median words": med,
        "later items": sum(i["position_stratum"] == "later" for i in items),
        "later items below median": sum(i["position_stratum"] == "later" and i["length_stratum"] == "short" for i in items),
    }
    bad = []
    for k, v in M2.items():
        ok = got[k] == v
        lines.append("%-28s M2 %-8s got %-8s %s" % (k, v, got[k], "OK" if ok else "DIFFERS"))
        if not ok:
            bad.append(k)

    # Wording check (decision D5): does the agent's final answer contain the reference answer?
    contains = 0
    rows = []
    for item, _ in pool:
        t, a = norm(item["true_answer"]), norm(item["agent_answer"])
        item["answer_contains_truth"] = bool(t) and t in a
        contains += item["answer_contains_truth"]
        rows.append(item)
    lines.append("Items whose agent_answer contains the true_answer text (need a manual look): %d of %d" % (contains, len(items)))

    with open(out / "pool.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["item", "framework", "file", "n_steps", "wc_pool", "n_agents", "agents", "label_step", "responsible_agent",
                "category", "length_stratum", "position_stratum", "answer_contains_truth"]
        w = csv.writer(f)
        w.writerow(cols)
        for i in rows:
            w.writerow([i["item"], i["framework"], i["file"], i["n_steps"], i["wc_pool"], i["n_agents"], "|".join(i["agents"]),
                        i["label_step"], i["responsible_agent"], i["label"]["category"], i["length_stratum"],
                        i["position_stratum"], i["answer_contains_truth"]])
    with open(out / "step_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "step", "agent", "text", "tool_calls", "tool_output", "word_count"])
        for item, steps in pool:
            # Per-item check: step numbers are 1..n in order
            assert [s["step"] for s in steps] == list(range(1, len(steps) + 1)), item["item"]
            for s in steps:
                # Redact Google API keys that occur inside some source traces (third-party text, not ours)
                red = lambda x: re.sub(r"AIza[0-9A-Za-z_-]{35}", "AIza[REDACTED]", x)
                w.writerow([item["item"], s["step"], s["agent"], red(s["text"]), red("\n".join(s["tool_calls"])),
                            red("\n\n".join(s["tool_output"])), s["word_count"]])
    collapsed = sum(1 for _, st in pool for s in st if s["tool_output_words"] > common.COLLAPSE_WORDS)
    lines.append("Steps with tool output over %d words (collapsed behind expand): %d" % (common.COLLAPSE_WORDS, collapsed))
    lines.append("Result: " + ("ALL M2 NUMBERS REPRODUCED" if not bad else "MISMATCH in: " + ", ".join(bad)))
    text = "\n".join(lines)
    (out / "pool_check.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
