# arXiv submission metadata

Fill these into the arXiv submission form. The source bundle for upload is built from `paper/main.tex`, `paper/main.bbl` and `paper/generated/` (figures and tables only).

**Title**

Exposure-Adjusted Pedestrian Harm Is 16 Percent Higher per 10 Percentage Points of Neighborhood Poverty in New York City

**Authors**

Aditya Bakshi (affiliation: Cohere Labs Community)

**Abstract** (plain text, 1911 characters, shortened from the paper's abstract to fit arXiv's 1,920 character limit)

Pedestrian injury and fatality rates are often reported to be elevated in lower-income neighborhoods, but population-based rates confound infrastructure hazards with variations in pedestrian exposure. We integrate modeled pedestrian volumes for New York City with street centerline geometry and five years of police-reported collision records (2019–2023). We cluster crosswalks into 41,937 crossing sites, mostly intersections, and assign collisions to them. Across 38,477 sites located in census tracts with complete covariate data, pedestrian injury and fatality collisions increase by 16% per 10-percentage-point increase in the tract poverty rate (rate ratio [RR] 1.16, 95% CI [1.12, 1.20]), conditioning on pedestrian crossing volume, roadway width, lane counts, posted speed limits, tract-level commuting mode shares, land use, and borough fixed effects. A model that holds only pedestrian volume fixed yields an RR of 1.30 (95% CI [1.26, 1.35]). This gradient is robust to alternative count estimators, site grouping distances, collision assignment radii, temporal partitions, borough exclusions, clustered covariance structures, and a truck route control. The estimate attenuates to 1.10 with ZIP-code fixed effects and increases to 1.19–1.22 after correcting for American Community Survey sampling error in poverty estimates. Pedestrian fatalities show a similar, somewhat steeper gradient (RR 1.29, 95% CI [1.17, 1.42]), arising from both higher collision frequency and a higher chance that a collision is fatal, although the second part is imprecise. Models relying on residential population yield attenuated ratios of 1.06–1.09, indicating that the observed disparity is uncovered by exposure adjustment rather than by spatial aggregation. These estimates reflect observational associations in the absence of vehicle volume counts. An open-source pipeline reproduces all results from public records.

**Primary category**

stat.AP (Statistics, Applications)

**Cross-lists**

physics.soc-ph (Physics and Society), cs.CY (Computers and Society)

**Comments**

8 pages, 4 figures, 3 tables. Code and reproduction guide: https://github.com/AdiBak/nyc-pedestrian-poverty-exposure (archived at https://doi.org/10.5281/zenodo.23754868)

**Journal reference, DOI, report number, MSC and ACM classes**

Leave blank.

**License**

CC BY 4.0 is a common choice for preprints. The arXiv default (non-exclusive license to distribute) also works.

**Other form items**

- Generative AI use is disclosed in the paper under "AI Use". Check the arXiv policy page on the day of submission for any form field that asks about it.
- A first submission in a category may need an endorsement. The arXiv form shows whether one is required once the category is chosen.
- Upload the source bundle (`main.tex`, `main.bbl`, `generated/`), not the PDF. Check that the preview PDF matches the local build before announcing.
