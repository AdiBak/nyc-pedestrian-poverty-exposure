# Preprints.org submission metadata

**Title**

Exposure-Adjusted Pedestrian Harm Is 16 Percent Higher per 10 Percentage Points of Neighborhood Poverty in New York City

**Author**

Aditya Bakshi, Cohere Labs Community, bakshia2@uci.edu (the address attached to the ORCID account, to be changed to a personal address through Preprints.org support)

**Abstract**

Pedestrian injury and fatality rates are frequently reported to be elevated in lower-income neighborhoods, but population-based rates confound infrastructure hazards with variations in pedestrian exposure. We integrate modeled pedestrian volumes for New York City with street centerline geometry and five years of geocoded police-reported collision records (2019–2023). Crosswalk segments are identified and clustered into 41,937 discrete crossing sites, predominantly intersections, to which collisions are spatially assigned. Across 38,477 sites located in census tracts with complete covariate data, pedestrian injury and fatality collisions increase by 16% per 10-percentage-point increase in the tract poverty rate (rate ratio [RR] 1.16, 95% CI [1.12, 1.20]), conditioning on pedestrian crossing volume, roadway width, lane counts, posted speed limits, tract-level commuting mode shares, land use, and borough fixed effects. A model that holds only pedestrian volume fixed yields an RR of 1.30 (95% CI [1.26, 1.35]). This gradient is robust to alternative count estimators, site grouping distances, collision assignment radii, temporal partitions, borough exclusions, clustered covariance structures, and a designated truck route control. The estimate attenuates to 1.10 with ZIP-code fixed effects and increases to 1.19–1.22 after correcting for American Community Survey sampling error in poverty estimates. Pedestrian fatalities show a similar, somewhat steeper gradient (RR 1.29, 95% CI [1.17, 1.42]), arising from both higher collision frequency and a higher chance that a collision is fatal, although the second component is imprecise. Conventional models relying on residential population yield attenuated ratios of 1.06–1.09, indicating that the observed disparity is uncovered by exposure adjustment rather than by spatial aggregation. These estimates reflect observational associations in the absence of vehicle volume counts. An open-source pipeline is provided to reproduce all data processing, models, and figures from public records.

**Keywords**

pedestrian safety; traffic crashes; neighborhood poverty; pedestrian exposure; New York City; Poisson regression

**Manuscript files**

`preprints_org_source.zip` holds `main.tex`, `main.bbl`, `references.bib` and `generated/` (figures and tables). The main file is `main.tex`.

**Conflicts of interest**

The author declares no conflicts of interest.

**Graphical abstract**

`graphical_abstract.png` (the study sites map, 2100 by 1050 pixels).

**Related websites**

- https://github.com/AdiBak/nyc-pedestrian-poverty-exposure
- https://doi.org/10.5281/zenodo.23754868

**Manuscript contents the screeners look for**

The first page carries the title, author, affiliation, corresponding author email, abstract, and keywords. The manuscript has a Conflicts of Interest section before the references and documents AI use in Methods (Use of generative AI).

**Funding**

Confirm before submitting. If there was none, enter "This research received no external funding."

**Ethics statement**

Not applicable. The study uses public, aggregated crash records, modeled pedestrian volumes, and Census data. It involves no human participants and no identifiable individuals.

**Data and code availability**

Code: https://github.com/AdiBak/nyc-pedestrian-poverty-exposure (archived at https://doi.org/10.5281/zenodo.23754868). The paper's "Code and data availability" section describes the public sources.

**Generative AI**

The paper discloses AI use in its "AI Use" section. Read the Preprints.org policy on AI-assisted writing before submitting and match its wording.
