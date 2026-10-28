# Data release notes

These notes describe the two processed input files that the `nycped` package reads, and what goes into a public data deposit (for example on Zenodo) at submission.

## Files in the deposit

| File | Rows | Columns | Size | SHA-256 |
|---|---|---|---|---|
| `tract_table.csv` | 2,189 | 11 | 161,574 bytes | `16632c5696a001e00acb16f6a3396c9547db6fe31d5baf9b97169c3022d3a208` |
| `ped_harm_crashes.csv` | 37,815 | 5 | 1,087,788 bytes | `bdfb46ee5da7c1b68a36c1fb7e8a1bfa98fabed41692eb456188831e6fdc76f5` |

### `ped_harm_crashes.csv`

One row per pedestrian harm crash. A crash qualifies when at least one pedestrian was injured or killed. The table has no identifiers, no dates finer than the year and no vehicle details.

| Column | Meaning |
|---|---|
| `year` | Crash year, 2019 to 2023 |
| `lat`, `lon` | Crash location in degrees. Latitude runs from 40.504 to 40.913 and longitude from -74.251 to -73.701. Most points sit at intersections. |
| `ped_inj` | Pedestrians injured in the crash. The column sums to 38,937. |
| `ped_kill` | Pedestrians killed in the crash. The column sums to 469. |

There are no missing values. Highway crashes were dropped with a keyword rule on street names. Crashes without usable coordinates were dropped.

### `tract_table.csv`

One row per census tract in the analysis, with at least 1,000 residents. The package uses the covariates. The crash counts are carried along for reference.

| Column | Meaning |
|---|---|
| `GEOID` | 11 digit 2020 census tract identifier. Read it as text. |
| `Total_Population` | ACS 2019 to 2023 5-year estimate |
| `Poverty_Rate_Percent` | Share of residents below the poverty line, ACS table S1701 |
| `Walk_Share`, `Transit_Share` | Share of workers who walk or use transit to work, ACS table S0801 |
| `Commercial_Share` | Share of lot floor area that is commercial, from NYC PLUTO |
| `ZCTA_cluster` | ZIP area used to cluster standard errors |
| `Ped_Killed`, `Ped_Injured`, `Crashes` | Pedestrian deaths, pedestrian injuries and all crashes in the tract, 2019 to 2023 |
| `n_years` | Number of years in the window, always 5 |

There are no missing values.

## How the files were made

Both come from `scripts/00_export_processed_inputs.py`, run in the Milestone 5 session of the original notebook on 28 October 2026. The crash file is the NYC Motor Vehicle Collisions Crashes export dated 10 August 2026. The tract table combines the ACS and PLUTO with ZIP codes recovered from crash coordinates. The script printed 2,189 tracts, 37,815 crashes and 469 deaths, matching the published run.

## What is not in the deposit

- **The NYC Walks network and any table of its volumes.** The supplementary file states no license, so it is not redistributed. The `fetch` command downloads it from the publisher. The site level tables carry crossing volumes derived from it, so they stay out of the deposit too, unless the authors confirm terms. The package rebuilds them in a few minutes from the two files above.
- **The raw centerline file.** It is a large public NYC dataset and `fetch` downloads it. The checksum of the file used is in `docs/REPRODUCE.md`.
- **The raw NYC crash file.** It is large and the city revises it over time. The crash extract above freezes the version used.

## Terms

Check the current terms before posting, since the exact wording was not confirmed here.

- NYC Open Data data are published for public reuse under the city's terms of use. Attribute the Department of Transportation and NYPD as the source of the crash records.
- American Community Survey and Census boundary data are in the public domain.
- PLUTO is published on NYC Open Data under the same city terms.
- Suggested license for the deposit is CC BY 4.0, with the attribution above.

## Draft Zenodo metadata for the data deposit

- **Type.** Dataset
- **Title.** Processed inputs for NYC pedestrian harm, neighborhood poverty and pedestrian exposure
- **Creator.** Bakshi, Aditya
- **Description.** Two derived files used to reproduce the analysis in the accompanying paper and code. A table of 37,815 pedestrian harm crashes in New York City, 2019 to 2023, and a table of 2,189 census tracts with poverty, commuting and land use measures. Built from NYC Open Data crash records, the American Community Survey and NYC PLUTO.
- **License.** CC BY 4.0
- **Related identifiers.** Is supplement to the code release and to the paper. Add both identifiers when they exist.
- **Keywords.** pedestrian safety, New York City, traffic crashes, poverty, exposure

## Checklist at submission

1. Make the GitHub repository public.
2. Turn on the Zenodo and GitHub integration for the repository.
3. Create a release such as v1.0.0. Zenodo archives it and issues a code DOI.
4. Upload the two data files as a separate Zenodo dataset deposit with the metadata above.
5. Put both DOIs in the README, the citation file, docs/REPRODUCE.md and the paper.
6. Ask the authors of NYC Walks about terms of use, and whether the site level tables may be shared.
7. Rerun the verify command from a clean clone and record the date.
