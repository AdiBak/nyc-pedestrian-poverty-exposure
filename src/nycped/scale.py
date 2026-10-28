"""Scale and zone effects. Aggregate sites to tracts, ZIP areas and random contiguous zones."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

FORMS = {
    'residents only': 'pov + log_pop + walk_z + transit_z + comm_z + C(county)',
    'residents + volume + design': ('pov + log_pop + log_vol + width10 + lanes + speed5 + walk_z + transit_z'
                                    ' + comm_z + C(county)'),
}


def tract_frame(sites: pd.DataFrame) -> pd.DataFrame:
    """One row per tract with crashes, crossing volume and volume weighted street design."""
    d = sites.copy()
    d['w_x_vol'] = d['max_width'] * d['site_vol']
    d['l_x_vol'] = d['max_lanes'] * d['site_vol']
    d['s_x_vol'] = d['max_speed'] * d['site_vol']
    t = (d.groupby('GEOID')
         .agg(harm=('harm', 'sum'), killed=('killed', 'sum'), vol=('site_vol', 'sum'),
              wv=('w_x_vol', 'sum'), lv=('l_x_vol', 'sum'), sv=('s_x_vol', 'sum'),
              pop=('Total_Population', 'first'), pov=('Poverty_Rate_Percent', 'first'),
              walk=('Walk_Share', 'first'), transit=('Transit_Share', 'first'),
              comm=('Commercial_Share', 'first'), zip=('ZCTA_cluster', 'first'), county=('county', 'first'))
         .reset_index())
    return t[t['pop'] > 0].reset_index(drop=True)


def adjacency(tracts: gpd.GeoDataFrame, ids, county_of: dict) -> dict:
    """Queen contiguity between tracts in the same borough."""
    g = tracts[tracts['GEOID'].isin(set(ids))][['GEOID', 'geometry']].reset_index(drop=True)
    pairs = gpd.sjoin(g, g, predicate='intersects')
    pairs = pairs[pairs['GEOID_left'] != pairs['GEOID_right']]
    same = pairs['GEOID_left'].map(county_of) == pairs['GEOID_right'].map(county_of)
    return pairs[same].groupby('GEOID_left')['GEOID_right'].apply(list).to_dict()


def random_zones(ids, nbrs: dict, k: int, rng) -> dict:
    """Grow random contiguous zones of up to k tracts. Returns a dict from tract id to zone number."""
    zone_of, zid = {}, 0
    for seed in rng.permutation(list(ids)):
        if seed in zone_of:
            continue
        zone_of[seed] = zid
        size = 1
        frontier = [n for n in nbrs.get(seed, []) if n not in zone_of]
        while size < k and frontier:
            nxt = frontier.pop(int(rng.integers(len(frontier))))
            if nxt in zone_of:
                continue
            zone_of[nxt] = zid
            size += 1
            frontier += [n for n in nbrs.get(nxt, []) if n not in zone_of]
        zid += 1
    return zone_of


def aggregate(t: pd.DataFrame, zone_ids) -> pd.DataFrame:
    z = t.assign(zone=zone_ids)
    for c in ['pov', 'walk', 'transit', 'comm']:
        z[c + '_p'] = z[c] * z['pop']
    grp = z.groupby('zone')
    out = grp[['harm', 'killed', 'vol', 'wv', 'lv', 'sv', 'pop', 'pov_p', 'walk_p', 'transit_p', 'comm_p']].sum()
    for c in ['pov', 'walk', 'transit', 'comm']:
        out[c] = out[c + '_p'] / out['pop']
    out['width10'] = out['wv'] / out['vol'] / 10
    out['lanes'] = out['lv'] / out['vol']
    out['speed5'] = out['sv'] / out['vol'] / 5
    out['log_pop'] = np.log(out['pop'])
    out['log_vol'] = np.log(out['vol'].clip(lower=1))
    for c in ['walk', 'transit', 'comm']:
        out[c + '_z'] = (out[c] - out[c].mean()) / out[c].std()
    idx = z.groupby('zone')['pop'].idxmax()
    out['county'] = z.loc[idx.values, 'county'].values
    return out.reset_index()


def fit_rr(zdf: pd.DataFrame, y: str, form: str, groups=None):
    kw = {'cov_type': 'HC1'} if groups is None else {'cov_type': 'cluster', 'cov_kwds': {'groups': groups}}
    res = smf.glm(f'{y} ~ {form}', data=zdf, family=sm.families.Poisson()).fit(**kw)
    lo, hi = res.conf_int().loc['pov']
    return float(np.exp(10 * res.params['pov'])), float(np.exp(10 * lo)), float(np.exp(10 * hi))


def real_scales(t: pd.DataFrame) -> pd.DataFrame:
    """Tracts and ZIP areas, for both outcomes and both models."""
    rows = []
    tract_z = aggregate(t, t['GEOID'].values)
    zip_z = aggregate(t, t['zip'].values)
    zip_groups = pd.factorize(t['zip'])[0]
    for y in ['harm', 'killed']:
        for name, form in FORMS.items():
            for label, zdf, groups in [('tracts', tract_z, zip_groups), ('ZIP areas', zip_z, None)]:
                rr, lo, hi = fit_rr(zdf, y, form, groups)
                rows.append({'outcome': y, 'model': name, 'scale': label, 'zones': len(zdf),
                             'rr': rr, 'lo': lo, 'hi': hi})
    return pd.DataFrame(rows)


def random_zonings(t: pd.DataFrame, nbrs: dict, sizes=(2, 4, 8, 16, 32), n_draws: int = 100,
                   seed: int = 11) -> pd.DataFrame:
    """Median and 95 percent range of the poverty ratio across random zonings at each size."""
    rng = np.random.default_rng(seed)
    ids = list(t['GEOID'])
    rows = []
    for k in sizes:
        zonings = [t['GEOID'].map(random_zones(ids, nbrs, k, rng)).values for _ in range(n_draws)]
        mean_zones = float(np.mean([len(np.unique(z)) for z in zonings]))
        for y in ['harm', 'killed']:
            for name, form in FORMS.items():
                vals = []
                for z in zonings:
                    try:
                        vals.append(fit_rr(aggregate(t, z), y, form)[0])
                    except Exception:
                        continue
                lo, med, hi = np.percentile(vals, [2.5, 50, 97.5])
                rows.append({'target_tracts': k, 'zones': round(mean_zones), 'outcome': y, 'model': name,
                             'median': float(med), 'lo95': float(lo), 'hi95': float(hi)})
    return pd.DataFrame(rows)
