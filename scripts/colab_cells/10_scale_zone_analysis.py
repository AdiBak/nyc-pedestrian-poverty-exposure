# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Scale and zone effects on the poverty gradient.
# Question: how much does the poverty rate ratio depend on how the city is divided up?
#  - Scale effect: the same data aggregated to larger and larger zones.
#  - Zone effect: many random contiguous zonings of the same average size.
# Needs only crossing_sites_model_data.csv on Drive and the Census tract boundaries.
# No Milestone 1 or Milestone 5 cells are needed. Allow 2 to 4 minutes.
#
# Zones are built from the 2,100 or so tracts in the site table. Each zone sums crashes and crossing
# volume, and takes population weighted poverty, walking, transit and commercial shares.
# Two models are fit at every scale, residents only and residents plus crossing volume and street design.

# %% K1. Scale and zone effects
import os
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
import statsmodels.api as sm
import statsmodels.formula.api as smf
from google.colab import drive

warnings.filterwarnings('ignore')
drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
df = pd.read_csv(f'{DRIVE_DIR}/crossing_sites_model_data.csv', dtype={'GEOID': str})

df['w_x_vol'] = df['max_width'] * df['site_vol']
df['l_x_vol'] = df['max_lanes'] * df['site_vol']
df['s_x_vol'] = df['max_speed'] * df['site_vol']
t = (df.groupby('GEOID')
     .agg(harm=('harm_crashes', 'sum'), killed=('ped_killed', 'sum'), vol=('site_vol', 'sum'),
          wv=('w_x_vol', 'sum'), lv=('l_x_vol', 'sum'), sv=('s_x_vol', 'sum'),
          pop=('Total_Population', 'first'), pov=('Poverty_Rate_Percent', 'first'),
          walk=('Walk_Share', 'first'), transit=('Transit_Share', 'first'),
          comm=('Commercial_Share', 'first'), zip=('ZCTA_cluster', 'first'), county=('county', 'first'))
     .reset_index())
t = t[t['pop'] > 0].reset_index(drop=True)
print('tracts:', len(t), '| harm crashes:', int(t['harm'].sum()), '| deaths:', int(t['killed'].sum()))

# Tract adjacency (queen contiguity), within the same borough
TRACT_ZIP = '/content/ny_tracts2020.zip'
if not os.path.exists(TRACT_ZIP):
    url = 'https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_36_tract_500k.zip'
    with open(TRACT_ZIP, 'wb') as f:
        f.write(requests.get(url, timeout=120).content)
g = gpd.read_file(TRACT_ZIP)
g = g[g['GEOID'].isin(t['GEOID'])][['GEOID', 'geometry']].reset_index(drop=True)
pairs = gpd.sjoin(g, g, predicate='intersects')
pairs = pairs[pairs['GEOID_left'] != pairs['GEOID_right']]
county_of = dict(zip(t['GEOID'], t['county']))
pairs = pairs[pairs['GEOID_left'].map(county_of) == pairs['GEOID_right'].map(county_of)]
nbrs = pairs.groupby('GEOID_left')['GEOID_right'].apply(list).to_dict()
ids = list(t['GEOID'])


def random_zones(k, rng):
    zone_of = {}
    zid = 0
    for seed in rng.permutation(ids):
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
    return t['GEOID'].map(zone_of).values


def aggregate(zone_ids):
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


FORMS = {
    'residents only': 'pov + log_pop + walk_z + transit_z + comm_z + C(county)',
    'residents + volume + design': 'pov + log_pop + log_vol + width10 + lanes + speed5 + walk_z + transit_z + comm_z + C(county)',
}


def fit_rr(zdf, y, form, groups=None):
    kw = {'cov_type': 'HC1'} if groups is None else {'cov_type': 'cluster', 'cov_kwds': {'groups': groups}}
    res = smf.glm(f'{y} ~ {form}', data=zdf, family=sm.families.Poisson()).fit(**kw)
    lo, hi = res.conf_int().loc['pov']
    return np.exp(10 * res.params['pov']), np.exp(10 * lo), np.exp(10 * hi)


def show(label, rrs):
    r, lo, hi = rrs
    return f'{label}: {r:.2f} ({lo:.2f} to {hi:.2f})'


tract_z = aggregate(t['GEOID'].values)
zip_z = aggregate(t['zip'].values)
zip_groups = pd.factorize(t['zip'])[0]
print(f'ZIP area zones: {len(zip_z)}')

rng = np.random.default_rng(11)
SIZES = [2, 4, 8, 16, 32]
R = 100
for y, name in [('harm', 'Pedestrian harm crashes'), ('killed', 'Pedestrian deaths')]:
    print(f'\n=== {name}: poverty rate ratio per +10 points ===')
    for fname, form in FORMS.items():
        print(f'\n  Model: {fname}')
        print('   ', show(f'tracts ({len(tract_z)} zones, ZIP clustered)', fit_rr(tract_z, y, form, zip_groups)))
        print('   ', show(f'ZIP areas ({len(zip_z)} zones)', fit_rr(zip_z, y, form)))
    # Random zonings, same set of zonings for both models
print('\n=== Random contiguous zonings, point estimates across', R, 'draws ===')
store = {}
for k in SIZES:
    zonings = [random_zones(k, rng) for _ in range(R)]
    store[k] = zonings
    zsizes = [len(np.unique(z)) for z in zonings]
    print(f'\n  target {k} tracts per zone: about {np.mean(zsizes):.0f} zones per draw, mean size {len(t) / np.mean(zsizes):.1f} tracts')
    for y, name in [('harm', 'harm crashes'), ('killed', 'deaths')]:
        for fname, form in FORMS.items():
            vals = []
            for z in zonings:
                try:
                    vals.append(fit_rr(aggregate(z), y, form)[0])
                except Exception:
                    continue
            vals = np.array(vals)
            lo, med, hi = np.percentile(vals, [2.5, 50, 97.5])
            print(f'    {name}, {fname}: median {med:.2f}, 95% of zonings between {lo:.2f} and {hi:.2f}')
print('\nReference from earlier runs, site level model D: harm crashes 1.16, deaths 1.29')
