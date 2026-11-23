"""Step A2: seeded item selection (Block A 24, Block B 8, practice 2, reserves 11) and counterbalancing lists.

Usage: python -I src/pipeline/select_items.py <AgentHallu folder> <results folder> [seed]
Reads the pool (rebuilt from the data), writes:
  item_set.json         design only (no label step, category or reason)
  labels_PRIVATE.json   labels and suggestion truth; never copied into app/
  selection_check.txt   assertions and counts
Do not open labels_PRIVATE.json before both team members have finished blind screening.
"""
import collections
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

DEFAULT_SEED = 20261113
CAP_PER_STEP = 6          # M2: no single step number in more than 6 Block A items
N_PER_CELL_A = 6          # 6 items in each of the 4 position x length cells -> 24
CELLS = [("early", "short"), ("early", "long"), ("later", "short"), ("later", "long")]


def cell(i):
    return (i["position_stratum"], i["length_stratum"])


def pick_block_a(items, rng):
    """Random 6 per cell, redrawn until no step number appears in more than CAP_PER_STEP items."""
    by = collections.defaultdict(list)
    for i in items:
        by[cell(i)].append(i)
    for attempt in range(1, 100001):
        chosen = []
        for c in CELLS:
            chosen += rng.sample(by[c], N_PER_CELL_A)
        counts = collections.Counter(i["label_step"] for i in chosen)
        if max(counts.values()) <= CAP_PER_STEP:
            return chosen, attempt
    raise RuntimeError("could not balance Block A; apply the M2 kill-criteria fallback and log it")


def split_halves(block_a, rng):
    """Two halves of 12 (3 per cell). Each half is split into S1/S2 (6 each: 3 early, 3 later, 3 short, 3 long)."""
    by = collections.defaultdict(list)
    for i in block_a:
        by[cell(i)].append(i)
    halves = {1: {"S1": [], "S2": []}, 2: {"S1": [], "S2": []}}
    # S1 takes 2/1/1/2 from the cells (early-short, early-long, later-short, later-long), S2 the rest.
    s1_take = {("early", "short"): 2, ("early", "long"): 1, ("later", "short"): 1, ("later", "long"): 2}
    for c in CELLS:
        pool = by[c][:]
        rng.shuffle(pool)
        for h in (1, 2):
            three, pool = pool[:3], pool[3:]
            k = s1_take[c]
            halves[h]["S1"] += three[:k]
            halves[h]["S2"] += three[k:]
    return halves


def suggestion_steps(steps, label_step):
    """Rule-based wrong suggestion (decision D2, revised D2b): the nearest step at least 2 steps from the label,
    preferring a step by a different agent than the responsible one (later step wins a tie in distance).
    Tier 1: different agent, distance >= 2. Tier 2: any agent, distance >= 2.
    Tier 3 (flagged near-miss): the old rule, first later step by another agent, else nearest earlier one."""
    resp = steps[label_step - 1]["agent"]
    n = len(steps)
    far = sorted((s for s in steps if abs(s["step"] - label_step) >= 2), key=lambda s: (abs(s["step"] - label_step), -s["step"]))
    for s in far:
        if s["agent"] != resp:
            return s["step"], "tier 1: different agent, >= 2 steps away", False
    if far:
        return far[0]["step"], "tier 2: same agent, >= 2 steps away", False
    for s in steps[label_step:]:
        if s["agent"] != resp:
            return s["step"], "tier 3 near-miss: later step by another agent", True
    for s in reversed(steps[:label_step - 1]):
        if s["agent"] != resp:
            return s["step"], "tier 3 near-miss: earlier step by another agent", True
    raise RuntimeError("no wrong suggestion possible")


def main(root, out, seed):
    out = pathlib.Path(out)
    rng = random.Random(seed)
    pool, log, med = common.build_pool(root)
    steps_of = {p[0]["item"]: p[1] for p in pool}
    items = [p[0] for p in pool]
    left = {i["item"]: i for i in items}

    block_a, attempts = pick_block_a(items, rng)
    for i in block_a:
        left.pop(i["item"])
    halves = split_halves(block_a, rng)

    # Block B: 4 early (2 at step 1, 2 at step 3) + 4 later, from what remains.
    rem = list(left.values())
    later = rng.sample([i for i in rem if i["position_stratum"] == "later"], 4)
    e1 = rng.sample([i for i in rem if i["position_stratum"] == "early" and i["label_step"] == 1], 2)
    e3 = rng.sample([i for i in rem if i["position_stratum"] == "early" and i["label_step"] == 3], 2)
    block_b = later + e1 + e3
    for i in block_b:
        left.pop(i["item"])
    # Practice: short early items, one at step 1 and one at step 3 (kept short so practice is quick).
    rem = list(left.values())
    p1 = rng.choice([i for i in rem if i["position_stratum"] == "early" and i["length_stratum"] == "short" and i["label_step"] == 1])
    p3 = rng.choice([i for i in rem if i["position_stratum"] == "early" and i["length_stratum"] == "short" and i["label_step"] == 3])
    practice = [p1, p3]
    for i in practice:
        left.pop(i["item"])
    # Reserves: every remaining later item, then early items alternating short/long up to 11.
    rem = list(left.values())
    reserves = [i for i in rem if i["position_stratum"] == "later"]
    for length in ("short", "long") * 6:
        if len(reserves) >= 11:
            break
        cand = [i for i in rem if i["position_stratum"] == "early" and i["length_stratum"] == length and i not in reserves]
        if cand:
            reserves.append(rng.choice(cand))

    # Block B groups and lists. G1/G2 each hold 2 early + 2 later.
    g_early, g_later = block_b[4:], block_b[:4]
    g1 = [g_later[0], g_later[1], g_early[0], g_early[2]]   # one step-1 and one step-3 early item in each group
    g2 = [g_later[2], g_later[3], g_early[1], g_early[3]]
    sugg = {}
    for i in block_b:
        wrong, how, near = suggestion_steps(steps_of[i["item"]], i["label_step"])
        sugg[i["item"]] = {"correct": i["label_step"], "incorrect": wrong, "rule": how, "near_miss_flag": near}
    # Pattern for list 1 (and 3): items 0..3 -> (view, suggestion); list 2 (and 4) is the complement.
    pat1 = [("console", "correct"), ("console", "incorrect"), ("visual", "correct"), ("visual", "incorrect")]
    pat2 = [("visual", "incorrect"), ("visual", "correct"), ("console", "incorrect"), ("console", "correct")]
    block_b_lists = {}
    for n, (g, pat) in enumerate([(g1, pat1), (g1, pat2), (g2, pat1), (g2, pat2)], start=1):
        block_b_lists[str(n)] = [{"item": it["item"], "view": v, "suggestion": s} for it, (v, s) in zip(g, pat)]

    # Block A lists: list n -> half, and which of S1/S2 is shown in the console view.
    block_a_lists = {}
    for n, (h, s1_view) in enumerate([(1, "console"), (1, "visual"), (2, "console"), (2, "visual")], start=1):
        s2_view = "visual" if s1_view == "console" else "console"
        block_a_lists[str(n)] = {
            "half": h,
            "console": [i["item"] for i in halves[h]["S1" if s1_view == "console" else "S2"]],
            "visual": [i["item"] for i in halves[h]["S2" if s1_view == "console" else "S1"]],
        }

    def brief(i):
        return {"item": i["item"], "framework": i["framework"], "n_steps": i["n_steps"], "words": i["wc_pool"],
                "n_agents": i["n_agents"], "position_stratum": i["position_stratum"], "length_stratum": i["length_stratum"]}

    item_set = {
        "seed": seed, "median_words_pool": med, "block_a_draws": attempts,
        "practice": [brief(i) for i in practice],
        "block_a": [brief(i) for i in block_a],
        "block_a_halves": {str(h): {k: [i["item"] for i in v] for k, v in halves[h].items()} for h in halves},
        "block_a_lists": block_a_lists,
        "block_b": [brief(i) for i in block_b],
        "block_b_lists": block_b_lists,
        "reserves": [brief(i) for i in reserves],
        "participant_cell_rule": "participant number n (P01 = 1): cell = (n-1) mod 8; list = cell//2 + 1; view order = console first if cell is even else visual first",
        "label_names": {"console": "View A", "visual": "View B"},
    }
    private = {
        "labels": {i["item"]: {"step": i["label_step"], "agent": i["responsible_agent"], "category": i["label"]["category"]}
                   for i in practice + block_a + block_b + reserves},
        "block_b_suggestions": sugg,
    }
    (out / "item_set.json").write_text(json.dumps(item_set, indent=1), encoding="utf-8")
    (out / "labels_PRIVATE.json").write_text(json.dumps(private, indent=1), encoding="utf-8")

    # ---- assertions and report ----
    L = []
    def chk(name, ok, detail=""):
        L.append("%-62s %s %s" % (name, "PASS" if ok else "FAIL", detail))
        return ok
    allsel = practice + block_a + block_b + reserves
    chk("selected items are distinct", len({i["item"] for i in allsel}) == len(allsel), "%d items" % len(allsel))
    chk("Block A size 24", len(block_a) == 24)
    c = collections.Counter(cell(i) for i in block_a)
    chk("Block A: 6 per position x length cell", all(c[x] == 6 for x in CELLS), str(dict(c)))
    chk("Block A: 12 early / 12 later", sum(i["position_stratum"] == "early" for i in block_a) == 12)
    sc = collections.Counter(i["label_step"] for i in block_a)
    chk("Block A: no step number in more than 6 items", max(sc.values()) <= CAP_PER_STEP, str(dict(sorted(sc.items()))))
    chk("Block A: always-step-3 and always-step-1 at or below 25%",
        max(sc.get(1, 0), sc.get(3, 0)) / 24 <= 0.25, "step1 %.3f step3 %.3f" % (sc.get(1, 0) / 24, sc.get(3, 0) / 24))
    chk("Block B size 8 (4 early, 4 later)", len(block_b) == 8 and sum(i["position_stratum"] == "later" for i in block_b) == 4)
    chk("Practice size 2", len(practice) == 2)
    chk("Reserves 11", len(reserves) == 11, "later reserves: %d" % sum(i["position_stratum"] == "later" for i in reserves))
    for h in (1, 2):
        for k in ("S1", "S2"):
            s = halves[h][k]
            ok = (len(s) == 6 and sum(i["position_stratum"] == "early" for i in s) == 3 and sum(i["length_stratum"] == "short" for i in s) == 3)
            chk("half %d %s: 6 items, 3 early/3 later, 3 short/3 long" % (h, k), ok)
    # Counterbalancing: across the 4 lists every item is seen in both views once.
    seen = collections.defaultdict(set)
    for l in block_a_lists.values():
        for v in ("console", "visual"):
            for it in l[v]:
                seen[it].add(v)
    chk("Block A lists: every item appears in both views across lists", all(len(v) == 2 for v in seen.values()) and len(seen) == 24)
    seenb = collections.defaultdict(set)
    for l in block_b_lists.values():
        for r in l:
            seenb[r["item"]].add((r["view"], r["suggestion"]))
    chk("Block B lists: every item shown with both a correct and an incorrect suggestion",
        all({s for _, s in v} == {"correct", "incorrect"} for v in seenb.values()) and len(seenb) == 8)
    chk("Block B lists: 4 trials, 2 per view, 1 correct + 1 incorrect per view",
        all(sorted((r["view"], r["suggestion"]) for r in l) == sorted([("console", "correct"), ("console", "incorrect"), ("visual", "correct"), ("visual", "incorrect")])
            for l in block_b_lists.values()))
    chk("Block B incorrect suggestion differs from the label", all(s["incorrect"] != s["correct"] for s in sugg.values()))
    n_far = sum(abs(s["incorrect"] - s["correct"]) >= 2 for s in sugg.values())
    chk("Block B wrong suggestion at least 2 steps from the label (items that could)", n_far == sum(not s["near_miss_flag"] for s in sugg.values()),
        "%d of 8 are >= 2 steps away; %d remain near-misses (flagged)" % (n_far, 8 - n_far))
    n_diff = sum(steps_of[k][s["incorrect"] - 1]["agent"] != steps_of[k][s["correct"] - 1]["agent"] for k, s in sugg.items())
    L.append("Block B wrong suggestion by a different agent than the responsible one: %d of 8" % n_diff)
    L.append("Block B rules used: %s" % dict(collections.Counter(s["rule"] for s in sugg.values())))
    fw = collections.Counter(i["framework"] for i in block_a)
    L.append("Block A by framework: %s; steps per item: median %s; words: min %d max %d" % (
        dict(fw), sorted(i["n_steps"] for i in block_a)[11], min(i["wc_pool"] for i in block_a), max(i["wc_pool"] for i in block_a)))
    L.append("Block A step numbers: %s" % dict(sorted(sc.items())))
    L.append("Block A: draws needed to satisfy the step cap: %d (seed %d)" % (attempts, seed))
    L.append("Block B step numbers: %s" % sorted(i["label_step"] for i in block_b))
    L.append("Block B wrong-suggestion distance (suggested - label): %s" % sorted(s["incorrect"] - s["correct"] for s in sugg.values()))
    text = "\n".join(L)
    (out / "selection_check.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(" FAIL" not in x for x in L) else 1


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) == 4 else DEFAULT_SEED))
