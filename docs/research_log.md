# Research log: poverty, exposure and pedestrian harm in New York City

Last updated 27 October 2026. This file records design decisions, numbers and open items so the paper can be built from it.

## Question and framing

Does neighborhood poverty relate to pedestrian harm after accounting for how many people walk and for street design? The paper reports two disparities.
- **Total gap.** How much more pedestrian harm poorer neighborhoods carry (models A and B).
- **Residual gap.** What remains after measured exposure, street design and tract context (models C and D). Transit and walking shares may sit on the causal path, so the residual gap answers a different question from the total gap.

## Data

| Source | Use | Notes |
|---|---|---|
| NYC Motor Vehicle Collisions, Crashes | Outcomes, 2019 to 2023 headline window | Missing ZIPs recovered from coordinates. Highway-flagged crashes dropped. |
| ACS 2019 to 2023 5-year (S1701, S0801) | Poverty, population, commuting | Tract level. |
| NYC PLUTO | Commercial share of floor area | Current release. |
| NYC Walks, Sevtsuk et al., Nature Cities (check the final citation year) | Modeled peak-hour pedestrian volumes, 315,577 segments | Calibrated to NYC DOT counts from 2018 and 2019. Metadata gives a preferred citation but no license. Do not redistribute the file. Consider writing to the contact in the metadata. |
| NYC Open Data, Centerline (id inkn-q76z) | Street width, lanes, posted speed, road type | The data.gov record lists no license information. Cite it. |
| Census 2020 cartographic tract boundaries | Tract assignment | |

NYC Walks volumes are for six peak hours (weekday and weekend, morning, midday, evening). They are an exposure index, not daily totals, and they date from 2018 and 2019 while crashes run to 2023.

## Method

1. Crosswalks are inferred as pedestrian segments that cross a centerline of an ordinary street (rw_type 1, active, not non-vehicular). 110,603 segments, 35 percent of all. Median length 16.6 m against 64.6 m for the rest.
2. Crosswalk midpoints within 25 m form sites, mostly intersections. 41,937 sites, median three crosswalks per site.
3. Pedestrian harm crashes (any pedestrian injured or killed) within 30 m of a site center are assigned to the site. About 82 to 84 percent of crashes are assigned.
4. Site covariates are summed crossing volume, widest street, most travel lanes and highest posted speed among streets crossed, and crosswalks per site. Tract covariates are poverty rate, walking share, transit share and commercial share.
5. Primary estimator is Poisson regression with cluster robust standard errors by ZIP area. Negative binomial GLM with a moment-based alpha (about 0.7 to 1.0) is the cross-check. Original negative binomial MLE output was discarded because of optimizer failure.
6. Primary specification is model D, with 38,477 sites.
   `harm crashes ~ poverty + log volume + width/10 + lanes + speed/5 + crosswalks (z) + walk share (z) + transit share (z) + commercial share (z) + borough`

## Results

### Tract level, poverty rate ratio per +10 points (injuries, deaths)

| Model | Injuries | Deaths |
|---|---|---|
| 1 Residents as exposure, with controls | 1.05 (1.02 to 1.08) | 1.02 (0.92 to 1.12) |
| 2 Residents as exposure, no controls | 1.12 (1.08 to 1.17) | 1.00 (0.92 to 1.09) |
| 3 Crossing volume as exposure, with controls | 1.21 (1.16 to 1.25) | 1.17 (1.06 to 1.28) |
| 4 Crossing volume as exposure, no controls | 1.34 (1.28 to 1.39) | 1.19 (1.10 to 1.30) |
| 5 Both as covariates, with controls | 1.11 (1.08 to 1.15) | 1.08 (0.99 to 1.18) |
| 6 Same as 5, plus borough | 1.11 (1.08 to 1.15) | 1.11 (1.01 to 1.22) |
| 7 Same as 5, Staten Island excluded | 1.12 (1.08 to 1.15) | 1.07 (0.98 to 1.18) |

Tract elasticities in model 5 are 0.46 for population and 0.41 for crossing volume (injuries). Models 3 and 4 assume risk proportional to volume, which the data reject, so they are not used.

### Site level, harm crashes, poverty rate ratio per +10 points

| Model | Poisson, robust | Negative binomial GLM |
|---|---|---|
| A Volume only | 1.30 (1.26 to 1.35) | 1.35 (1.30 to 1.41) |
| B + street design | 1.28 (1.23 to 1.32) | 1.33 (1.27 to 1.39) |
| C + tract controls | 1.15 (1.11 to 1.18) | 1.15 (1.11 to 1.19) |
| D + borough (primary) | 1.16 (1.12 to 1.20) | 1.17 (1.12 to 1.21) |

Model D coefficients as rate ratios. Volume elasticity 0.79. Width +10 ft 1.26 (1.21 to 1.31). Travel lane +1 1.09 (1.04 to 1.15). Posted speed +5 mph 1.24 (1.08 to 1.41), but speed barely varies. Per SD, transit share 1.40 (1.34 to 1.46), walking share 1.11, commercial share 0.93, crosswalks per site 0.86. Brooklyn 1.41 and Queens 1.37 relative to the Bronx.

Street design absorbs about 8 percent of the log poverty gap. The tract controls absorb about half.

### Robustness of the site level poverty ratio

| Check | Result |
|---|---|
| Assignment radius 20, 30, 50 m | 1.17, 1.16, 1.16 |
| Drop top 1 percent of sites | 1.13 (1.10 to 1.17) |
| Outcome pedestrians injured | 1.16 (1.12 to 1.20) |
| Site grouping 15, 25, 40 m | 1.14, 1.16, 1.16 |
| 2019 to 2021, 2022 to 2023 | 1.16, 1.16 |
| By year 2019, 2020, 2021, 2022, 2023 | 1.12, 1.19, 1.19, 1.17, 1.16 |
| Without Bronx, Brooklyn, Manhattan, Queens, Staten Island | 1.18, 1.19, 1.13, 1.16, 1.16 |
| Measurement error in volume, reliability 0.95 to 0.7 (SIMEX) | 1.17 to 1.18 linear, 1.18 to 1.25 quadratic |
| Poverty by volume interaction | None (p = 0.50) |
| Poverty by street width interaction | Slightly smaller gap on wider streets, about 3 percent per 10 ft |

### Pedestrian deaths at sites (secondary outcome, 411 deaths in the model, 469 among all coordinate-valid harm crashes)

Poverty rate ratio per +10 points, Poisson robust.

| Check | Result |
|---|---|
| Model A, B, C, D | 1.28 (1.18 to 1.39), 1.26 (1.16 to 1.37), 1.23 (1.11 to 1.36), 1.29 (1.17 to 1.42) |
| Negative binomial GLM, model D (alpha 1.09) | 1.28 (1.16 to 1.41) |
| Grouping 15 m, 40 m | 1.23 (1.12 to 1.35), 1.28 (1.16 to 1.41) |
| Crash radius 20 m, 50 m | 1.28 (1.16 to 1.42), 1.29 (1.18 to 1.42) |
| 2019 to 2021 (251 deaths), 2022 to 2023 (160 deaths) | 1.25 (1.13 to 1.39), 1.35 (1.16 to 1.56) |
| Without Bronx, Brooklyn, Manhattan, Queens, Staten Island | 1.29, 1.34, 1.25, 1.32, 1.27 |
| Cluster bootstrap, 500 resamples of 183 ZIP clusters | 1.29 (1.16 to 1.42) |

Frequency and severity split for model D. Harm crashes per site 1.16 (1.12 to 1.20). Deaths per harm crash 1.11 (1.00 to 1.23). Deaths per site 1.29 (1.17 to 1.42). About 60 percent of the death gradient comes from more harm crashes and about 40 percent from a higher chance that a crash is fatal. The severity interval touches 1, so call it suggestive.

About 12 percent of deaths (469 against 411) are not within 30 m of a site, probably mid-block, so the result describes deaths near intersections. Tract-level death models were null or borderline (1.02 to 1.11), so the paper must explain the difference. Two outcomes were examined, injuries and deaths.

### Plausibility of the modeled volumes

Median volume per crossing by borough is Bronx 159, Brooklyn 162, Manhattan 290, Queens 127, Staten Island 110. Rank correlation with density 0.60, with walking share 0.51, with poverty 0.20. Total crossing volume against poverty is negative (-0.16). The range across boroughs looks compressed relative to density and walking share, so volumes may be overstated in low-activity areas.

### Scale and zone effects (27 October 2026)

Zones aggregate site crashes and crossing volume from 2,183 tracts. Poisson, poverty rate ratio per +10 points. Residents only means log population plus walking, transit and commercial shares plus borough. The other model adds log crossing volume and volume-weighted street width, lanes and speed.

| Scale | Harm, residents only | Harm, with volume and design | Deaths, residents only | Deaths, with volume and design |
|---|---|---|---|---|
| Tracts (2,183) | 1.06 (1.02 to 1.10) | 1.13 (1.10 to 1.16) | 1.16 (1.05 to 1.29) | 1.23 (1.12 to 1.36) |
| ZIP areas (183) | 1.09 (1.01 to 1.16) | 1.20 (1.12 to 1.29) | 1.16 (1.00 to 1.36) | 1.25 (1.04 to 1.50) |
| Random zones of about 2 tracts, median | 1.06 | 1.15 | 1.15 | 1.24 |
| About 3, 5, 9 tracts, median | 1.06, 1.07, 1.07 | 1.16, 1.17, 1.18 | 1.12, 1.12, 1.10 | 1.21, 1.19, 1.19 |
| About 14 tracts, median | 1.07 | 1.18 | 1.07 | 1.15 |

Reading. Scale matters little. For harm crashes the exposure-adjusted ratio runs 1.13 to 1.20 across scales and 95 percent of random zonings at one size span about plus or minus 0.04. The residents-only estimate is stable at 1.06 to 1.09 but much smaller. So the exposure adjustment, not the geography, drives the estimate. For deaths the exposure-adjusted ratio drifts down from 1.29 (sites) and 1.23 (tracts) to about 1.15 for zones of 14 tracts, and the zone effect widens because few deaths fall in each zone. Do not frame scale sensitivity as the lead contribution. Report robustness to scale as a strength.

Specification note for deaths. The Milestone 5 tract model gave no gradient (1.02) with population as an exact offset and no borough effects. With population entering freely, borough effects and the assigned deaths, tract-level death ratios are 1.08 to 1.16 without volume and 1.23 with it. The earlier null was fragile to specification. The Milestone 5 write-up and the TDSP poster title ("but Deaths Do Not") describe the earlier analysis and need revising for any public version that uses this work.

## Limitations to state in the paper

- Association, not cause. No vehicle traffic volumes. Residual confounding is possible.
- NYC Walks volumes are modeled, peak-hour only, from 2018 and 2019, and calibrated mostly at commercial corridors.
- About 16 to 18 percent of harm crashes are not within 30 m of any site (mostly mid-block) and are excluded.
- Tract measures are ecological and say nothing about who is injured.
- Poverty comes from one ACS period. Transit and walking shares may be mediators.

## Files in Google Drive, MyDrive/TDSP/nyc_walks

supp_data_1_network.zip, supp_data_1_metadata.txt, centerline_inkn-q76z.geojson, tract_exposure_2018_2019_volumes.csv, tract_crossing_exposure_2018_2019_volumes.csv, exposure_model_results.csv, crossing_sites_model_data.csv, sites_eps25_r30_by_year.csv.

## Scripts

See the run order table in the README. Scripts 00 to 10 are the notebook cells that produced the numbers above, saved as files. Script 06 replaces the first-pass estimates in script 05.

## Open items

1. Done. Deaths battery and scale analysis (27 October 2026).
2. Done. Repository version 0.1 built (27 October 2026). Still to do, pin package versions after a clean run and test outside Colab.
3. Done. The original TDSP notebook now has an Additional Work section with these analyses. A backup copy of the earlier version is in Drive.
4. Consider vehicle traffic exposure (NYC DOT counts are sparse) and truck or bus route attributes.
5. Decide on writing to the NYC Walks authors about terms of use and the volume calibration in low-density areas.
6. Literature section against NYC Health Department 2017, Smart Growth America, the Columbia leading pedestrian interval study, the Minneapolis and Oregon equity studies, and the MAUP papers.
7. The Dropbox preprint of NYC Walks, if the student wants to attach it, to check methods details.
8. Milestone 6 leading pedestrian interval analysis stays exploratory. Milestone 7 prediction result stays a secondary section.
