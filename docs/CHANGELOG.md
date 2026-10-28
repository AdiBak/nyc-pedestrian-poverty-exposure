# Changelog

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
