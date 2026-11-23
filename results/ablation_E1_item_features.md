# E1 item-feature analysis

SCOPE: E1: 82 eligible pool items; simple rules only; descriptive (no p-values, no intervals); position and category are confounded; not a model of human or LLM difficulty

Adjusted R-squared of a linear probability model (outcome ~ features). 'alone' = one feature; 'drop one' = all features except that one; the last column is the change from the full model (negative = that feature carried explanatory share).

## always step 1 hits the label

Full model adjusted R2: 0.801

| feature | alone | full minus this feature | change when dropped |
|---|---|---|---|
| category | 0.81 | 0.261 | -0.539 |
| framework | 0.104 | 0.803 | 0.003 |
| length | 0.048 | 0.802 | 0.001 |
| n_agents | -0.008 | 0.805 | 0.004 |
| position | 0.062 | 0.803 | 0.002 |

## always step 3 hits the label

Full model adjusted R2: 0.816

| feature | alone | full minus this feature | change when dropped |
|---|---|---|---|
| category | 0.428 | 0.487 | -0.328 |
| framework | 0.207 | 0.814 | -0.001 |
| length | 0.195 | 0.814 | -0.002 |
| n_agents | 0.011 | 0.816 | -0.0 |
| position | 0.326 | 0.445 | -0.371 |

## always step 3 names the responsible agent

Full model adjusted R2: 0.546

| feature | alone | full minus this feature | change when dropped |
|---|---|---|---|
| category | 0.522 | 0.174 | -0.372 |
| framework | 0.158 | 0.542 | -0.005 |
| length | 0.08 | 0.546 | -0.001 |
| n_agents | -0.02 | 0.554 | 0.007 |
| position | -0.01 | 0.509 | -0.037 |

## chance accuracy 1/steps

Full model adjusted R2: 0.569

| feature | alone | full minus this feature | change when dropped |
|---|---|---|---|
| category | 0.0 | 0.506 | -0.063 |
| framework | 0.056 | 0.537 | -0.032 |
| length | 0.403 | 0.409 | -0.16 |
| n_agents | 0.001 | 0.479 | -0.09 |
| position | 0.085 | 0.488 | -0.081 |

## Position by category (counts)

| position_stratum | Human-Interaction Hallucination | Planning Hallucination | Reasoning Hallucination | Retrieval Hallucination |
|---|---|---|---|---|
| early | 22 | 21 | 15 | 7 |
| later | 0 | 0 | 16 | 1 |

## Framework and category by labelled step (counts)

| framework | category | 1 | 2 | 3 | 4+ |
|---|---|---|---|---|---|
| Camel | Human-Interaction Hallucination | 0 | 0 | 22 | 0 |
| Camel | Planning Hallucination | 2 | 0 | 0 | 0 |
| Camel | Reasoning Hallucination | 0 | 0 | 7 | 4 |
| Magentic_One | Planning Hallucination | 16 | 0 | 3 | 0 |
| Magentic_One | Reasoning Hallucination | 0 | 1 | 7 | 12 |
| Magentic_One | Retrieval Hallucination | 0 | 0 | 7 | 1 |

## Rates by position (share of items)

| position_stratum | step1_hit | step3_hit | step3_agent_ok | chance |
|---|---|---|---|---|
| early | 0.277 | 0.708 | 0.708 | 0.177 |
| later | 0.0 | 0.0 | 0.647 | 0.121 |

Correlation in the pool: corr(words, 1/steps) = -0.64; corr(words, steps) = 0.66.

Reading note: outcomes 1 to 3 depend on the label position by definition, so position is expected to explain them; the table does not show what makes an item hard for people.
