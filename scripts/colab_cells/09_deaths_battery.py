# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Robustness battery for the pedestrian death gradient at crossing sites.
# Run in the TDSP Research Sandbox after the Milestone 1 and Milestone 5 cells.
# Uses these names from the session: crashes, tracts, tract_table, HEADLINE_YEARS.
# Allow 8 to 10 minutes. The first part rebuilds the crosswalks and sites.
#
# Checks
#  1. Model progression A to D for deaths, Poisson robust and negative binomial GLM.
#  2. Site grouping distance 15, 25, 40 m and crash radius 20, 30, 50 m.
#  3. Time: 2019 to 2021 versus 2022 to 2023, with death counts.
#  4. Leave one borough out.
#  5. Cluster bootstrap interval for the death ratio in model D.
#  6. Frequency versus severity: harm crashes per site, then deaths per harm crash.

# %% J1. Deaths battery
import os
import zipfile
import warnings
import numpy as np
import pandas as pd
import patsy
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
print('pedestrian harm crashes:', len(cp), '| deaths among them:', int(cp['ped_kill'].sum()))


def make_dataset(eps, radius):
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

    near = gpd.sjoin_nearest(cp, pts[['site', 'geometry']], how='left', max_distance=radius)
    near = near[~near.index.duplicated(keep='first')]
    ok = near[near['site'].notna()]
    tot = ok.groupby('site').agg(harm=('site', 'size'), killed=('ped_kill', 'sum'))
    hy = ok.groupby(['site', 'year']).size().unstack(fill_value=0)
    hy.columns = [f'y{int(k)}' for k in hy.columns]
    ky = ok.groupby(['site', 'year'])['ped_kill'].sum().unstack(fill_value=0)
    ky.columns = [f'k{int(k)}' for k in ky.columns]
    d = (s.merge(tot, left_on='site', right_index=True, how='left')
          .merge(hy, left_on='site', right_index=True, how='left')
          .merge(ky, left_on='site', right_index=True, how='left'))
    for yr in YEARS:
        for pref in ['y', 'k']:
            if f'{pref}{yr}' not in d.columns:
                d[f'{pref}{yr}'] = 0
    allc = ['harm', 'killed'] + [f'y{yr}' for yr in YEARS] + [f'k{yr}' for yr in YEARS]
    d[allc] = d[allc].fillna(0)
    d['k_early'] = d[[f'k{yr}' for yr in YEARS if yr <= 2021]].sum(axis=1)
    d['k_late'] = d[[f'k{yr}' for yr in YEARS if yr >= 2022]].sum(axis=1)
    d['log_vol'] = np.log(d['site_vol'].clip(lower=1))
    d['width10'] = d['max_width'] / 10
    d['speed5'] = d['max_speed'] / 5
    d['lanes'] = d['max_lanes']
    d = d.dropna(subset=['log_vol', 'width10', 'speed5', 'lanes', 'Poverty_Rate_Percent', 'Walk_Share',
                         'Transit_Share', 'Commercial_Share', 'ZCTA_cluster']).copy()
    for k in ['Walk_Share', 'Transit_Share', 'Commercial_Share', 'n_cross']:
        d[k + '_z'] = (d[k] - d[k].mean()) / d[k].std()
    return d


DESIGN = 'log_vol + width10 + lanes + speed5'
CTRL = ' + n_cross_z + Walk_Share_z + Transit_Share_z + Commercial_Share_z'
SPECS = {'A volume only': 'log_vol', 'B + street design': DESIGN,
         'C + tract controls': DESIGN + CTRL, 'D + borough (primary)': DESIGN + CTRL + ' + C(county)'}
RHS_D = 'Poverty_Rate_Percent + ' + SPECS['D + borough (primary)']


def fit(d, y, rhs=RHS_D, offset=None):
    groups = pd.factorize(d['ZCTA_cluster'])[0]
    model = smf.glm(f'{y} ~ {rhs}', data=d, family=sm.families.Poisson(), offset=offset)
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups})


def fit_nb(d, y, rhs):
    p = fit(d, y, rhs)
    mu = np.asarray(p.mu)
    yy = d[y].values
    alpha = max(float((mu * (((yy - mu) ** 2 - yy) / mu)).sum() / (mu * mu).sum()), 1e-6)
    groups = pd.factorize(d['ZCTA_cluster'])[0]
    model = smf.glm(f'{y} ~ {rhs}', data=d, family=sm.families.NegativeBinomial(alpha=alpha))
    return model.fit(cov_type='cluster', cov_kwds={'groups': groups}), alpha


def rr(res):
    lo, hi = res.conf_int().loc['Poverty_Rate_Percent']
    return f"{np.exp(10 * res.params['Poverty_Rate_Percent']):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})"


d25 = make_dataset(25, 30)
print(f'\nprimary dataset: {len(d25)} sites, {int(d25["harm"].sum())} harm crashes, {int(d25["killed"].sum())} deaths')

# 1. Model progression
print('\n1. Deaths, poverty rate ratio per +10 points')
for k, f in SPECS.items():
    rhs = 'Poverty_Rate_Percent + ' + f
    p = fit(d25, 'killed', rhs)
    nbres, alpha = fit_nb(d25, 'killed', rhs)
    print(f'  {k}: Poisson {rr(p)} | NB {rr(nbres)} (alpha {alpha:.2f})')

# 2. Site definition and radius
print('\n2. Site grouping distance and crash radius, model D')
for eps, radius in [(15, 30), (40, 30), (25, 20), (25, 50)]:
    dd = make_dataset(eps, radius)
    print(f'  grouping {eps} m, radius {radius} m: {int(dd["killed"].sum())} deaths, poverty RR = {rr(fit(dd, "killed"))}')

# 3. Time
print('\n3. Time, model D')
for label, y in [('2019 to 2021', 'k_early'), ('2022 to 2023', 'k_late')]:
    print(f'  {label}: {int(d25[y].sum())} deaths, poverty RR = {rr(fit(d25, y))}')
print('  deaths per year:', {yr: int(d25[f"k{yr}"].sum()) for yr in YEARS})

# 4. Leave one borough out
print('\n4. Leave one borough out, model D')
for name in COUNTY_NAMES.values():
    sub = d25[d25['county'] != name].copy()
    print(f'  without {name}: {int(sub["killed"].sum())} deaths, poverty RR = {rr(fit(sub, "killed"))}')


# 5. Cluster bootstrap for the death ratio
def irls(Xm, yv, beta0, iters=40, tol=1e-9):
    beta = beta0.copy()
    for _ in range(iters):
        eta = Xm @ beta
        mu = np.exp(np.clip(eta, -20, 20))
        z = eta + (yv - mu) / mu
        XtW = Xm.T * mu
        new = np.linalg.solve(XtW @ Xm, XtW @ z)
        done = np.max(np.abs(new - beta)) < tol
        beta = new
        if done:
            break
    return beta


yS, XS = patsy.dmatrices(f'killed ~ {RHS_D}', d25, return_type='dataframe')
Xv, yv = XS.values.astype(float), yS.iloc[:, 0].values.astype(float)
i_pov = list(XS.columns).index('Poverty_Rate_Percent')
cidx = pd.factorize(d25['ZCTA_cluster'])[0]
rows_by_cluster = [np.where(cidx == g)[0] for g in range(cidx.max() + 1)]
b0 = irls(Xv, yv, np.zeros(Xv.shape[1]), iters=80)
rng = np.random.default_rng(7)
boots = []
for _ in range(500):
    pick = rng.integers(0, len(rows_by_cluster), len(rows_by_cluster))
    idx = np.concatenate([rows_by_cluster[g] for g in pick])
    try:
        boots.append(irls(Xv[idx], yv[idx], b0)[i_pov])
    except np.linalg.LinAlgError:
        continue
lo, hi = np.percentile(np.exp(10 * np.array(boots)), [2.5, 97.5])
print(f'\n5. Cluster bootstrap, {len(boots)} resamples of {len(rows_by_cluster)} ZIP clusters, deaths, model D')
print(f'  point estimate {np.exp(10 * b0[i_pov]):.2f}, percentile interval {lo:.2f} to {hi:.2f}')

# 6. Frequency versus severity
freq = fit(d25, 'harm')
has = d25[d25['harm'] > 0].copy()
sev = fit(has, 'killed', offset=np.log(has['harm'].values))
dea = fit(d25, 'killed')
print('\n6. Frequency and severity, model D')
print(f'  harm crashes per site (frequency): {rr(freq)}')
print(f'  deaths per harm crash (severity, {len(has)} sites with a crash): {rr(sev)}')
print(f'  deaths per site (total): {rr(dea)}')

d25.to_csv(f'{DRIVE_DIR}/sites_eps25_r30_by_year.csv', index=False)
print('\nsaved to', f'{DRIVE_DIR}/sites_eps25_r30_by_year.csv')
