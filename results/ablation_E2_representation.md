# E2 representation ablation (no LLM)

SCOPE: E2: 82 eligible pool items; simple rules on a text format; not language models and not people; says nothing about how a human reads either view; no p-values

## pool_82 (n = 82, mean chance 0.165)

| rule | available in | exact | agent | tolerant (+-1) | found no step |
|---|---|---|---|---|---|
| always step 1 | R1 only (needs step numbers) | 0.220 | 0.293 | 0.232 | 0 |
| always step 3 | R1 only (needs step numbers) | 0.561 | 0.695 | 0.622 | 0 |
| first step by a non-coordinating agent | R1 only (needs agent names) | 0.573 | 0.707 | 0.622 | 0 |
| first step with a tool call | R1 and R2 | 0.366 | 0.500 | 0.402 | 15 |
| first step with tool output | R1 and R2 | 0.366 | 0.500 | 0.402 | 15 |
| first step with a number not in the question | R1 and R2 | 0.183 | 0.256 | 0.488 | 3 |

| identifiability in plain text (R2) | items | share |
|---|---|---|
| label step message empty (tool-only step) | 35 of 82 | 0.427 |
| label step message duplicated by another step | 0 of 82 | 0.000 |
| responsible agent also wrote the previous step (speaker change lost in R2) | 4 of 82 | 0.049 |

## block_a_24 (n = 24, mean chance 0.163)

| rule | available in | exact | agent | tolerant (+-1) | found no step |
|---|---|---|---|---|---|
| always step 1 | R1 only (needs step numbers) | 0.250 | 0.417 | 0.292 | 0 |
| always step 3 | R1 only (needs step numbers) | 0.208 | 0.542 | 0.375 | 0 |
| first step by a non-coordinating agent | R1 only (needs agent names) | 0.250 | 0.583 | 0.375 | 0 |
| first step with a tool call | R1 and R2 | 0.083 | 0.417 | 0.167 | 5 |
| first step with tool output | R1 and R2 | 0.083 | 0.417 | 0.167 | 5 |
| first step with a number not in the question | R1 and R2 | 0.167 | 0.333 | 0.333 | 1 |

| identifiability in plain text (R2) | items | share |
|---|---|---|
| label step message empty (tool-only step) | 6 of 24 | 0.250 |
| label step message duplicated by another step | 0 of 24 | 0.000 |
| responsible agent also wrote the previous step (speaker change lost in R2) | 4 of 24 | 0.167 |

## block_b_8 (n = 8, mean chance 0.122)

| rule | available in | exact | agent | tolerant (+-1) | found no step |
|---|---|---|---|---|---|
| always step 1 | R1 only (needs step numbers) | 0.250 | 0.375 | 0.250 | 0 |
| always step 3 | R1 only (needs step numbers) | 0.250 | 0.625 | 0.375 | 0 |
| first step by a non-coordinating agent | R1 only (needs agent names) | 0.250 | 0.625 | 0.375 | 0 |
| first step with a tool call | R1 and R2 | 0.250 | 0.500 | 0.375 | 0 |
| first step with tool output | R1 and R2 | 0.250 | 0.500 | 0.375 | 0 |
| first step with a number not in the question | R1 and R2 | 0.250 | 0.375 | 0.500 | 0 |

| identifiability in plain text (R2) | items | share |
|---|---|---|
| label step message empty (tool-only step) | 3 of 8 | 0.375 |
| label step message duplicated by another step | 0 of 8 | 0.000 |
| responsible agent also wrote the previous step (speaker change lost in R2) | 0 of 8 | 0.000 |

