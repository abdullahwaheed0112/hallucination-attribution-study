# Item set note (Step A)

Seed 20261113. Rebuild with:

```
python -I src/pipeline/build_pool.py <AgentHallu folder> results
python -I src/pipeline/select_items.py <AgentHallu folder> results
python -I src/pipeline/export_app_data.py <AgentHallu folder> results app/data
```

Outputs are in `results/` (`pool_check.txt`, `selection_check.txt`) and `app/data/`. A rerun gives byte-identical `item_set.json` and `labels_PRIVATE.json` (checked by hash).

## Final counts

| Set | Items | Notes |
|---|---|---|
| Eligible pool | 82 | 47 Magentic-One, 35 Camel; all M2 numbers reproduced (`results/pool_check.txt`) |
| Block A | 24 | 6 in each position x length cell; step numbers 1, 3 appear in at most 6 items; 16 Magentic-One, 8 Camel |
| Block B | 8 | 4 early (two at step 1, two at step 3) and 4 later |
| Practice | 2 | short early items, one at step 1 and one at step 3; not scored |
| Reserves | 11 | the one remaining later item plus 10 early items; screened only if time allows |

Screening covers the 34 selected items (Block A + Block B + practice) first. The reserves are screened only if time allows; the report states which were screened.

## Things to know

- **The later stratum is used up.** Of 17 later-position items, Block A takes 12 (all 6 short ones), Block B takes 4 and 1 is left as a reserve. If screening flags any of the 6 later-short Block A items, the M2 kill-criteria fallback applies (split the later stratum at its own median length). The only later reserve is long.
- **Balance on the scored items.** Always-step-1 and always-step-3 score 25.0% and 20.8% on Block A, and 25.0% and 25.0% on Block B (`results/baselines.csv`). Over all 34 selected items, always step 1 scores 26.5% because the two practice items add one step-1 label; practice trials are not scored.
- **Block B wrong suggestions** follow deviation D2b: the nearest step at least 2 steps from the label, preferring a different agent. All 8 were found at tier 1 (different agent, 2 or 3 steps away), so none remains a near-miss. Both team members must still check each one in screening mode.
- **Wording check (D5).** Eight pool items have an agent answer that contains the reference text as a substring. Reading them shows the matches are on short answers such as "5" or "D" and none looks correct, but a substring test cannot rule out equivalent answers. Screening mode therefore includes a "final answer appears correct" box, and the "wrong answer" wording stays unless it is ticked for a selected item.
- **Word counts.** Item length (used for the median split) uses the same measure as `scripts/pool.py`. Per-step `word_count` in `step_table.csv` counts the displayed text, so the two differ slightly.
- **Leak test.** `app/data/` contains no label key (`hallucination_*`, `explanation`) and no Block A label. Block B candidate steps are stored under keys X and Y with no correct/incorrect flag; the key is in `results/suggestion_key_PRIVATE.json`. This hides labels from a participant only as long as they do not read the page source; the app is not tamper-proof.
- **Do not open** `results/labels_PRIVATE.json` or `results/suggestion_key_PRIVATE.json` before both team members have finished blind screening.
- **Licence.** Traces come from AgentHallu (Liu et al., 2026), commit 9ffe8bc. The repository says CC BY 4.0 and the paper says CC BY-NC-SA 4.0; we follow the stricter terms (attribution, non-commercial, share-alike).
