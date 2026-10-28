# Reviewer checks

Run on 28 October 2026 with the checks command of the nycped package, on the rebuilt site table (38,475 sites, Python 3.13). The primary estimate is the poverty rate ratio per 10 points of 1.16 (1.12 to 1.20), from Poisson regression with standard errors clustered by ZIP area.

## 1. Spatial dependence

| Check | Result |
|---|---|
| Moran I of model residuals, 8 nearest neighbors, 199 permutations, sites | 0.088 (permutation p = 0.005) |
| Moran I of residuals summed by tract | 0.198 (permutation p = 0.005) |
| Standard errors clustered by ZIP area (183 clusters, primary) | 1.16 (1.12 to 1.20) |
| Clustered by tract (2,183) | 1.16 (1.13 to 1.19) |
| Clustered by 1 km grid cell (822) | 1.16 (1.13 to 1.19) |
| Clustered by 2 km grid cell (247) | 1.16 (1.12 to 1.20) |
| Clustered by 4 km grid cell (81) | 1.16 (1.13 to 1.20) |
| Block bootstrap, 247 blocks of 2 km, 300 resamples | 1.16 (1.13 to 1.20) |
| ZIP area fixed effects, so only variation within a ZIP area | 1.10 (1.07 to 1.13) |

Reading. The residuals are positively spatially correlated, strongest at tract level, so something spatially structured is still missing from the model. The inference does not depend on it. The intervals barely move when the clustering is coarsened from ZIP areas to 4 km blocks, and the block bootstrap agrees. The within ZIP estimate of 1.10 is smaller than 1.16, so about a third of the log gap comes from differences between ZIP areas. The rest is a gradient among tracts in the same ZIP area, which regional confounding cannot explain.

The ZIP fixed effects model uses a lean estimator that eliminates the fixed effects analytically. It matches the dense statsmodels fit to six decimals in the point estimate and within 2 percent in the standard error on test data.

## 2. Truck routes as a partial stand-in for heavy vehicle traffic

The centerline file flags designated truck routes. A site counts as a truck route site if any street its crosswalks cross is one. This is a street class proxy, not a measure of vehicle volume. About 17.7 percent of sites qualify. Truck route streets are wider, with a median of 36 to 42 feet against 30 feet for other streets.

| Model | Sites | Poverty rate ratio |
|---|---|---|
| Primary (model D) | 38,475 | 1.16 (1.12 to 1.20) |
| Plus the truck route flag | 38,475 | 1.17 (1.13 to 1.20) |
| Sites on no truck route | 31,653 | 1.13 (1.09 to 1.18) |
| Sites on a truck route | 6,822 | 1.20 (1.16 to 1.25) |

Truck route sites carry 1.48 times the harm of other sites after the other controls. Adding the flag leaves the poverty ratio unchanged. The ratio is somewhat larger on truck routes. I did not use the snow priority codes in the centerline file, because their meaning could not be confirmed.

## 3. Sampling error in the ACS tract poverty rate

Pending. Run scripts/01_export_tract_poverty_moe.py in Colab, then run the checks command with the option --poverty-moe pointing at tract_poverty_moe.csv. The check adds noise at the tract level in proportion to the ACS margin of error, refits, and extrapolates back to zero error.

## Reproducibility note

Rebuilding the site table in Python 3.13 gave 38,475 sites in the model, and Colab gave 38,477. The two sites differ only in the zero crash fringe, probably because library versions break exact ties in the 25 meter grouping differently. The estimates agree to four decimals, 1.1611 against 1.1612. The verify command now allows a difference of five sites.
