# Step E: ablation definitions (written before any ablation was run)

Fri 2026-11-13. All ablations here need no participants and no LLM. Each one names its unit, its inputs, what it measures, and what it cannot say. Nothing here is a human-study result.

## E1. Item-feature analysis

- **Question.** Which of error position, trace length, number of agents, hallucination category and framework go with whether a simple rule hits the labelled step?
- **Unit and input.** The 82 eligible pool items (`results/pool.csv`, plus the agent at step 3 from `results/step_table.csv`). Block A is not analysed here: it was balanced by design on position and length, so those two features were fixed, not observed.
- **Outcomes (one per item).** (a) always-step-1 hits the label; (b) always-step-3 hits the label; (c) always-step-3 names the responsible agent; (d) chance accuracy 1/(number of steps), a continuous outcome.
- **Features.** Position (label at step 3 or earlier vs step 4 or later), length (words, standardised), number of agents (2, 3, 4), category (4 levels), framework (2 levels).
- **Method.** Linear probability model by least squares for each outcome. Report adjusted R-squared for each feature alone, for all features together, and the drop in adjusted R-squared when each feature is removed from the full model. Also cross-tabulate position by category, because 16 of the 17 later items are reasoning hallucinations. No p-values and no intervals: the 82 items are the whole eligible pool, not a sample from a larger population, and the outcomes are deterministic functions of the labels.
- **Scope.** Describes this pool and these simple rules. It does not say what makes an item hard for people or for an LLM. Position and category are confounded, so their separate shares are not identified. Outcomes (a) to (c) are partly definitional (the rule "always step 3" can only hit when the label is at step 3), so a high share for position is expected and not a finding about difficulty.

## E2. Representation ablation without an LLM

- **Question.** How much of what a simple rule can do depends on the console's agent-tagged, step-numbered format, compared with plain text?
- **Representations.** R1 = the console format (each step has its number and agent name). R2 = plain text (step boundaries visible, no step numbers, no agent names).
- **Rules.** Format-dependent rules need step numbers or agent names: always step 1, always step 3, "first step by an agent other than the coordinating agents" (Orchestrator, Planner, Coordinator). Text-only rules work in both: "first step with a tool call", "first step with tool output", "first step whose message contains a number that does not appear in the question". Each rule returns one step.
- **Measures.** (a) Exact and agent accuracy of each rule on the 82 pool items, with its chance-corrected comparison to the 16.5% mean chance; (b) in R2, the share of items where the step is still identifiable from text alone: the share of items where the labelled step's message is an exact duplicate of another step's message or is empty (a tool-only step), since plain text could not tell those steps apart; (c) the share of items where the responsible agent is the same as the agent of the previous step (R2 would lose the speaker change).
- **Scope.** Describes simple rules on a text format, not language models, not people. It does not show how a human reads either view; the human comparison is the main study. Context from M2 only: DoVer reported that adding step indices raised GPT-4o step accuracy from 6% to 24%; this ablation does not test that.

## E3. Pilot component use (correlational, needs the pilot file)

- **Question.** In the visual view, do trials where participants used search, opened step details or used the filter have different accuracy from trials where they did not?
- **Unit and input.** Block A trials in the visual view from a trial file; counts `n_search`, `n_details`, `n_filter` from the app log.
- **Method.** Descriptive table: number of trials, exact accuracy and median time with and without each component. No inference when the data label is not SIMULATED.
- **Scope.** Correlational only; people who use a component may be the ones who found the trial hard. With the pilot of two team members who know the labels' source, it can only check that the logging works. No pilot file exists yet, so on real data this is **not run**. The script is tested on SIMULATED data only, and its output is stamped.

## E4. Not possible now

- A full view-component ablation (lane marks, arrows, search marks, details panel each removed in their own condition) needs participants. It is future work.
- An LLM representation ablation (plain text versus tagged text) needs an LLM, which is not available (the project instructions Section 2). E2 above is the participant-free and LLM-free substitute and answers a narrower question.
