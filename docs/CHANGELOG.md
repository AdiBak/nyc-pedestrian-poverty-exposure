# Changelog

## 0.4.5, 28 October 2026

- Declared matplotlib as a dependency. The paper command's figures need it, and the GitHub Actions run failed without it from the paper command commit onward.

## 0.4.4, 28 October 2026

- Map figure: removed the axis labels that tract plotting adds and shrank the crash markers, which had saturated panel (b).

## 0.4.3, 28 October 2026

- The paper command also writes `map.png`, two panels of the study sites (by tract poverty, and sized by harm crashes), with tract outlines when `ny_tracts2020.zip` is present. Added a test.

## 0.4.2, 28 October 2026

- The paper command also writes `gradient.pdf` (observed over expected harm by poverty decile, with ZIP area bootstrap intervals) and `ladder.pdf` (poverty ratio across models A to D).

## 0.4.1, 28 October 2026

- Fixed the paper command failing on the pedestrians injured check. Sites with no assigned crash had a missing injured count, and the loader now treats it as zero. Added a test.
- Colab rebuild on 28 October gave 38,477 sites. Truck route sites carry 1.47 times the harm, not 1.48.

## 0.4.0, 28 October 2026

- New command paper. It writes the paper's tables (`table_main.tex`, `table_scale.tex`), the robustness figure, `robustness.csv` and `numbers.json` from a site table, so each number in the paper traces to code. Pass `--crashes` and `--tract-table` to include the site definition checks, which rebuild the site table at other grouping distances and crash radii.
- The site table now carries a `injured` column, so the pedestrians injured check runs from the site table.
- The `paper/` folder holds the LaTeX draft. Its `generated/` files are placeholders until the command has run on the final site table.

## 0.3.1, 28 October 2026

- The sampling error check now reports the reliability of the poverty rate among tracts alike on the other controls, 0.689, next to the unconditional 0.786.
- Recorded the sampling error results in docs/CHECKS_LOG.md. Corrected poverty ratios for harm crashes run from 1.19 to 1.22 against the naive 1.16.

## 0.3.0, 28 October 2026

- New command checks, with the checks a reviewer is likely to ask for. Moran I of the residuals, standard errors clustered at several spatial scales, a spatial block bootstrap, ZIP area fixed effects, a truck route proxy for heavy vehicle traffic, and sensitivity to sampling error in the ACS poverty rate. Results are in docs/CHECKS_LOG.md.
- The site table now carries any_truck, from the centerline truck route field. Rebuild it with the sites command to get it.
- A lean fixed effects estimator, poisson_fixed_effects, tested against statsmodels.
- scripts/01_export_tract_poverty_moe.py pulls tract poverty margins of error through the Census API, for the sampling error check.
- verify allows a difference of five sites. Python 3.13 gave 38,475 sites and Colab 38,477, with identical estimates to four decimals.

## 0.2.1, 28 October 2026

- Added `docs/REPRODUCE.md`, a five step guide with expected output from the confirmed end to end run.
- Added `docs/DATA_RELEASE.md`, which describes the two processed inputs, their checksums and the plan for a data deposit.
- Added `.zenodo.json` for the code release.
- `fetch` now labels files that were already present as recorded, with their modification time, and not as retrieved on the date it first saw them.

## 0.2.0, 28 October 2026

- The analysis is now a Python package, `nycped`, with a command line, unit tests and continuous integration. The original Colab cells moved to `scripts/colab_cells/`.
- `fetch` records the URL, date, size and checksum of every download in `MANIFEST.json`.
- `scripts/00_export_processed_inputs.py` writes the two small inputs that depend on the Census API and the crash export, so the package no longer needs the notebook session.
- `verify` compares a fresh fit with stored expected values.
- The centerline reader loads six columns, not about 60. Peak memory for rebuilding the sites fell to about 400 MB.
- Model results are freed between fits, which keeps memory use low on small machines.
- Checked in Python 3.13. The crosswalk and site counts, the model ladders, the robustness checks and the scale analysis match the original runs.

### New result from the package

Pedestrian deaths by year, model D, poverty rate ratio per 10 points. 2019 1.10 (0.93 to 1.30), 2020 1.43 (1.18 to 1.74), 2021 1.26 (1.02 to 1.57), 2022 1.42 (1.14 to 1.76), 2023 1.24 (1.00 to 1.54). The pooled estimate is 1.29. The intervals overlap, but 2019 is the lowest and its interval includes 1. With 69 to 96 deaths per year, treat the year to year pattern as noise.

## 0.1.0, 27 October 2026

- First version. The Colab cells that produced the results, the TDSP notebook with its additional work section, and the research log.
