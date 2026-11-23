# SIMULATED - pipeline test only

## Large-sample check (N = 200, 5 seeds per truth; pass rule in the script header)

| truth | mean_estimate | abs_error | covered_of_5 | models_used | verdict |
|---|---|---|---|---|---|
| 0.0 | 0.003 | 0.003 | 5 | 1 | PASS |
| 0.8 | 0.766 | 0.034 | 4 | 1 | PASS |

## Planned-size check (N = 32, 20 seeds per truth)

| truth | mean_estimate | sd_of_estimates | interval_covers_truth | interval_excludes_zero | of | models_used |
|---|---|---|---|---|---|---|
| 0.0 | -0.003 | 0.167 | 20 | 0 | 20 | 1 |
| 0.8 | 0.756 | 0.267 | 17 | 19 | 20 | 1 |

Estimates are log odds of the visual view. Intervals are posterior intervals from the model that was used (1 = VB mixed GLM with slope, 2 = without slope, 3 = GEE).
