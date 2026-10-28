# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Robustness checks for the site level poverty estimate.
#  1. Site definition: group crosswalks within 15, 25 or 40 m.
#  2. Time: 2019 to 2021 versus 2022 to 2023, and each year, with the same 2018 and 2019 volumes.
#  3. Leave one borough out.
# Run in the TDSP Research Sandbox after the Milestone 1 and Milestone 5 cells.
# Uses these names from the session: crashes, tracts, tract_table, HEADLINE_YEARS.
# Allow several minutes. The first part rebuilds the crosswalks and reads a 275 MB file.

# %% I1. Robustness checks
import os
import zipfile
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.cluster import DBSCAN
from google.colab import drive

warnings.filterwarnings('ignore')
drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
MEMBER = 'NYC_pednetwork_estimates_counts_2018-2019.geojson'
LOCAL = f'/content/{MEMBER}'
COUNTY_NAMES = {'005': 'Bronx', '047': 'Brooklyn', '061': 'Manhattan', '081': 'Queens', '085': 'Staten Island'}
RADIUS_M = 30
YEARS = sorted(HEADLINE_YEARS)

if not os.path.exists(LOCAL):
    with zipfile.ZipFile(f'{DRIVE_DIR}/supp_data_1_network.zip') as z:
        with z.open(MEMBER) as src, open(LOCAL, 'wb') as dst:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)

# Crosswalks, built once
cl = gpd.read_file(f'{DRIVE_DIR}/centerline_inkn-q76z.geojson').to_crs(6538)
for c in ['rw_type', 'status', 'streetwidth', 'posted_speed', 'number_travel_lanes']:
    cl[c] = pd.to_numeric(cl[c], errors='coerce')
road = cl[(cl['status'] == 2) & (cl['rw_type'] == 1) & (cl['trafdir'] != 'NV')]
road = road[['streetwidth', 'posted_speed', 'number_travel_lanes', 'geometry']]

WKDY = ['predwkdyAM', 'predwkdyMD', 'predwkdyPM']
WKND = ['predwkndAM', 'predwkndMD', 'predwkndPM']
seg = gpd.read_file(LOCAL, engine='pyogrio', columns=WKDY + WKND).to_crs(6538)
seg[WKDY + WKND] = seg[WKDY + WKND].fillna(0).clip(lower=0)
seg['vol_peak'] = seg[WKDY + WKND].mean(axis=1)
seg['seg_id'] = np.arange(len(seg))
hit = gpd.sjoin(seg[['seg_id', 'geometry']], road, how='inner', predicate='intersects')
widest = (hit.sort_values('streetwidth', ascending=False, na_position='last')
          .drop_duplicates('seg_id')[['seg_id', 'streetwidth', 'posted_speed', 'number_travel_lanes']])
cross = seg.merge(widest, on='seg_id', how='inner')
mid = cross.geometry.interpolate(0.5, normalized=True)
xy = np.c_[mid.x.values, mid.y.values]
print('crosswalk segments:', len(cross))

# Tract attributes and crash points
tm0 = tract_table(HEADLINE_YEARS, 'local')
cols = ['GEOID', 'Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share', 'Commercial_Share', 'ZCTA_cluster']
tr = tracts.to_crs(6538)[['GEOID', 'geometry']]

c = crashes[crashes['YEAR'].isin(HEADLINE_YEARS) & ~crashes['is_highway']].copy()
c['ped_inj'] = c['NUMBER OF PEDESTRIANS INJURED'].fillna(0)
c['ped_kill'] = c['NUMBER OF PEDESTRIANS KILLED'].fillna(0)
c = c[(c['ped_inj'] + c['ped_kill']) > 0]
c = c[c['LATITUDE'].between(40.4, 41.0) & c['LONGITUDE'].between(-74.3, -73.6)]
cp = gpd.GeoDataFrame(c[['ped_inj', 'ped_kill']].assign(year=c['YEAR'].values).reset_index(drop=True),
                      geometry=gpd.points_from_xy(c['LONGITUDE'], c['LATITUDE']), crs=4326).to_crs(6538)
print('pedestrian harm crashes:', len(cp))


def make_dataset(eps):
    lab = DBSCAN(eps=eps, min_samples=1).fit_predict(xy)
    cr = pd.DataFrame({'site': lab, 'x': xy[:, 0], 'y': xy[:, 1], 'vol_peak': cross['vol_peak'].values,
                       'w': cross['streetwidth'].values, 's': cross['posted_speed'].values,
                       'l': cross['number_travel_lanes'].values})
    s = (cr.groupby('site')
         .agg(n_cross=('vol_peak', 'size'), site_vol=('vol_peak', 'sum'), max_width=('w', 'max'),
              max_speed=('s', 'max'), max_lanes=('l', 'max'), x=('x', 'mean'), y=('y', 'mean'))
         .reset_index())
    pts = gpd.GeoDataFrame(s[['site']], geometry=gpd.points_from_xy(s['x'], s['y']), crs=6538)
    j = gpd.sjoin(pts, tr, how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')]
    s['GEOID'] = j['GEOID'].values
    s = s.merge(tm0[cols], on='GEOID', how='inner')
    s['county'] = s['GEOID'].str[2:5].map(COUNTY_NAMES)
    pts = pts[pts['site'].isin(s['site'])]

    nearest = gpd.sjoin_nearest(cp, pts[['site', 'geometry']], how='left', max_distance=RADIUS_M)
    nearest = nearest[~nearest.index.duplicated(keep='first')]
    ok = nearest[nearest['site'].notna()]
    tot = ok.groupby('site').agg(harm=('site', 'size'), killed=('ped_kill', 'sum'))
    byyr = ok.groupby(['site', 'year']).size().unstack(fill_value=0)
    byyr.columns = [f'y{int(k)}' for k in byyr.columns]
    d = s.merge(tot, left_on='site', right_index=True, how='left').merge(byyr, left_on='site', right_index=True, how='left')
    ycols = [f'y{y}' for y in YEARS]
    for k in ['harm', 'killed'] + [k for k in ycols if k in d.columns]:
        d[k] = d[k].fillna(0)
    for k in ycols:
        if k not in d.columns:
            d[k] = 0
    early = [f'y{y}' for y in YEARS if y <= 2021]
    late = [f'y{y}' for y in YEARS if y >= 2022]
    d['early'] = d[early].sum(axis=1)
    d['late'] = d[late].sum(axis=1)
    d['log_vol'] = np.log(d['site_vol'].clip(lower=1))
    d['width10'] = d['max_width'] / 10
    d['speed5'] = d['max_speed'] / 5
    d['lanes'] = d['max_lanes']
    d = d.dropna(subset=['log_vol', 'width10', 'speed5', 'lanes', 'Poverty_Rate_Percent', 'Walk_Share',
                         'Transit_Share', 'Commercial_Share', 'ZCTA_cluster']).copy()
    for k in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
        d[k + '_z'] = (d[k] - d[k].mean()) / d[k].std()
    return d, len(ok) / len(cp)


RHS = ('Poverty_Rate_Percent + log_vol + width10 + lanes + speed5 + n_cross_z + Walk_Share_z'
       ' + Transit_Share_z + Commercial_Share_z + C(county)')


def fit(d, y):
    groups = pd.factorize(d['ZCTA_cluster'])[0]
    return smf.glm(f'{y} ~ {RHS}', data=d, family=sm.families.Poisson()).fit(
        cov_type='cluster', cov_kwds={'groups': groups})


def rr(res):
    lo, hi = res.conf_int().loc['Poverty_Rate_Percent']
    return f"{np.exp(10 * res.params['Poverty_Rate_Percent']):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})"


# 1. Site definition
print('\n1. Site definition (30 m crash radius), model D')
datasets = {}
for eps in [15, 25, 40]:
    d, share = make_dataset(eps)
    datasets[eps] = d
    print(f'  grouping distance {eps} m: {len(d)} sites, {share:.1%} of crashes assigned, poverty RR per +10 = {rr(fit(d, "harm"))}')

# 2. Time
d = datasets[25]
print('\n2. Stability over time (same 2018 and 2019 volumes), 25 m sites')
for label, y in [('2019 to 2021', 'early'), ('2022 to 2023', 'late')] + [(str(yr), f'y{yr}') for yr in YEARS]:
    res = fit(d, y)
    print(f'  {label}: crashes = {int(d[y].sum())}, poverty RR per +10 = {rr(res)}, volume elasticity = {res.params["log_vol"]:.2f}')

# 3. Leave one borough out
print('\n3. Leave one borough out, 25 m sites')
for name in COUNTY_NAMES.values():
    sub = d[d['county'] != name].copy()
    print(f'  without {name}: {len(sub)} sites, poverty RR per +10 = {rr(fit(sub, "harm"))}')
