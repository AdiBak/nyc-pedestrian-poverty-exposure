# NYC pedestrian harm, neighborhood poverty and pedestrian exposure

Research code for an analysis of how pedestrian harm in New York City relates to neighborhood poverty once pedestrian exposure and street design are accounted for. The analysis extends a Transportation Data Science Project (TDSP) Navigator notebook. A preprint is in preparation.

**Status.** Version 0.4.3. The analysis is a Python package, `nycped`, with unit tests and a command line. See "What has been verified" below for what has and has not been run.

## Main findings

Crashes from 2019 through 2023 are assigned to 38,477 crossing sites, which are mostly intersections. Rate ratios are per 10 point increase in the tract poverty rate, with 95 percent intervals, from Poisson regression with standard errors clustered by ZIP area.

| Analysis | Rate ratio |
|---|---|
| Pedestrian harm crashes, crossing volume only | 1.30 (1.26 to 1.35) |
| Plus street width, lanes and speed limit | 1.28 (1.23 to 1.32) |
| Plus tract controls and borough effects (primary) | 1.16 (1.12 to 1.20) |
| Pedestrian deaths, primary model | 1.29 (1.17 to 1.42) |

- The harm estimate stays between 1.12 and 1.25 across alternative estimators, site definitions, time periods, boroughs, measurement error in the volumes and geographic scales.
- Exposure drives the estimate more than geography does. With residents only, tract and ZIP-area ratios sit between 1.06 and 1.09.
- About 60 percent of the death gap comes from more harm crashes and about 40 percent from a higher chance that a crash is fatal. The severity part is suggestive, since its interval touches 1.
- These are associations. The analysis has no vehicle traffic volumes.

All numbers, checks and limitations are in `docs/research_log.md`.

## Quick start

```
pip install -e ".[test]"
pytest                                   # unit tests, about 10 seconds, no data needed
export NYCPED_DATA_DIR=/path/to/data     # any empty folder
python -m nycped fetch                   # downloads the public sources and writes MANIFEST.json
```

`fetch` records the URL, date, size and SHA-256 checksum of every file it downloads in `MANIFEST.json`, so a later run can check that it is using the same inputs.

## Reproducing the results

For a step by step guide with the expected output, see `docs/REPRODUCE.md`. For the processed inputs and the planned data deposit, see `docs/DATA_RELEASE.md`.

There are two routes.

**Check the numbers from a saved site table.** This needs the site table and no raw data. It reruns the primary models and compares them with the stored expected values.

```
python -m nycped verify --sites site_table.csv
python -m nycped models --sites site_table.csv --bootstrap 500
python -m nycped robustness --sites site_table.csv
python -m nycped scale --sites site_table.csv
```

**Rebuild everything from the raw sources.** Two small inputs come from the original Colab notebook, because they depend on the Census API and on the NYC crash export.

1. In the TDSP notebook session, after the Milestone 5 setup, run `scripts/00_export_processed_inputs.py`. It writes `tract_table.csv` and `ped_harm_crashes.csv` to your data folder. The script prints the row counts to expect.
2. Run the package.

```
python -m nycped fetch
python -m nycped sites --crashes ped_harm_crashes.csv --tract-table tract_table.csv
python -m nycped models --sites site_dataset.csv
```

| Command | What it does |
|---|---|
| `fetch` | Downloads the NYC Walks files, the street centerlines and the Census tract boundaries |
| `sites` | Infers crosswalks, groups them into sites, assigns crashes and writes `site_dataset.csv` |
| `models` | Models A to D for harm crashes and deaths, the frequency and severity split, optional cluster bootstrap |
| `robustness` | Measurement error in the volumes, time periods, leave one borough out |
| `scale` | Tracts, ZIP areas and random contiguous zones |
| `checks` | Spatial dependence, truck routes and sampling error in the ACS poverty rate |
| `paper` | Writes the paper's tables, robustness figure and `numbers.json` into `paper/generated` |
| `verify` | Compares a fresh fit with the stored expected values |

## What has been verified

Run in Python 3.13 with the versions in `requirements-lock.txt`.

- The unit tests pass. They use small synthetic examples with known answers, including recovery of a known poverty effect and checks of the crosswalk, site and crash assignment logic.
- Rebuilding the crosswalks and sites from the raw NYC Walks and centerline files gives 110,603 crosswalk segments and 41,937 sites, the same as the original run. It takes about 25 seconds and 400 MB of memory.
- `verify` on the saved site table passes all six checks, including 1.16 for harm crashes and 1.29 for deaths.
- `models`, `robustness` and `scale` reproduce the numbers in the research log.
- `fetch` downloads the sources, and the checksums of the NYC Walks files match the originals.
- The `sites` command ran end to end on synthetic crashes placed on the real sites.

- The export script ran in the Milestone 5 session and printed the expected counts, 2,189 tracts, 37,815 crashes and 469 deaths.
- The full rebuild, `fetch`, `sites` and `verify`, ran in Google Colab from the raw sources and the two processed inputs. It gave 110,603 crosswalk segments, 41,937 sites and 38,477 sites in the model, and all six checks passed.

Not yet run. The Colab runner notebook and the continuous integration workflow have not been run.

## Package layout

```
src/nycped/      The package. config, io, exposure, crashes, sitedata, models, robustness, scale, cli
tests/           Unit tests, plus integration tests that run only when NYCPED_DATA_DIR holds the data
scripts/         00_export_processed_inputs.py, and colab_cells/ with the original notebook cells
notebooks/       The TDSP Navigator notebook with its additional work section, and run_on_colab.ipynb
docs/            Research log and changelog
data/            Data notes only. No third-party data are stored here.
```

`scripts/colab_cells/` holds the original numbered Colab cells that produced the first results. They are kept for the record. The package supersedes them.

## Running on Google Colab

Open `notebooks/run_on_colab.ipynb`. It mounts Drive, installs the package, and runs the commands above. While the repository is private, add a GitHub access token as a Colab secret named `GITHUB_TOKEN`. Do not paste credentials into notebook cells.

## Data

No third-party data are stored in this repository. See `data/README.md` for sources and terms. The NYC Walks supplementary file states no license, so use it with citation and do not redistribute it.

## Reproducibility notes

- Random seeds are fixed. The measurement error test uses 2026, the cluster bootstrap 7 and the random zonings 11.
- Continuous integration runs the unit tests on every push, on Python 3.11 and 3.12.
- Library versions are unpinned in `pyproject.toml`. `requirements-lock.txt` records the versions used for the verified run.

## AI assistance

Parts of this work were developed with AI assistance (Claude, Anthropic) for literature search, planning the analyses and drafting code. The author directed the work, ran the analyses and takes responsibility for the results and their interpretation.

## License and citation

Code is released under the MIT license. See `LICENSE`. To cite the code, see `CITATION.cff`.
