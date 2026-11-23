"""Step A3: write the data the study app may see (allow-list only) to app/data/.

Usage: python -I src/pipeline/export_app_data.py <AgentHallu folder> <results folder> <app/data folder>
Shipped per item: id, question, reference answer, the system's final answer, and the step table
(step, agent, text, tool calls, tool output, word count). Never shipped: hallucination_step, category,
subcategory, reason, explanation, Block A labels. Practice labels (step only) and the two candidate steps per
Block B item (keys X and Y, no flag saying which one is correct) are shipped in design.js.
Writes results/suggestion_key_PRIVATE.json so scoring can decode X/Y offline.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

ALLOWED_ITEM_KEYS = ["id", "question", "true_answer", "agent_answer", "agents", "steps"]
ALLOWED_STEP_KEYS = ["step", "agent", "text", "tool_calls", "tool_output", "words"]


def main(root, results, appdata):
    results, appdata = pathlib.Path(results), pathlib.Path(appdata)
    appdata.mkdir(parents=True, exist_ok=True)
    item_set = json.loads((results / "item_set.json").read_text(encoding="utf-8"))
    private = json.loads((results / "labels_PRIVATE.json").read_text(encoding="utf-8"))
    pool, _, _ = common.build_pool(root)
    by_id = {p[0]["item"]: p for p in pool}
    seed = item_set["seed"]

    practice = [i["item"] for i in item_set["practice"]]
    block_a = [i["item"] for i in item_set["block_a"]]
    block_b = [i["item"] for i in item_set["block_b"]]
    reserves = [i["item"] for i in item_set["reserves"]]
    ids = practice + block_a + block_b + reserves

    items = {}
    for iid in ids:
        item, steps = by_id[iid]
        # Agent order of first appearance = lane order in the visual view.
        agents = []
        for s in steps:
            if s["agent"] not in agents:
                agents.append(s["agent"])
        items[iid] = {
            "id": iid, "question": item["question"], "true_answer": item["true_answer"], "agent_answer": item["agent_answer"],
            "agents": agents,
            "steps": [{"step": s["step"], "agent": s["agent"], "text": s["text"], "tool_calls": s["tool_calls"],
                       "tool_output": s["tool_output"], "words": s["word_count"]} for s in steps],
        }
        assert list(items[iid].keys()) == ALLOWED_ITEM_KEYS
        assert all(list(s.keys()) == ALLOWED_STEP_KEYS for s in items[iid]["steps"])

    rng = random.Random(seed + 1)
    key, cand = {}, {}
    for iid, s in private["block_b_suggestions"].items():
        pair = [("correct", s["correct"]), ("incorrect", s["incorrect"])]
        rng.shuffle(pair)
        key[iid] = {"X": pair[0][0], "Y": pair[1][0]}
        cand[iid] = {"X": pair[0][1], "Y": pair[1][1]}
    b_lists = {}
    for n, rows in item_set["block_b_lists"].items():
        b_lists[n] = [{"item": r["item"], "view": r["view"],
                       "sugg": [k for k, v in key[r["item"]].items() if v == r["suggestion"]][0]} for r in rows]

    screening = block_a + block_b
    rng.shuffle(screening)
    rng2 = random.Random(seed + 2)
    res = reserves[:]
    rng2.shuffle(res)
    design = {
        "practice": practice,
        "practice_feedback_step": {i: private["labels"][i]["step"] for i in practice},
        "block_a": block_a, "block_a_lists": item_set["block_a_lists"],
        "block_b": block_b, "block_b_candidates": cand, "block_b_lists": b_lists,
        "screening_order": screening + practice + res, "screening_primary_count": len(screening) + len(practice), "screening_practice_items": practice,
        "view_names": item_set["label_names"],
        "participant_cell_rule": item_set["participant_cell_rule"],
        "seed": seed,
    }
    (appdata / "items.js").write_text("window.ITEMS = " + json.dumps(items, ensure_ascii=False) + ";\n", encoding="utf-8")
    (appdata / "design.js").write_text("window.DESIGN = " + json.dumps(design, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    (results / "suggestion_key_PRIVATE.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print("items exported: %d (practice %d, block A %d, block B %d, reserves %d)" % (len(items), len(practice), len(block_a), len(block_b), len(reserves)))
    print("items.js bytes: %d; design.js bytes: %d" % ((appdata / "items.js").stat().st_size, (appdata / "design.js").stat().st_size))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
