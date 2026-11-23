# SIMULATED - pipeline test only

Input: trials_SIMULATED.csv. Tables written: trials_SIMULATED__metrics_by_view.csv, trials_SIMULATED__metrics_by_view_and_stratum.csv, trials_SIMULATED__block_b_agreement.csv, trials_SIMULATED__error_classes.csv, trials_SIMULATED__signed_error_wrong_answers.csv, trials_SIMULATED__tlx_by_view.csv, trials_SIMULATED__results.json.

## Block A by view

| view | n_trials | n_participants | exact_acc | agent_acc | tolerant_acc | mean_signed_error | median_time_s | brier | timeouts | mean_confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| console | 192.0 | 32.0 | 0.344 | 0.573 | 0.682 | -0.247 | 72.744 | 0.22 | 6.0 | 3.194 |
| visual | 192.0 | 32.0 | 0.531 | 0.74 | 0.76 | 0.075 | 69.49 | 0.203 | 5.0 | 3.503 |

## Primary model (1: VB mixed GLM, participant + participant-by-view + item)

Odds ratio visual vs console: 2.65 (95% 1.92 to 3.66). Interval type: posterior (variational Bayes), not a frequentist confidence interval.
