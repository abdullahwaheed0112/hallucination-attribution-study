# Checklist: do View A and View B show identical information?

Do this once in a real browser, ideally by double-clicking `app/index.html` (not through the server), then again once through `python -m http.server 8765 --directory app`. About 15 minutes. Use code `P01` with data label **TEST**. Tick each box; write down anything that differs.

## 0. Machine check
- [ ] Open `app/selftest.html`. After a few seconds the page says `RESULT: PASS` and `failed: 0`. (If it says FAIL, stop and send the first failures.)

## 1. Same record in both views (start a session with TEST, reach a trial in each view)
For one trace, open it in View A, note the answers, then open the same item in View B (P02 gives the other view first, or use the override boxes on the start screen).
- [ ] The task sentence, the question, the system's final answer and the reference answer are word-for-word the same in both.
- [ ] Every step has the same header text: `[Step k] Agent`. In View B this header appears above the text when you click a step.
- [ ] Click each step in View B and compare with the same step in View A. The message text, the tool call text and the tool output are identical.
- [ ] Nothing in View B tells you something View A does not: no summary, no score, no colour meaning other than message versus tool call.
- [ ] A step with a tool call shows an orange square in View B and a "Tool call" block in View A. A step with only text shows a blue circle and only a "Message" block.

## 2. Collapse rule
- [ ] Find a step whose tool output is collapsed in View A ("Tool output (N words, collapsed)" and an Expand button). In View B the same step shows the same label and button, with the same N.
- [ ] Expanding shows the same text in both. Collapsing hides it again.

## 3. Search
- [ ] Type `the` in the find box in both views. The count ("1 of N") is the same.
- [ ] Next and Previous move through the same matches. In View B, Next opens the matching step in the panel; in View A it scrolls to it.
- [ ] In View B every step with a match has a dashed ring on its mark; steps without one do not.
- [ ] Search for a word that appears only in a collapsed tool output: the count includes it, and Next expands that output in both views.
- [ ] Search for `zzzqqq`: "0 matches" in both.

## 4. Agent filter
- [ ] Untick one agent. In View A the bodies of that agent's steps read "Hidden by agent filter"; headers and Select buttons stay. In View B the marks of that agent fade and the panel shows the same note when you open one of its steps.
- [ ] The search count drops to the same number in both views.

## 5. Answering
- [ ] View A has a "Select this step" button in every step header. View B has one in the panel only, after you click a step.
- [ ] Both ask "Submit [Step k] Agent as your answer?" with Confirm and Cancel, then ask for confidence 1 to 5. Cancel returns to the trace.
- [ ] After submitting in practice, the feedback screen appears. In the main trials there is no feedback.

## 6. Timer, break, TLX, Block B
- [ ] The timer starts at 4:00 when the record appears and counts down; it turns red in the last minute. (To see a timeout quickly, run `DAV.TRIAL_MS = 5000` in the browser console before the trial.)
- [ ] After 6 trials in one view you get the six workload sliders; Submit unlocks only after all six are moved. Then a break screen names the other view.
- [ ] In Block B, a badge "AI suggests this step" appears in the step header in View A, and as an "AI" flag on the mark plus the badge in the panel in View B. The wording is identical.

## 7. Data
- [ ] On the start screen the saved-data line shows counts. Download "Trials CSV" and open it: one row per trial, the columns in `app/README.md`, no column that says whether the answer was right.

## 8. Layout
- [ ] At your pilot screen size, the swimlane and the details panel are visible without much scrolling. Note the screen size and anything cramped.
- [ ] The lane marks are readable with the colours as shown (blue circle, orange square). If you or a pilot participant have colour-vision difficulty, say so.

Delete the TEST data afterwards with "Delete saved data" on the start screen.
