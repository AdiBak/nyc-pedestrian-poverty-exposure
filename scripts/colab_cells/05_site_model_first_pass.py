# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Crossing site level model of pedestrian harm crashes, 2019 to 2023.
# Run in the TDSP Research Sandbox after the Milestone 1 and Milestone 5 cells.
# Uses these names from your session: crashes, tracts, tract_table, HEADLINE_YEARS, smf, gpd.
#
# Design
#  1. Infer crosswalks as pedestrian segments that cross a street centerline (as before).
#  2. Group crosswalk midpoints within 25 m of each other into sites, which are mostly intersections.
#     Crash coordinates sit at the intersection center, so a site is the right unit, not one crosswalk.
#  3. Count pedestrian harm crashes within 30 m of each site's center.
#  4. Model counts with site crossing volume, street width, lanes, speed and tract poverty.

# %% F1. Build sites, assign crashes, fit the models
import os
import zipfile
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm
from sklearn.cluster import DBSCAN
from google.colab import drive

warnings.filterwarnings('ignore')
drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
MEMBER = 'NYC_pednetwork_estimates_counts_2018-2019.geojson'
LOCAL = f'/content/{MEMBER}'
COUNTY_NAMES = {'005': 'Bronx', '047': 'Brooklyn', '061': 'Manhattan', '081': 'Queens', '085': 'Staten Island'}
SITE_EPS_M = 25      # crosswalks closer than this form one site
CRASH_RADIUS_M = 30  # a crash belongs to the nearest site within this distance

if not os.path.exists(LOCAL):
    with zipfile.ZipFile(f'{DRIVE_DIR}/supp_data_1_network.zip') as z:
        with z.open(MEMBER) as src, open(LOCAL, 'wb') as dst:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)

# Street centerlines, ordinary streets only
cl = gpd.read_file(f'{DRIVE_DIR}/centerline_inkn-q76z.geojson').to_crs(6538)
for c in ['rw_type', 'status', 'streetwidth', 'posted_speed', 'number_travel_lanes']:
    cl[c] = pd.to_numeric(cl[c], errors='coerce')
road = cl[(cl['status'] == 2) & (cl['rw_type'] == 1) & (cl['trafdir'] != 'NV')]
road = road[['streetwidth', 'posted_speed', 'number_travel_lanes', 'geometry']]

# Pedestrian volumes and crosswalk inference
WKDY = ['predwkdyAM', 'predwkdyMD', 'predwkdyPM']
WKND = ['predwkndAM', 'predwkndMD', 'predwkndPM']
seg = gpd.read_file(LOCAL, engine='pyogrio', columns=WKDY + WKND).to_crs(6538)
seg[WKDY + WKND] = seg[WKDY + WKND].fillna(0).clip(lower=0)
seg['vol_peak'] = seg[WKDY + WKND].mean(axis=1)
seg['seg_id'] = np.arange(len(seg))

hit = gpd.sjoin(seg[['seg_id', 'geometry']], road, how='inner', predicate='intersects')
widest = (hit.sort_values('streetwidth', ascending=False, na_position='last')
          .drop_duplicates('seg_id')
          [['seg_id', 'streetwidth', 'posted_speed', 'number_travel_lanes']])
cross = seg.merge(widest, on='seg_id', how='inner')
print('crosswalk segments:', len(cross))

# Group crosswalks into sites
mid = cross.geometry.interpolate(0.5, normalized=True)
xy = np.c_[mid.x.values, mid.y.values]
cross['site'] = DBSCAN(eps=SITE_EPS_M, min_samples=1).fit_predict(xy)
cross['x'], cross['y'] = xy[:, 0], xy[:, 1]

sites = (cross.groupby('site')
         .agg(n_cross=('seg_id', 'size'), site_vol=('vol_peak', 'sum'),
              max_width=('streetwidth', 'max'), max_speed=('posted_speed', 'max'),
              max_lanes=('number_travel_lanes', 'max'), x=('x', 'mean'), y=('y', 'mean'))
         .reset_index())
site_pts = gpd.GeoDataFrame(sites[['site']], geometry=gpd.points_from_xy(sites['x'], sites['y']), crs=6538)
print('sites:', len(sites), '| median crosswalks per site:', int(sites['n_cross'].median()))

# Tract attributes from the Milestone 5 table
tm0 = tract_table(HEADLINE_YEARS, 'local')
tr = tracts.to_crs(6538)[['GEOID', 'geometry']]
js = gpd.sjoin(site_pts, tr, how='left', predicate='within')
js = js[~js.index.duplicated(keep='first')]
sites['GEOID'] = js['GEOID'].values
cols = ['GEOID', 'Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share', 'Commercial_Share',
        'ZCTA_cluster', 'Total_Population']
sites = sites.merge(tm0[cols], on='GEOID', how='inner')
sites['county'] = sites['GEOID'].str[2:5].map(COUNTY_NAMES)
print('sites in Milestone 5 tracts:', len(sites))

# Pedestrian harm crashes, 2019 to 2023, highway crashes dropped
c = crashes[crashes['YEAR'].isin(HEADLINE_YEARS) & ~crashes['is_highway']].copy()
c['ped_inj'] = c['NUMBER OF PEDESTRIANS INJURED'].fillna(0)
c['ped_kill'] = c['NUMBER OF PEDESTRIANS KILLED'].fillna(0)
c = c[(c['ped_inj'] + c['ped_kill']) > 0]
c = c[c['LATITUDE'].between(40.4, 41.0) & c['LONGITUDE'].between(-74.3, -73.6)]
cp = gpd.GeoDataFrame(c[['ped_inj', 'ped_kill']].reset_index(drop=True),
                      geometry=gpd.points_from_xy(c['LONGITUDE'], c['LATITUDE']), crs=4326).to_crs(6538)
print('pedestrian harm crashes with coordinates:', len(cp))


def assign(radius):
    j = gpd.sjoin_nearest(cp, site_pts, how='left', max_distance=radius)
    j = j[~j.index.duplicated(keep='first')]
    ok = j['site'].notna()
    agg = (j[ok].groupby('site')
           .agg(harm_crashes=('site', 'size'), ped_injured=('ped_inj', 'sum'), ped_killed=('ped_kill', 'sum')))
    return agg, ok.mean()


def build(radius):
    agg, share = assign(radius)
    d = sites.merge(agg, left_on='site', right_index=True, how='left')
    d[['harm_crashes', 'ped_injured', 'ped_killed']] = d[['harm_crashes', 'ped_injured', 'ped_killed']].fillna(0)
    d['log_vol'] = np.log(d['site_vol'].clip(lower=1))
    d['width10'] = d['max_width'] / 10
    d['speed5'] = d['max_speed'] / 5
    d['lanes'] = d['max_lanes']
    d = d.dropna(subset=['log_vol', 'width10', 'speed5', 'lanes', 'Poverty_Rate_Percent', 'Walk_Share',
                         'Transit_Share', 'Commercial_Share', 'ZCTA_cluster'])
    return d, share


def fit(d, terms):
    rhs = ' + '.join(['Poverty_Rate_Percent'] + terms)
    groups = pd.factorize(d['ZCTA_cluster'])[0]
    try:
        model = smf.negativebinomial(f'harm_crashes ~ {rhs}', data=d)
        return model.fit(disp=0, maxiter=300, cov_type='cluster', cov_kwds={'groups': groups}), 'NB'
    except Exception:
        model = smf.glm(f'harm_crashes ~ {rhs}', data=d, family=sm.families.Poisson())
        return model.fit(cov_type='cluster', cov_kwds={'groups': groups}), 'Poisson'


def rr10(res):
    lo, hi = res.conf_int().loc['Poverty_Rate_Percent']
    return f"{np.exp(10 * res.params['Poverty_Rate_Percent']):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})"


d, share = build(CRASH_RADIUS_M)
print(f'\nShare of harm crashes within {CRASH_RADIUS_M} m of a site: {share:.1%}')
print(f'sites in the model: {len(d)} | sites with at least one harm crash: {(d["harm_crashes"] > 0).mean():.1%}'
      f' | mean crashes per site: {d["harm_crashes"].mean():.2f}')

design = ['log_vol', 'width10', 'lanes', 'speed5']
more = design + ['n_cross', 'Walk_Share', 'Transit_Share', 'Commercial_Share']
specs = [('A  crossing volume only', ['log_vol']),
         ('B  + street width, lanes, speed', design),
         ('C  + crosswalks per site and tract controls', more),
         ('D  + borough effects', more + ['C(county)'])]

rows, fits = [], {}
for label, terms in specs:
    res, kind = fit(d, terms)
    fits[label] = res
    rows.append({'model': label, 'estimator': kind, 'poverty_RR_per_10': rr10(res),
                 'volume_elasticity': (f"{res.params['log_vol']:.2f}" if 'log_vol' in res.params else '')})
print('\nPoverty rate ratio per +10 points, 95% interval, clustered by ZIP area')
print(pd.DataFrame(rows).to_string(index=False))

full = fits[specs[-1][0]]
ci = full.conf_int()
tab = pd.DataFrame({'coef': full.params, 'lo': ci[0], 'hi': ci[1], 'p': full.pvalues}).round(3)
print('\nFull model coefficients. Units are log counts per unit of each variable.')
print('width10 is per 10 feet, speed5 per 5 mph, lanes per travel lane, Poverty_Rate_Percent per point.')
print(tab.to_string())

print('\nSensitivity to the crash assignment radius, full model')
for radius in [20, 30, 50]:
    dr, sh = build(radius)
    res, kind = fit(dr, more + ['C(county)'])
    print(f'  {radius} m: {sh:.1%} of crashes assigned, poverty RR per +10 = {rr10(res)} ({kind})')

print('\nTen sites with the most harm crashes')
show = ['site', 'county', 'n_cross', 'site_vol', 'max_width', 'max_lanes', 'max_speed', 'harm_crashes', 'Poverty_Rate_Percent']
print(d.sort_values('harm_crashes', ascending=False).head(10)[show].round(1).to_string(index=False))

d.to_csv(f'{DRIVE_DIR}/crossing_sites_model_data.csv', index=False)
print('\nsaved to', f'{DRIVE_DIR}/crossing_sites_model_data.csv')
