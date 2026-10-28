# Developed and run in Google Colab, as a cell of the project notebook.
# See README.md for the run order and for what each script needs.

# %% Libraries
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium

# %% Mount Drive and load the crash data
from google.colab import drive
drive.mount('/content/drive')
data = pd.read_csv("/content/drive/MyDrive/Motor_Vehicle_Collisions_-_Crashes_20260810.csv")

# % Milestone 5 setup, notebook cell 70
# Imports and settings
import io
import os
import time
import urllib.request

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import statsmodels
import statsmodels.api as sm
import statsmodels.formula.api as smf
from google.colab import userdata

# Define study windows and population thresholds
STUDY_START, STUDY_END = 2019, 2024
HEADLINE_YEARS = list(range(2019, 2024))        # matches the ACS 2019-2023 window
EARLY_YEARS, LATE_YEARS = [2019, 2020, 2021], [2022, 2023, 2024]
MIN_POP_ZIP = 5000                              # resident floor for a ZIP to enter the analysis
MIN_POP_TRACT = 1000                            # resident floor for a tract
SNAP_FT = 1640                                  # snap radius for points on bridges or water (about 500 m)
NYC_COUNTIES = ['005', '047', '061', '081', '085']
HWY_WORDS = ['EXPRESSWAY', 'PARKWAY', 'BRIDGE', 'HIGHWAY', 'TUNNEL', 'THRUWAY', 'TURNPIKE', 'FDR', 'BQE']
CONTROLS = ['Walk_Share', 'Transit_Share', 'Commercial_Share']

# Model specifications for later evaluation
SPECS = [('poverty only', []),
         ('+ walking, transit', CONTROLS[:2]),
         ('+ walking, transit, commercial', CONTROLS)]
OUTCOMES = [('Ped_Killed', 'Deaths'), ('Ped_Injured', 'Injuries'), ('Crashes', 'All crashes')]

# Create output directory and configure pandas display
OUT_DIR = '/content/results'
os.makedirs(OUT_DIR, exist_ok=True)
API_KEY = userdata.get('CENSUS_API_KEY')
pd.set_option('display.width', 250, 'display.max_colwidth', 45)

print(f"pandas {pd.__version__}, statsmodels {statsmodels.__version__}, geopandas {gpd.__version__}")

# % Milestone 5 setup, notebook cell 71
# Crash data window setup
crashes = data.copy()
# Parse crash dates to datetime format
crashes['CRASH DATE'] = pd.to_datetime(crashes['CRASH DATE'])
print("Latest crash date in file:", crashes['CRASH DATE'].max().date())
# Filter records to our target study timeframe
crashes['YEAR'] = crashes['CRASH DATE'].dt.year
crashes = crashes[crashes['YEAR'].between(STUDY_START, STUDY_END)].copy()

per_year = crashes.groupby('YEAR').size()
print(per_year)
if crashes['CRASH DATE'].max() < pd.Timestamp(f'{STUDY_END}-12-01'):
    print(f"WARNING: {STUDY_END} looks incomplete.")

# Safely convert ZIP to numeric, coercing errors to NaN
crashes['ZIP_REPORTED'] = pd.to_numeric(crashes['ZIP CODE'], errors='coerce')
# Generate a heuristic road type flag by checking for highway-related keywords
street_text = (crashes['ON STREET NAME'].fillna('') + ' ' + crashes['CROSS STREET NAME'].fillna('')).str.upper()
crashes['is_highway'] = street_text.str.contains('|'.join(HWY_WORDS), regex=True)   # approximate road type flag

fatal = crashes[crashes['NUMBER OF PEDESTRIANS KILLED'] > 0]
print(f"Fatal pedestrian crashes missing a ZIP: {fatal['ZIP_REPORTED'].isna().mean():.1%}")
print(f"Highway flagged, with a ZIP: {fatal.loc[fatal['ZIP_REPORTED'].notna(), 'is_highway'].mean():.1%}, "
      f"without a ZIP: {fatal.loc[fatal['ZIP_REPORTED'].isna(), 'is_highway'].mean():.1%}")

# % Milestone 5 setup, notebook cell 72
# Boundaries, tract assignment and ZIP recovery

def download(url, path):
    """Helper to fetch geographic files locally."""
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    return path

# Load ZCTA and Census Tract shapefiles
zcta = gpd.read_file(download(
    "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip", "/content/zcta2020.zip"))
zcode = [c for c in zcta.columns if c.startswith('ZCTA5CE')][0]
tracts = gpd.read_file(download(
    "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_36_tract_500k.zip", "/content/ny_tracts2020.zip"))
# Filter to the five NYC counties and reproject to NY State Plane (feet) for accurate distance measurements
tracts = tracts[tracts['COUNTYFP'].isin(NYC_COUNTIES)][['GEOID', 'geometry']].to_crs(2263)
print(f"NYC tracts: {len(tracts)}")

# Only consider crashes with plausible geographic coordinates
valid = crashes['LATITUDE'].between(40.4, 41.0) & crashes['LONGITUDE'].between(-74.3, -73.6)
pts = gpd.GeoDataFrame(
    crashes.loc[valid, []],
    geometry=gpd.points_from_xy(crashes.loc[valid, 'LONGITUDE'], crashes.loc[valid, 'LATITUDE']),
    crs=4326).to_crs(2263)

# Every crash with coordinates gets a tract. Points inside match at distance 0, others snap within SNAP_FT.
jt = gpd.sjoin_nearest(pts, tracts, how='left', max_distance=SNAP_FT)
jt = jt[~jt.index.duplicated(keep='first')]
crashes['TRACT'] = jt['GEOID'].reindex(crashes.index)

# Crashes without a reported ZIP get one from the ZCTA boundaries
xmin, ymin, xmax, ymax = pts.total_bounds
zcta_nyc = zcta.to_crs(2263).cx[xmin - 5000:xmax + 5000, ymin - 5000:ymax + 5000]
pts_zip = pts[crashes.loc[pts.index, 'ZIP_REPORTED'].isna()]
jz = gpd.sjoin_nearest(pts_zip, zcta_nyc[[zcode, 'geometry']], how='left', max_distance=SNAP_FT)
jz = jz[~jz.index.duplicated(keep='first')]
crashes['ZIP_RECOVERED'] = pd.to_numeric(jz[zcode], errors='coerce').reindex(crashes.index)

# Store different ZIP scenarios for our sensitivity analysis
crashes['ZIP_ALL'] = crashes['ZIP_REPORTED'].fillna(crashes['ZIP_RECOVERED'])
crashes['ZIP_LOCAL'] = crashes['ZIP_REPORTED'].fillna(crashes['ZIP_RECOVERED'].where(~crashes['is_highway']))

# Cluster id for each tract is the ZIP that contains its centroid. Important for clustering standard errors.
tr_c = tracts.copy()
tr_c['geometry'] = tr_c.geometry.centroid
cl = gpd.sjoin_nearest(tr_c, zcta_nyc[[zcode, 'geometry']], how='left')
tract_cluster = cl[~cl.index.duplicated(keep='first')][['GEOID', zcode]].rename(columns={zcode: 'ZCTA_cluster'})

head = crashes[crashes['YEAR'].isin(HEADLINE_YEARS)]
deaths = head['NUMBER OF PEDESTRIANS KILLED']
print("Share of pedestrian deaths placed, headline window")
for col in ['ZIP_REPORTED', 'ZIP_ALL', 'ZIP_LOCAL', 'TRACT']:
    print(f"  {col}: {deaths[head[col].notna()].sum() / deaths.sum():.1%}")

# % Milestone 5 setup, notebook cell 73
# Neighborhood data from the Census API and PLUTO
ACS_BASE = "https://api.census.gov/data/2023/acs/acs5/subject"
# 2019-2023 5-year estimates
ACS_VARS = {'S1701_C01_001E': 'Total_Population', 'S1701_C03_001E': 'Poverty_Rate_Percent',
            'S0801_C01_010E': 'Walk_Share', 'S0801_C01_009E': 'Transit_Share'}

def fetch_acs(geo_clause):
    url = f"{ACS_BASE}?get=NAME,{','.join(ACS_VARS)}&{geo_clause}&key={API_KEY}"
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    rows = r.json()
    d = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=ACS_VARS)
    for c in ACS_VARS.values():
        d[c] = pd.to_numeric(d[c], errors='coerce')
        d.loc[d[c] < 0, c] = np.nan                     # suppressed values arrive as large negatives
    return d

zip_acs = fetch_acs("for=zip%20code%20tabulation%20area:*")
zip_acs['ZIP'] = pd.to_numeric(zip_acs['zip code tabulation area'], errors='coerce')
zip_acs = zip_acs.dropna(subset=['ZIP']).astype({'ZIP': int})

tract_acs = fetch_acs(f"for=tract:*&in=state:36&in=county:{','.join(NYC_COUNTIES)}")
tract_acs['GEOID'] = tract_acs['state'] + tract_acs['county'] + tract_acs['tract']

PLUTO_URL = "https://data.cityofnewyork.us/resource/64uk-42ks.csv"

def get_with_retry(params, tries=5):
    for i in range(tries):
        r = requests.get(PLUTO_URL, params=params, timeout=180)
        if r.status_code == 200:
            return r
        print(f"PLUTO attempt {i + 1}: HTTP {r.status_code}, waiting {5 * 2 ** i}s")
        time.sleep(5 * 2 ** i)
    r.raise_for_status()

def pluto_share(group):
    r = get_with_retry({'$select': f'{group}, sum(comarea) as com_area, sum(resarea) as res_area',
                        '$group': group, '$limit': 5000})
    p = pd.read_csv(io.StringIO(r.text), dtype={group: str})
    p['Commercial_Share'] = p['com_area'] / (p['com_area'] + p['res_area']) * 100
    return p

pz = pluto_share('zipcode')
pz['ZIP'] = pd.to_numeric(pz['zipcode'], errors='coerce')
pluto_zip = pz.dropna(subset=['ZIP']).astype({'ZIP': int})[['ZIP', 'Commercial_Share']]

pt = pluto_share('bct2020')
pt['bct2020'] = pt['bct2020'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(7)
boro_to_county = {'1': '061', '2': '005', '3': '047', '4': '081', '5': '085'}
pt = pt[pt['bct2020'].str[0].isin(boro_to_county)].copy()
pt['GEOID'] = '36' + pt['bct2020'].str[0].map(boro_to_county) + pt['bct2020'].str[1:]
pluto_tract = pt[['GEOID', 'Commercial_Share']]
print(f"ZIPs with ACS data: {len(zip_acs)}, NYC tracts with ACS data: {len(tract_acs)}, "
      f"PLUTO ZIPs: {len(pluto_zip)}, PLUTO tracts: {len(pluto_tract)}")

# % Milestone 5 setup, notebook cell 74
# Table builders and model helpers
EVENTS = dict(Ped_Killed=('NUMBER OF PEDESTRIANS KILLED', 'sum'),
              Ped_Injured=('NUMBER OF PEDESTRIANS INJURED', 'sum'),
              Crashes=('CRASH DATE', 'size'))
NEED = ['Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share', 'Commercial_Share']

def zip_table(years, zip_col, min_pop=MIN_POP_ZIP):
    """Aggregate crash and census data at the ZIP code level."""
    d = crashes[crashes['YEAR'].isin(years)].dropna(subset=[zip_col]).copy()
    d[zip_col] = d[zip_col].astype(int)
    agg = d.groupby(zip_col).agg(**EVENTS).reset_index().rename(columns={zip_col: 'ZIP'})
    # Merge in Census and PLUTO features
    m = (agg.merge(zip_acs[['ZIP', 'Total_Population', 'Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share']],
                   on='ZIP', how='inner')
            .merge(pluto_zip, on='ZIP', how='left'))
    m = m[m['Total_Population'] >= min_pop].dropna(subset=NEED).reset_index(drop=True)
    m['n_years'] = len(years)
    return m

def tract_table(years, scenario='local', min_pop=MIN_POP_TRACT):
    """Aggregate crash and census data at the Census Tract level."""
    d = crashes[crashes['YEAR'].isin(years)].dropna(subset=['TRACT'])
    if scenario == 'local':
        d = d[~d['is_highway']]                         # drop highway flagged crashes entirely
    agg = d.groupby('TRACT').agg(**EVENTS).reset_index().rename(columns={'TRACT': 'GEOID'})
    m = (tract_acs[['GEOID', 'Total_Population', 'Poverty_Rate_Percent', 'Walk_Share', 'Transit_Share']]
         .merge(agg, on='GEOID', how='left')            # tracts with no crashes stay in as zeros
         .merge(pluto_tract, on='GEOID', how='left')
         .merge(tract_cluster, on='GEOID', how='left'))
    m[list(EVENTS)] = m[list(EVENTS)].fillna(0)
    m = m[m['Total_Population'] >= min_pop].dropna(subset=NEED + ['ZCTA_cluster']).reset_index(drop=True)
    m['n_years'] = len(years)
    return m

def fit_nb(m, outcome, controls, groups=None):
    """Negative binomial regression model with population exposure. Pass groups to cluster the standard errors."""
    rhs = ' + '.join(['Poverty_Rate_Percent'] + controls)
    model = smf.negativebinomial(f'{outcome} ~ {rhs}', data=m, exposure=m['Total_Population'] * m['n_years'])
    if groups is None:
        return model.fit(disp=0, maxiter=500)
    return model.fit(disp=0, maxiter=500, cov_type='cluster', cov_kwds={'groups': pd.factorize(groups)[0]})

def rr_text(fit, term='Poverty_Rate_Percent'):
    """Compute and format Rate ratio per +10 points of poverty with a 95% interval."""
    lo, hi = fit.conf_int().loc[term]
    return f"{np.exp(10 * fit.params[term]):.2f} ({np.exp(10 * lo):.2f} to {np.exp(10 * hi):.2f})"

zip_m = zip_table(HEADLINE_YEARS, 'ZIP_LOCAL')
tract_m = tract_table(HEADLINE_YEARS, 'local')
print(f"ZIP analysis: {len(zip_m)} ZIPs, {zip_m['Ped_Killed'].sum():.0f} deaths")
print(f"Tract analysis: {len(tract_m)} tracts, {tract_m['Ped_Killed'].sum():.0f} deaths, "
      f"{tract_m['ZCTA_cluster'].nunique()} ZIP clusters, {(tract_m['Ped_Killed'] == 0).mean():.0%} of tracts with no deaths")
