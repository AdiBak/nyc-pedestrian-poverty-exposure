# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# Step 2 of the crossing exposure build.
# The NYC Walks file has no segment type, so we infer crosswalks as the segments that cross a
# street centerline. Sidewalks run alongside streets and crosswalks cross them. Park footpaths
# do not cross roadbeds, so they drop out of this measure.
# Run after step 1, which saved the centerline file to Drive.

# %% C2. Infer crosswalks and build tract level crossing exposure
import os
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from google.colab import drive

drive.mount('/content/drive')
DRIVE_DIR = '/content/drive/MyDrive/TDSP/nyc_walks'
MEMBER = 'NYC_pednetwork_estimates_counts_2018-2019.geojson'
LOCAL = f'/content/{MEMBER}'

if not os.path.exists(LOCAL):
    with zipfile.ZipFile(f'{DRIVE_DIR}/supp_data_1_network.zip') as z:
        with z.open(MEMBER) as src, open(LOCAL, 'wb') as dst:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)

TRACT_ZIP = '/content/ny_tracts2020.zip'
if not os.path.exists(TRACT_ZIP):
    url = 'https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_36_tract_500k.zip'
    with open(TRACT_ZIP, 'wb') as f:
        f.write(requests.get(url, timeout=120).content)

NYC_COUNTIES = {'005': 'Bronx', '047': 'Brooklyn', '061': 'Manhattan',
                '081': 'Queens', '085': 'Staten Island'}
tracts = gpd.read_file(TRACT_ZIP)
tracts = tracts[tracts['COUNTYFP'].isin(NYC_COUNTIES)][['GEOID', 'geometry']].to_crs(6538)

# Street centerlines
cl = gpd.read_file(f'{DRIVE_DIR}/centerline_inkn-q76z.geojson').to_crs(6538)
for c in ['rw_type', 'status', 'streetwidth', 'posted_speed']:
    cl[c] = pd.to_numeric(cl[c], errors='coerce')

# Read the example names to interpret each road type code before trusting it
summary = cl.groupby('rw_type').agg(
    n=('physicalid', 'size'),
    median_width_ft=('streetwidth', 'median'),
    share_nonvehicular=('trafdir', lambda s: (s == 'NV').mean()))
summary['examples'] = cl.groupby('rw_type')['full_street_name'].agg(
    lambda s: ' | '.join(s.dropna().drop_duplicates().head(4)))
print('Road types in the centerline file')
print(summary.round(2).to_string())
print('\nnonped values')
print(cl['nonped'].value_counts(dropna=False).head(8).to_string())

# Pedestrian volumes
WKDY = ['predwkdyAM', 'predwkdyMD', 'predwkdyPM']
WKND = ['predwkndAM', 'predwkndMD', 'predwkndPM']
seg = gpd.read_file(LOCAL, engine='pyogrio', columns=WKDY + WKND).to_crs(6538)
seg[WKDY + WKND] = seg[WKDY + WKND].fillna(0).clip(lower=0)
seg['len_m'] = seg.geometry.length
seg['vol_wkdy'] = seg[WKDY].mean(axis=1)
seg['vol_wknd'] = seg[WKND].mean(axis=1)
seg['vol_peak'] = seg[WKDY + WKND].mean(axis=1)
seg['seg_id'] = np.arange(len(seg))

# Start with ordinary streets only. Add other codes here only after reading the table above.
STREET_TYPES = [1]
road = cl[(cl['status'] == 2) & (cl['rw_type'].isin(STREET_TYPES)) & (cl['trafdir'] != 'NV')]
road = road[['physicalid', 'streetwidth', 'posted_speed', 'geometry']]
print('\nstreet centerlines used:', len(road))

hit = gpd.sjoin(seg[['seg_id', 'geometry']], road, how='inner', predicate='intersects')
n_hit = hit.groupby('seg_id').size()
widest = (hit.sort_values('streetwidth', ascending=False, na_position='last')
          .drop_duplicates('seg_id')[['seg_id', 'streetwidth', 'posted_speed']])
seg['n_streets'] = seg['seg_id'].map(n_hit).fillna(0).astype(int)
seg = seg.merge(widest, on='seg_id', how='left')
seg['is_cross'] = seg['n_streets'] > 0

print('segments flagged as crossings:', int(seg['is_cross'].sum()),
      f"({seg['is_cross'].mean():.1%} of all)")
print('flagged segments that meet two or more streets:', int((seg['n_streets'] >= 2).sum()))
print('\nMedian length and peak volume, crossings versus other segments')
print(seg.groupby('is_cross')[['len_m', 'vol_peak']].median().round(1).to_string())

# Assign each crossing to the tract that holds its midpoint
cr = seg[seg['is_cross']].copy()
cr['geometry'] = cr.geometry.interpolate(0.5, normalized=True)
cr = gpd.GeoDataFrame(cr, geometry='geometry', crs=seg.crs)
keep = ['vol_wkdy', 'vol_wknd', 'vol_peak', 'streetwidth', 'posted_speed', 'geometry']
cj = gpd.sjoin(cr[keep], tracts, how='left', predicate='within')
print('crossings without a tract:', int(cj['GEOID'].isna().sum()))
cj = cj.dropna(subset=['GEOID'])

cj['vol_x_spd'] = cj['vol_peak'] * cj['posted_speed']
cj['vol_spd'] = cj['vol_peak'].where(cj['posted_speed'].notna(), 0)
cj['vol_x_wid'] = cj['vol_peak'] * cj['streetwidth']
cj['vol_wid'] = cj['vol_peak'].where(cj['streetwidth'].notna(), 0)

agg = (cj.groupby('GEOID')
       .agg(n_crossings=('vol_peak', 'size'),
            cross_vol_wkdy=('vol_wkdy', 'sum'),
            cross_vol_wknd=('vol_wknd', 'sum'),
            cross_vol_peak=('vol_peak', 'sum'),
            _xs=('vol_x_spd', 'sum'), _vs=('vol_spd', 'sum'),
            _xw=('vol_x_wid', 'sum'), _vw=('vol_wid', 'sum'))
       .reset_index())
agg['wtd_speed_mph'] = agg['_xs'] / agg['_vs'].replace(0, np.nan)
agg['wtd_street_width_ft'] = agg['_xw'] / agg['_vw'].replace(0, np.nan)
agg = agg.drop(columns=['_xs', '_vs', '_xw', '_vw'])
agg['mean_cross_vol'] = agg['cross_vol_peak'] / agg['n_crossings']
agg['county'] = agg['GEOID'].str[2:5].map(NYC_COUNTIES)

out_csv = f'{DRIVE_DIR}/tract_crossing_exposure_2018_2019_volumes.csv'
agg.to_csv(out_csv, index=False)
print('\ntracts with crossings:', len(agg), 'of', len(tracts), '| saved to', out_csv)

cols = ['GEOID', 'county', 'n_crossings', 'cross_vol_peak', 'mean_cross_vol',
        'wtd_speed_mph', 'wtd_street_width_ft']
print('\nTop 10 tracts by crossing volume')
print(agg.sort_values('cross_vol_peak', ascending=False).head(10)[cols].round(1).to_string(index=False))
print('\nMedian crossing volume by borough')
print(agg.groupby('county')['cross_vol_peak'].median().round(0).to_string())
print('\nDistribution')
print(agg[['n_crossings', 'cross_vol_peak', 'wtd_speed_mph', 'wtd_street_width_ft']]
      .describe().round(1).to_string())

# How different is this from the first exposure measure?
old_csv = f'{DRIVE_DIR}/tract_exposure_2018_2019_volumes.csv'
if os.path.exists(old_csv):
    old = pd.read_csv(old_csv, dtype={'GEOID': str})
    both = old.merge(agg, on='GEOID')
    rho = both['ped_m_peak'].corr(both['cross_vol_peak'], method='spearman')
    print(f'\nSpearman correlation with the first measure (pedestrian meters): {rho:.2f}')
