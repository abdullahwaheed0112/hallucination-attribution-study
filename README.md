# Locating the first hallucinated step in multi-agent LLM traces

A study instrument, item set and analysis code for one question: **do people find the first hallucinated step in a multi-agent LLM trace more accurately with a plain console log (View A) or with an information-equivalent swimlane view (View B)?** Answers are scored against the AgentHallu labels.

**Status.** The study has not been run with participants, because ethics review for a classmate study is unresolved. The repository contains the pipeline that builds the item set, the offline study app, participant-free baselines and ablations, analysis code tested on simulated data, the blind screening of the labels by the two authors, and the paper (`paper/`). It contains no result about whether either view helps. Nothing in `simulated/` is a finding.

Authors: Abdullah Waheed, Chaudhary Abdul Moiz (NUCES, Pakistan).

## 1. Repository layout

| Folder | Contents |
|---|---|
| `paper/` | LaTeX source (`paper.tex`, `refs.bib`), figures and the compiled `paper.pdf` |
| `app/` | Static study app (HTML, CSS, JavaScript, SVG). No build step, no network calls |
| `src/pipeline/` | Item selection, app data export, representation ablation, screening agreement |
| `scripts/` | Baselines, analysis, simulation, figures, checks, power planning |
| `results/` | Real outputs from the item set, baselines, ablations, screening and checks |
| `simulated/`, `figures/simulated/` | SIMULATED outputs only, used to test the analysis code |
| `figures/real/` | Figures made from real files (no participants) |
| `docs/` | Decision log, item-set and ablation notes, checklists, session guide |

Not included: the AgentHallu and Who&When datasets (`data/`), the written study-design document, the answer-key files `results/labels_PRIVATE.json` and `results/suggestion_key_PRIVATE.json` (the pipeline regenerates them), the authors' pilot sessions, and the PDFs of the cited papers.

## 2. Requirements

- Windows 10 or 11 with PowerShell (the commands also work elsewhere with path changes). No Node.js, no LLM, no API key.
- Python 3.11 or newer. Developed with Python 3.15.0.
- Packages (tested versions: numpy 2.5.4, scipy 1.18.1, pandas 3.0.6, statsmodels 0.15.0, matplotlib 3.11.2, pypdf 7.0.0):

```powershell
python -m pip install numpy scipy pandas statsmodels matplotlib pypdf
```

- A LaTeX distribution (for example MiKTeX) only if you want to rebuild the paper.

## 3. Get the data

Clone or download the two datasets into a folder named `data/` at the top of this repository, as given by their authors:

- AgentHallu, commit `9ffe8bc` (https://github.com/liuxuannan/AgentHallu)
- Who&When, commit `b2bae5c` (https://github.com/mingyin1/Agents_Failure_Attribution)

Treat `data/` as untrusted and read-only: do not run anything from it and do not open its `.env` file. The scripts that read it use only the standard library and are run with `python -I`. In the commands below, set this variable first (adjust the path to where AgentHallu sits):

```powershell
$AH = "data\AgentHallu-9ffe8bc888feaf15d89833f4b0e3c4697f44acc1\AgentHallu-9ffe8bc888feaf15d89833f4b0e3c4697f44acc1\AgentHallu"
```

## 4. Rebuild the item set and the baselines

Each command prints its own check against the planned numbers (82 eligible items, 47 Magentic-One and 35 Camel, 46 labels at step 3, median length 1,135.5 words, 6 later-position items below the median). Seeds are fixed, so reruns give identical files.

```powershell
python -I scripts\pool.py $AH
```

```powershell
python -I src\pipeline\build_pool.py $AH results
```

```powershell
python -I src\pipeline\select_items.py $AH results
```

```powershell
python -I src\pipeline\export_app_data.py $AH results app\data
```

```powershell
python -I scripts\baselines.py $AH results
```

```powershell
python -P -E scripts\write_run_info.py results
```

Expected: `ALL M2 NUMBERS REPRODUCED`, all assertions `PASS` in `results\selection_check.txt`, and `RESULT: REPRODUCED` from the baselines. Library versions and every seed are written to `results\run_info.json`.

Planning simulations for statistical power (assumptions, about a minute each):

```powershell
python -P -E scripts\power2.py
```

```powershell
python -P -E scripts\power.py
```

## 5. The study app

```powershell
python -m http.server 8765 --directory app
```

Open `http://localhost:8765` (use a second terminal for other commands; stop the server with Ctrl+C). Opening `app\index.html` directly is meant to work but has not been tested, and some browsers restrict storage for `file://` pages.

- **Self-test:** open `http://localhost:8765/selftest.html`. It must report `RESULT: PASS` with 6,439 checks and 0 failed. It compares the text of every step in both views with text built independently from the raw data.
- **Views:** View A is a single scrolling console log. View B is a swimlane (one row per agent) with a details panel. Both use the same text, the same collapse rule for long tool output, the same search and the same answer action.
- **Modes:** practice, Block A (unaided), Block B (with an "AI suggests this step" badge, no rationale) and screening (blind labelling by a researcher).
- **Data label:** `TEST` (default) for any run of the app itself, `PILOT` only for sessions by the two authors.
- More detail and the data schema: `app\README.md`, `docs\session_guide.md`, `docs\equivalence_checklist.md`.

## 6. Analysis

The analysis scripts read the trial-level file that the app exports. They apply inference (model, p-values, intervals) only to data labelled `SIMULATED`; data labelled `PILOT` or `TEST` get descriptive output only.

On simulated data (pipeline test only; every output is stamped SIMULATED):

```powershell
python -P -E scripts\simulate_trials.py results simulated 32 20261201 0.8
```

```powershell
python -P -E scripts\trial_io.py simulated\trials_SIMULATED.csv results
```

```powershell
python -P -E scripts\analyze.py simulated\trials_SIMULATED.csv results simulated --tlx simulated\tlx_SIMULATED.csv
```

```powershell
python -P -E scripts\recovery_test.py results simulated
```

The recovery test (about 3 minutes) checks that a known injected effect is recovered and must pass before the model is used on real data.

Participant-free figures and ablations on real files:

```powershell
python -P -E scripts\figures.py real results figures\real
```

```powershell
python -P -E scripts\ablation_items.py results
```

```powershell
python -I src\pipeline\ablation_representation.py $AH results
```

On a real export from the app (replace the file names; scoring reads `results\labels_PRIVATE.json`, which the pipeline creates in section 4):

```powershell
python -P -E scripts\trial_io.py <trials.csv> results
```

```powershell
python -P -E scripts\analyze.py <trials.csv> results <output folder> --tlx <tlx.csv>
```

Reproducibility note: reruns are byte-identical except the variational-Bayes mixed-model fit, whose results agree to about six significant digits but differ in the last digits (`simulated\trials_SIMULATED__results.json` and `simulated\recovery_*_runs_SIMULATED.csv`).

## 7. Screening agreement

Both authors labelled the first hallucinated step blind in screening mode. Their files are in `results\screening\`. To recompute agreement (Cohen's kappa between screeners, agreement with the label, items where both differ from the label):

```powershell
python -I src\pipeline\screening_agreement.py results\screening\AW_screening.csv results\screening\AM_screening.csv results\screening --labels results\labels_PRIVATE.json --confirm-both-finished
```

Without `--labels ... --confirm-both-finished` the script computes only the agreement between the two screeners and never opens a label file. Test on synthetic files:

```powershell
python -P -E scripts\test_screening_agreement.py $env:TEMP\screening_test
```

## 8. Checks

```powershell
python -P -E scripts\check_paper.py
```

`check_paper.py` recomputes the numbers claimed in the paper from `results\`; its pilot checks need the authors' pilot files, which are not in this repository. `scripts\check_comparison_sources.py` searches the cited PDFs for each figure in the comparison table (you supply the PDFs).

## 9. Build the paper

```powershell
cd paper
latexmk -pdf paper.tex
```

## 10. Rules that hold for this project

1. Every number in a written result comes from a script that reads real files; the script and its output are saved.
2. Simulated data stay in `simulated\` and `figures\simulated\`, are named SIMULATED, and are never reported as findings.
3. Data from the two authors' sessions are `PILOT`, reported descriptively only: no p-values, no confidence intervals, no claims of significance.
4. Deviations from the planned design are logged in `docs\decisions_log.md` with what, why, date and impact.
5. Nobody outside the two authors may use the app until ethics review is resolved.

## 11. Licences and credits

- Traces: AgentHallu (Liu et al., 2026), https://github.com/liuxuannan/AgentHallu, commit 9ffe8bc. The repository states CC BY 4.0 and the paper states CC BY-NC-SA 4.0; we follow the stricter terms (attribution, non-commercial, share-alike). Files here that contain AgentHallu trace text (`results\step_table.csv`, `app\data\items.js`) are under those terms. See `NOTICE`.
- Who&When (Zhang et al., 2025): MIT licence in its repository. It was not needed for the item set.
