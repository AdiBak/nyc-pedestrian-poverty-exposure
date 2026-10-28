# NYC pedestrian harm, neighborhood poverty and pedestrian exposure

Research code for an analysis of how pedestrian harm in New York City relates to neighborhood poverty once pedestrian exposure and street design are accounted for. The work extends a Transportation Data Science Project (TDSP) Navigator notebook. A preprint is in preparation.

**Status.** Research code, version 0.1. The scripts were developed and run in Google Colab. Running them outside Colab has not been tested, and the Python versions are not pinned yet.

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

## Repository layout

```
scripts/      Numbered scripts, in run order (Colab cells in Jupytext percent format)
notebooks/    The TDSP Navigator notebook, with the additional work section and saved outputs
docs/         Research log with design decisions, results and open items
data/         Data notes only. No third-party data are stored here.
```

## How to run

1. Put the NYC crash file (`Motor_Vehicle_Collisions_-_Crashes_20260810.csv` from NYC Open Data) in the top level of your Google Drive.
2. Save a free Census API key in Colab Secrets as `CENSUS_API_KEY` and switch on notebook access.
3. Create the Drive folder `MyDrive/TDSP/nyc_walks`. The scripts save and read their files there.
4. Run the scripts in order. Scripts 00, 04, 05, 08 and 09 need the session that script 00 builds, so run them in the same Colab session, or rerun 00 first.

| Script | What it does |
|---|---|
| `00_setup_crash_and_acs_tables.py` | Loads crashes, recovers missing ZIPs, builds the ACS and PLUTO tract tables and the helper functions |
| `01_download_nyc_walks.py` | Downloads the NYC Walks supplementary files into Drive |
| `02_fetch_centerlines.py` | Downloads NYC street centerlines and prints their road types |
| `03_crosswalk_tract_exposure.py` | Infers crosswalks and totals crossing volume by tract |
| `04_tract_models.py` | Tract level poverty models with exposure |
| `05_site_model_first_pass.py` | Builds sites, assigns crashes, saves the site table |
| `06_site_models_robust.py` | Primary estimates, Poisson and negative binomial GLM, first checks |
| `07_measurement_error_simex.py` | Sensitivity to error in the pedestrian volumes |
| `08_robustness_checks.py` | Site definition, time period and borough |
| `09_deaths_battery.py` | Pedestrian deaths, frequency versus severity, cluster bootstrap |
| `10_scale_zone_analysis.py` | Scale and zone effects across tracts, ZIP areas and random zones |

Script 05 fits its first models with negative binomial maximum likelihood, which did not converge for one specification. Script 06 replaces those estimates, so read 06, not 05.

Scripts 05, 08 and 09 read a 275 MB file and rebuild the sites, so each takes several minutes.

## Data

No third-party data are stored in this repository. See `data/README.md` for sources and terms. The NYC Walks supplementary file states no license, so use it with citation and do not redistribute it.

## Reproducibility notes

- Random seeds are set in the scripts that simulate. The measurement error test uses 2026, the cluster bootstrap 7 and the random zonings 11.
- Package versions are not pinned. After a clean end to end run, create a lock file.
- The notebook in `notebooks/` keeps the outputs from the runs that produced the numbers above, except the output of script 06, which came from a separate Python session on the saved site table. Rerun that cell to refresh it.

## AI assistance

Parts of this work were developed with AI assistance (Claude, Anthropic) for literature search, planning the analyses and drafting code. The author directed the work, ran every script and takes responsibility for the results and their interpretation.

## License and citation

Code is released under the MIT license. See `LICENSE`. To cite the code, see `CITATION.cff`.
