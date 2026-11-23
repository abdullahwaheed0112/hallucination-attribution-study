"""Step C: participant-free baselines on the item set (and on the full pool as a reproduction check).

Usage: python -I scripts/baselines.py <AgentHallu folder> <results folder>
Reads results/item_set.json, results/labels_PRIVATE.json, and rebuilds the pool from the data.
Writes results/baselines.csv. No LLM is called. The published figure is copied from the AgentHallu paper
(Table 2, page 6, Gemini-2.5-Pro overall step localization) and is NOT item-matched.
"""
import csv, json, pathlib, sys, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "pipeline"))
import common  # noqa: E402

PUBLISHED = 41.1


def score(rows, method):
    """rows: list of (n, label, agents_by_step, resp_agent). Returns exact, agent, tolerant (as proportions)."""
    ex = ag = tol = 0.0
    for n, lab, agents, resp in rows:
        if method == "chance":
            ex += 1 / n
            ag += sum(a == resp for a in agents) / n
            tol += sum(abs(s - lab) <= 1 for s in range(1, n + 1)) / n
        else:
            k = method
            ex += k == lab
            ag += agents[k - 1] == resp
            tol += abs(k - lab) <= 1
    m = len(rows)
    return ex / m, ag / m, tol / m


def main(root, out):
    out = pathlib.Path(out)
    pool, _, _ = common.build_pool(root)
    iset = json.loads((out / "item_set.json").read_text(encoding="utf-8"))
    lab = json.loads((out / "labels_PRIVATE.json").read_text(encoding="utf-8"))["labels"]
    by = {p[0]["item"]: p for p in pool}

    def row(iid):
        item, steps = by[iid]
        return (item["n_steps"], item["label_step"], [s["agent"] for s in steps], item["responsible_agent"])
    ids = lambda key: [i["item"] for i in iset[key]]
    sets = {"pool_82": list(by), "block_a_24": ids("block_a"), "block_b_8": ids("block_b"),
            "blocks_a_b_32": ids("block_a") + ids("block_b"),
            "selected_34": ids("practice") + ids("block_a") + ids("block_b")}
    # strata inside Block A and the pool
    for name in ("pool_82", "block_a_24"):
        for pos in ("early", "later"):
            sets["%s|%s" % (name, pos)] = [i for i in sets[name] if by[i][0]["position_stratum"] == pos]
        for ln in ("short", "long"):
            sets["%s|%s" % (name, ln)] = [i for i in sets[name] if by[i][0]["length_stratum"] == ln]
    assert all(lab[i]["step"] == by[i][0]["label_step"] for i in sets["selected_34"])  # private labels agree with the data
    methods = [("chance (1/n; agent: share of steps by responsible agent)", "chance"),
               ("always step 1", 1), ("always step 3", 3)]
    with open(out / "baselines.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_set", "n_items", "method", "exact_acc", "agent_acc", "tolerant_acc_pm1", "note"])
        for sname, idl in sets.items():
            rows = [row(i) for i in idl]
            for mname, m in methods:
                e, a, t = score(rows, m)
                w.writerow([sname, len(rows), mname, "%.4f" % e, "%.4f" % a, "%.4f" % t, "computed from data"])
        w.writerow(["published", "", "AgentHallu best LLM (Gemini-2.5-Pro), step localization", "%.4f" % (PUBLISHED / 100), "", "",
                    "PUBLISHED figure, NOT item-matched: all AgentHallu frameworks and categories, not our 82-item pool; agent and tolerant accuracy not reported in this form"])
    for r in csv.reader(open(out / "baselines.csv", encoding="utf-8")):
        if "|" not in r[0]:
            print(" | ".join(r[:6]))
    # reproduction check against M2
    full = {m: score([row(i) for i in sets["pool_82"]], m) for _, m in methods}
    print("\nM2 check on pool_82: always step 3 = %.3f (M2 0.561); always step 1 = %.3f (M2 0.220); chance = %.3f (M2 0.165)" % (full[3][0], full[1][0], full["chance"][0]))
    ok = abs(full[3][0] - .561) < .0006 and abs(full[1][0] - .220) < .0006 and abs(full["chance"][0] - .165) < .0006
    print("RESULT:", "REPRODUCED" if ok else "DIFFERS")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
