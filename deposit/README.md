# Processed inputs for the nycped analysis

This record holds the two processed input files read by the `nycped` Python package. The package, tests, and reproduction guide are at https://github.com/AdiBak/nyc-pedestrian-poverty-exposure and archived at https://doi.org/10.5281/zenodo.23754868.

These files support the preprint "Exposure-Adjusted Pedestrian Harm Is 16 Percent Higher per 10 Percentage Points of Neighborhood Poverty in New York City".

## Files

| File | Rows | Columns | Size in bytes | SHA-256 |
|---|---|---|---|---|
| `tract_table.csv` | 2,189 | 11 | 161,574 | `16632c5696a001e00acb16f6a3396c9547db6fe31d5baf9b97169c3022d3a208` |
| `ped_harm_crashes.csv` | 37,815 | 5 | 1,087,788 | `bdfb46ee5da7c1b68a36c1fb7e8a1bfa98fabed41692eb456188831e6fdc76f5` |

## ped_harm_crashes.csv

One row per pedestrian harm crash in New York City, 2019 to 2023. A crash qualifies when at least one pedestrian was injured or killed. Highway crashes and crashes without usable coordinates were dropped. The file has no identifiers, no dates finer than the year, and no vehicle details.

| Column | Meaning |
|---|---|
| `year` | Crash year, 2019 to 2023 |
| `lat`, `lon` | Crash location in degrees |
| `ped_inj` | Pedestrians injured in the crash (sums to 38,937) |
| `ped_kill` | Pedestrians killed in the crash (sums to 469) |

Source: NYC Motor Vehicle Collisions, Crashes (NYPD), NYC Open Data dataset h9gi-nx95, export dated 10 August 2026.

## tract_table.csv

One row per census tract with at least 1,000 residents.

| Column | Meaning |
|---|---|
| `GEOID` | 11 digit 2020 census tract identifier, to be read as text |
| `Total_Population` | ACS 2019 to 2023 five-year estimate |
| `Poverty_Rate_Percent` | Share of residents below the poverty line (ACS table S1701) |
| `Walk_Share`, `Transit_Share` | Share of workers who walk or use transit to work (ACS table S0801) |
| `Commercial_Share` | Share of lot floor area that is commercial (NYC PLUTO) |
| `ZCTA_cluster` | ZIP Code Tabulation Area used to cluster standard errors |
| `Ped_Killed`, `Ped_Injured`, `Crashes` | Pedestrian deaths, pedestrian injuries, and all crashes in the tract, 2019 to 2023 |
| `n_years` | Number of years in the window (always 5) |

Sources: American Community Survey 2019 to 2023 five-year estimates (U.S. Census Bureau) and Primary Land Use Tax Lot Output (NYC Department of City Planning).

## Provenance

Both files were produced by `scripts/00_export_processed_inputs.py` in the code repository. The script printed 2,189 tracts, 37,815 crashes, and 469 deaths.

## Not included

The NYC Walks pedestrian volume network is not redistributed because its supplementary file states no license. The `nycped fetch` command downloads it from the publisher. See `docs/REPRODUCE.md` in the repository.

## License

CC BY 4.0. Attribute NYC Open Data, the New York City Police Department, the U.S. Census Bureau, and the New York City Department of City Planning as the original sources.
