"""Shared loading and parsing for the item pipeline.

Reads AgentHallu JSON as plain data (json module only). Nothing in the data folder is executed or imported.
Run the scripts that use this module with `python -I`; they add this folder to sys.path themselves.
"""
import json
import pathlib
import statistics

FRAMEWORKS = {"Magentic_One": "MO", "Camel": "CA"}
MAX_STEPS = 20
MAX_WORDS = 3000
COLLAPSE_WORDS = 150  # tool output longer than this is collapsed behind "expand" (M2 Step 3.4)


def words(x):
    return len(str(x).split())


def tool_call_text(tc):
    """One readable line per tool call: name(arguments as JSON)."""
    out = []
    for c in tc or []:
        out.append("%s(%s)" % (c.get("name", "?"), json.dumps(c.get("arguments", {}), ensure_ascii=False)))
    return out


def tool_output_text(tr):
    return [str(x) for x in (tr or [])]


def parse_trace(path, fw):
    """Return (item dict with all fields incl. labels, step list). Labels are kept apart in item['label']."""
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    hist = d["history"]
    steps = []
    wc_pool = 0
    for s in hist:
        content = s.get("content")
        content = "" if content is None else str(content)
        calls = tool_call_text(s.get("tool_calls"))
        outs = tool_output_text(s.get("tool_responses"))
        # Same word measure as scripts/pool.py (M2): split() of str() of each field.
        wc_pool += words(s.get("content", "")) + words(s.get("tool_responses", "")) + words(s.get("tool_calls", ""))
        steps.append({
            "step": int(s["step"]),
            "agent": "None" if s.get("role") is None else str(s.get("role")),
            "text": content,
            "tool_calls": calls,
            "tool_output": outs,
            "word_count": words(content) + sum(words(c) for c in calls) + sum(words(o) for o in outs),
            "tool_output_words": sum(words(o) for o in outs),
        })
    stem = pathlib.Path(path).stem
    item = {
        "item": "%s_%s" % (FRAMEWORKS[fw], stem),
        "framework": fw,
        "file": "%s/%s" % (fw, pathlib.Path(path).name),
        "question": d.get("question", ""),
        "true_answer": d.get("true_answer", ""),
        "agent_answer": d.get("agent_answer", ""),
        "n_steps": len(hist),
        "wc_pool": wc_pool,
        "agents": sorted({st["agent"] for st in steps}),
        "n_agents": len({st["agent"] for st in steps}),
        "is_hallucination": d.get("is_hallucination"),
        "label": {
            "hallucination_step": d.get("hallucination_step"),
            "category": d.get("hallucination_category"),
            "subcategory": d.get("hallucination_subcategory"),
            "reason": d.get("hallucination_reason"),
        },
    }
    return item, steps


def build_pool(agenthallu_root):
    """Apply the M2 filters in the order of scripts/pool.py. Returns (pool, counts_log).

    pool is a list of (item, steps). counts_log lists the count after each filter.
    """
    root = pathlib.Path(agenthallu_root)
    cands = []
    for fw in FRAMEWORKS:
        for f in sorted((root / fw).glob("*.json")):
            item, steps = parse_trace(f, fw)
            if item["is_hallucination"] != "true":
                continue
            hs = int(item["label"]["hallucination_step"])
            role = [s for s in steps if s["step"] == hs][0]["agent"]
            item["responsible_agent"] = role
            item["label_step"] = hs
            cands.append((item, steps))
    log = [("hallucination present", len(cands))]
    a = [c for c in cands if c[0]["n_steps"] <= MAX_STEPS]
    log.append(("<= %d steps" % MAX_STEPS, len(a)))
    b = [c for c in a if c[0]["wc_pool"] <= MAX_WORDS]
    log.append(("<= %d words" % MAX_WORDS, len(b)))
    c = [x for x in b if x[0]["responsible_agent"] not in ("None", "")]
    log.append(("responsible role known", len(c)))
    seen, d = set(), []
    for x in c:
        k = x[0]["question"][:200].strip().lower()  # same key as pool.py
        if k in seen:
            continue
        seen.add(k)
        d.append(x)
    log.append(("unique question", len(d)))
    med = statistics.median(x[0]["wc_pool"] for x in d)
    for item, _ in d:
        item["length_stratum"] = "long" if item["wc_pool"] > med else "short"
        item["position_stratum"] = "early" if item["label_step"] <= 3 else "later"
    return d, log, med
