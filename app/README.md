# Study app

Static, offline, no build step, no network calls. Version 0.1.0.

## Run

- Double-click `index.html`, or from the project folder run `python -m http.server 8765 --directory app` and open `http://localhost:8765`.
- The server is the safer choice: some browsers restrict storage for `file://` pages. If storage is blocked the app says so on the start screen and keeps data in memory only, so download before closing the tab.
- `selftest.html` runs the view-equivalence checks (about 5 seconds). Its result must read `PASS`.

## Modes

| Mode | What happens |
|---|---|
| Study session | background questions, task text, 2 practice trials with feedback, Block A (6 trials in the first view, TLX, break, 6 trials in the second view, TLX), Block B (4 trials with "AI suggests this step", no rationale), last questions, download |
| Screening | blind labelling of the first hallucinated step in the console view, no time limit. 34 selected items first (32 scored items, then the 2 practice items), then 11 reserves, which are optional. Per item: chosen step or "cannot find one", confidence, "final answer appears correct", "offensive or personal content", "ambiguous", comment. Resumes where a screener left off |

Participant code `Pnn`: cell = (nn - 1) mod 8, list = cell div 2 + 1, View A first when the cell is even. The start screen shows the result and lets you override it for testing. Data label `PILOT` is for the two team members; `TEST` marks runs that must be excluded from analysis.

View A = console, View B = visual, for everyone. Cut line switches are in `js/core.js` (`DAV.FEATURES`: `filter`, `blockB`).

## Data (browser storage key `dav_records_v1`; download buttons on the start screen)

Record types and fields (CSV columns in `js/store.js`):

- `trial`: participant, data_label, session_id, list, view_order, block (practice, A, B), trial_index, item, view (console, visual), chosen_step (null if timed out), timed_out, time_ms (record shown to submission), confidence (1-5, null if timed out), suggestion_key (X or Y), suggestion_step, suggestion_shown, suggestion_accepted, n_search, n_details, n_filter, n_scroll, n_expand, events (list of {t ms, type, detail}), app_version, timestamp.
- `tlx`: participant, data_label, session_id, view, block, mental, physical, temporal, performance, effort, frustration (0-100), raw_tlx (mean of the six).
- `background`: programming, llm_agents (1-5). `final`: preference (A, B, none), comments.
- `screen`: screener, item, index, reserve, practice_item, chosen_step, no_step_found, time_ms, confidence, final_answer_correct, offensive_or_personal, ambiguous, comment.

Correctness is not stored. Scoring joins `item` and `chosen_step` with `results/labels_PRIVATE.json` offline; Block B suggestion keys X and Y are decoded with `results/suggestion_key_PRIVATE.json`.

Event types: `search` (query, number of matches), `search_nav`, `filter`, `details_open` (visual view, a step opened in the panel), `expand` (tool output opened or closed), `select_click` (before confirmation), `scroll` (at most one per second).

## What is shipped in `data/`

`items.js` and `design.js` are written by `src/pipeline/export_app_data.py` from an allow-list. They contain no hallucination label, category, reason or explanation, no Block A answer key, and the Block B candidate steps under neutral keys. This does not stop a participant who reads the page source; the study is in person.
