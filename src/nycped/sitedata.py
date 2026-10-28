"""Assemble the site level modeling table."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_site_dataset(sites: pd.DataFrame, counts: pd.DataFrame, years) -> pd.DataFrame:
    """Merge crash counts onto sites, add model variables and drop sites with missing values."""
    d = sites.merge(counts, left_on='site', right_index=True, how='left')
    count_cols = ['harm', 'killed'] + [f'y{y}' for y in years] + [f'k{y}' for y in years]
    d[count_cols] = d[count_cols].fillna(0)
    d['y_early'] = d[[f'y{y}' for y in years if y <= 2021]].sum(axis=1)
    d['y_late'] = d[[f'y{y}' for y in years if y >= 2022]].sum(axis=1)
    d['k_early'] = d[[f'k{y}' for y in years if y <= 2021]].sum(axis=1)
    d['k_late'] = d[[f'k{y}' for y in years if y >= 2022]].sum(axis=1)
    d['log_vol'] = np.log(d['site_vol'].clip(lower=1))
    d['width10'] = d['max_width'] / 10
    d['speed5'] = d['max_speed'] / 5
    d['lanes'] = d['max_lanes']
    need = ['log_vol', 'width10', 'speed5', 'lanes', 'Poverty_Rate_Percent', 'Walk_Share',
            'Transit_Share', 'Commercial_Share', 'ZCTA_cluster']
    d = d.dropna(subset=need).copy()
    for c in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
        d[c + '_z'] = (d[c] - d[c].mean()) / d[c].std()
    return d
