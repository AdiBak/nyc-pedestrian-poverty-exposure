# Data notes

No third-party data are stored in this repository. The scripts download what they need into `MyDrive/TDSP/nyc_walks` in Google Drive.

| Source | Used for | How to obtain | Terms |
|---|---|---|---|
| NYC Motor Vehicle Collisions, Crashes (NYPD) | Pedestrian harm outcomes, 2019 to 2023 | NYC Open Data, dataset h9gi-nx95. The study used the export dated 10 August 2026. | NYC Open Data terms of use |
| NYC Walks, Sevtsuk, Basu, Liu, Alhassan and Kollar (2026), Nature Cities | Modeled peak-hour pedestrian volumes on 315,577 sidewalk, crosswalk and footpath segments | Supplementary Data 1 on the article page, https://www.nature.com/articles/s44284-025-00383-y. Script 01 downloads it. | The metadata gives a preferred citation and no license. Cite it and do not redistribute the file. The metadata lists a contact for questions. |
| NYC Open Data, Centerline | Street width, travel lanes, posted speed, road type | https://data.cityofnewyork.us/d/inkn-q76z. Script 02 downloads it. | The catalog entry lists no license information. Cite it. |
| U.S. Census Bureau, American Community Survey 2019 to 2023 5-year estimates | Poverty, population, walking and transit commuting (tables S1701 and S0801) | Census API. Needs a free key. Script 00 pulls it. | Public domain |
| U.S. Census Bureau, 2020 cartographic boundary files | Tract and ZCTA geometry | Script 00 downloads them. | Public domain |
| NYC Department of City Planning, PLUTO | Commercial share of floor area | NYC Open Data. Script 00 pulls it. | NYC Open Data terms of use |

Files the scripts create in Drive include `supp_data_1_network.zip`, `centerline_inkn-q76z.geojson`, `tract_crossing_exposure_2018_2019_volumes.csv`, `crossing_sites_model_data.csv` and `sites_eps25_r30_by_year.csv`.

Notes on the NYC Walks volumes. They cover six peak hours (weekday and weekend, morning, midday and evening), so they are an exposure index and not daily totals. They are calibrated to NYC DOT counts from 2018 and 2019, while the crashes run to 2023.
