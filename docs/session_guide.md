# One-page guide: pilot session and screening session

Only the two team members take part. Nobody else may be recruited (ethics review, open issue O8).

## Before either session (5 minutes)
1. From the project folder run `python -m http.server 8765 --directory app` and open `http://localhost:8765`.
2. Open `selftest.html` once: it must say `RESULT: PASS`.
3. On the start screen click "Delete saved data" if old TEST records are there (download them first if you want them).
4. Do not open `results/labels_PRIVATE.json` or `results/suggestion_key_PRIVATE.json`. Do not look at `trials.csv` or any analysis output until both sessions below are finished.

## Pilot session (about 55 minutes each, one person at a time, same screen)
Purpose: check that the app, timing and instructions work. The two of you built it, so the pilot says nothing about how accurate classmates will be.
1. Member 1 uses code `P01`, member 2 uses `P02`. Set the data label to **PILOT** only for these two real sessions. For any practice run of the app itself, keep **TEST**.
2. The other member sits behind and takes notes: where the person hesitates, what they misread, any control they never used, the screen size, any step that felt cramped.
3. Run the whole sequence: background, 2 practice trials, Block A (6 trials in the first view, workload sliders, break, 6 trials in the second view, workload sliders), Block B, last questions. Do not skip the break.
4. Note the total time. If it is over 60 minutes, M2 says to drop Block B.
5. At the end click "Download JSON (all)" and "Trials CSV" and "TLX CSV". Save them as `pilot_P01_all.json`, `pilot_P01_trials.csv`, `pilot_P01_tlx.csv` (and the same for P02) in `results/pilot/`. Then "Delete saved data".
6. Write notes the same day (what was confusing and what you changed).
7. Report pilot results descriptively only, labelled `PILOT (n = 2)`: no p-values, no intervals, no "significant".

## Screening session (about 2.5 hours each, done separately, blind)
Purpose: label the first hallucinated step yourself so we can compare your labels with AgentHallu's.
1. Each member opens the app in their own browser profile or on their own machine. Choose "Screening mode" and enter your initials as the code, for example `AW`. Label `TEST` is fine: screening records have their own file.
2. Work through the 34 selected items first (the 32 scored items, then the 2 practice items). The 11 reserves come after and are optional; do them only if time allows, and say in the report which were done.
3. For each item: read the trace, pick the first step where an agent said something not supported by the task, earlier steps or a tool output (or press "I cannot find one"), give a confidence, and tick the boxes: final answer appears correct, offensive or personal content, ambiguous. Add a comment when unsure.
4. Do not talk to each other about the items or look at the labels until both have finished. The two practice items are not blind if you already ran a pilot session; their records are marked and are left out of the agreement figure.
5. You can stop and resume: items you already saved under the same initials are skipped.
6. Click "Screening CSV" and save as `screening_<initials>.csv` in `results/screening/`. Then "Delete saved data".
7. Save both files in `results/screening/`. The agreement script (`src/pipeline/screening_agreement.py`) (Cohen's kappa between you two, agreement with the label, items where both differ from the label by more than one step) runs after both files exist.

## Order that keeps the study honest
Screening and pilot can be done on the same day in either order. If you pilot first, the two practice items' labels have been shown to you (as feedback); everything else stays blind. Flagged items are excluded from the confirmatory analysis and never removed silently.
